"""Clasificacion LLM de titulares del dia (Groq free, sin frontend).

Lee data/raw/<hoy>/alerts_rss.csv + prensa_rss.csv, clasifica cada titular
(categoria + sentimiento + topico) con Groq gratis y guarda
data/raw/<hoy>/clasificacion_llm.csv para que transform/load lo absorban.

Sin GROQ_API_KEY en el entorno -> SKIP honesto (DataFrame vacio, el daily
sigue con las reglas de kpis_marca). La key se crea gratis en
console.groq.com (solo email, sin tarjeta) y se exporta asi:
  export GROQ_API_KEY=gsk_...
429 (cuota) -> backoff 60s + 1 reintento por lote; timeout 90s por request.
Jamas levanta excepcion fuera del daily.
"""

import json
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
BATCH = 50
COLS = ["fecha", "medio", "titulo", "link", "categoria", "sentimiento", "topico", "modelo"]

SYSTEM = (
    "Clasificas titulares de turismo de Medellin y Colombia. "
    "Categorias: MICE, vacacional, marca, seguridad, clima, infraestructura, otro. "
    "Sentimiento: pos, neu, neg. Topico: 2-4 palabras. "
    "Respondes SOLO un JSON array con objetos {\"i\",\"cat\",\"sent\",\"top\"}, "
    "sin texto extra, sin code fences."
)


def _today() -> str:
    return date.today().isoformat()


def _load_titulares() -> pd.DataFrame:
    """Une alerts + prensa de hoy en una tabla (titulo, medio, fecha, link)."""
    frames = []
    day = RAW / _today()
    for name, medio_col in (("alerts_rss", "feed"), ("prensa_rss", "medio")):
        p = day / f"{name}.csv"
        if not p.exists():
            continue
        try:
            df = pd.read_csv(p)
        except Exception as e:
            print(f"[classify][WARN] {name}: no se pudo leer ({e})")
            continue
        if "titulo" not in df.columns:
            continue
        nd = pd.DataFrame({c: df[c] for c in ("titulo", "link", "fecha") if c in df.columns})
        nd["medio"] = df[medio_col] if medio_col in df.columns else ""
        nd["origen"] = name
        frames.append(nd)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["titulo"] = out["titulo"].astype(str)
    return out.drop_duplicates(subset=["titulo"]).reset_index(drop=True)


def _chat(messages: list, api_key: str) -> str:
    r = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "temperature": 0, "max_tokens": 4000},
        timeout=90,
    )
    if r.status_code == 429:
        print("[classify] 429 cuota -> backoff 60s + 1 reintento")
        time.sleep(60)
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "temperature": 0, "max_tokens": 4000},
            timeout=90,
        )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _parse(text: str) -> list:
    """Limpia code fences y parsea el JSON array (tolerante)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        data = json.loads(t)
    except Exception:
        start, end = t.find("["), t.rfind("]")
        data = json.loads(t[start:end + 1]) if start >= 0 and end > start else []
    return data if isinstance(data, list) else []


def _classify_batch(items: list, api_key: str) -> list:
    user = "Clasifica estos titulares. Responde SOLO el JSON array:\n" + "\n".join(
        f'{i}. {t["titulo"][:220]}' for i, t in enumerate(items)
    )
    try:
        data = _parse(_chat(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            api_key,
        ))
    except Exception as e:
        print(f"[classify][WARN] lote fallido: {str(e)[:150]}")
        return []
    out = []
    for d in data:
        try:
            it = items[int(d.get("i", -1))]
        except (TypeError, ValueError, IndexError):
            continue
        out.append({
            "fecha": it.get("fecha", ""), "medio": it.get("medio", ""),
            "titulo": it["titulo"], "link": it.get("link", ""),
            "categoria": str(d.get("cat", "otro")).lower()[:20],
            "sentimiento": str(d.get("sent", "neu")).lower()[:4],
            "topico": str(d.get("top", ""))[:60], "modelo": MODEL,
        })
    return out


def run() -> list:
    """Clasifica los titulares de hoy. Sin key -> SKIP limpio."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        print("[classify][SKIP] sin GROQ_API_KEY (gratis en console.groq.com) -> skip")
        return []
    df = _load_titulares()
    if df.empty:
        print("[classify][SKIP] sin titulares hoy")
        return []
    rows: list = []
    recs = df.to_dict(orient="records")
    for i in range(0, len(recs), BATCH):
        chunk = recs[i:i + BATCH]
        rows.extend(_classify_batch(chunk, api_key))
        print(f"[classify] lote {i // BATCH + 1}: {len(rows)} clasificados de {len(recs)}")
        time.sleep(3)  # pacing anti-429
    out = pd.DataFrame({c: [r.get(c, "") for r in rows] for c in COLS})
    p = RAW / _today() / "clasificacion_llm.csv"
    out.to_csv(p, index=False)
    print(f"[classify] {len(out)}/{len(recs)} titulares -> {p}")
    return [p]


if __name__ == "__main__":
    run()
