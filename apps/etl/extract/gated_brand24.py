"""Brand24 API Data trial: menciones de marca Medellin/Bureau.

Auth con BRAND24_KEY (header X-Api-Key) + BRAND24_ACCOUNT_ID desde entorno
(trial Pro 14 dias, 10 keywords, 30k menciones; alta en
app.brand24.com/account/integrations-api-data, exportar en
~/.bureau_backend_env).
Base: https://api-data.brand24.com. Endpoints minimos utiles al tablero marca:
  - proyectos (keywords del trial: Medellin/Bureau, max 10)
  - menciones por proyecto/keyword (fuente, sentimiento, alcance).
Sin keys -> fallback manual: data/raw/manual/brand24*.csv|xlsx copiado a
data/raw/<hoy>/brand24_menciones.csv. Sin keys ni manual -> SKIP honesto con
instrucciones. Ante error/429 -> save_or_carry desde base.py, jamas levanta.
Guarda data/raw/<hoy>/brand24_menciones.csv con columnas
periodo, keyword, fuente, sentimiento, alcance, fecha_consulta.
"""

import os
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from .base import save_or_carry

API_BASE = "https://api-data.brand24.com"
PROJECT_PATHS = ("/projects", "/v1/projects")
MENTION_PATHS = ("/mentions", "/v1/mentions")

# Keywords del trial (max 10): marca Medellin/Bureau para tablero marca.
KEYWORDS = [
    "Medellín",
    "Medellin",
    "Bureau Medellín",
    "Bureau Medellin",
    "Visit Medellín",
    "Turismo Medellín",
    "Medellín Bureau",
    "Medellín travel",
    "Medellin Colombia",
    "Bureau de Medellín",
]

COLUMNS = ["periodo", "keyword", "fuente", "sentimiento", "alcance", "fecha_consulta"]
OUT_NAME = "brand24_menciones"

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

POS = {"pos", "positive", "positivo", "positiva"}
NEG = {"neg", "negative", "negativo", "negativa"}


def _norm_sentimiento(raw: object) -> str:
    s = str(raw or "").strip().lower()
    if s in POS:
        return "pos"
    if s in NEG:
        return "neg"
    return "neu"


def _as_list(payload: object) -> list:
    """El API Data puede envolver en data/mentions/results/items/projects."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "mentions", "results", "items", "projects"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                for sub in ("data", "mentions", "results", "items"):
                    inner = val.get(sub)
                    if isinstance(inner, list):
                        return inner
    return []


def parse_mentions(payload: dict | list, keyword: str, hoy: str | None = None) -> pd.DataFrame:
    recs: list[dict] = []
    hoy = hoy or date.today().isoformat()
    for it in _as_list(payload):
        if not isinstance(it, dict):
            continue
        fecha = str(
            it.get("publishedAt")
            or it.get("published_at")
            or it.get("date")
            or it.get("createdAt")
            or it.get("created_at")
            or hoy
        )
        try:
            alcance = float(it.get("reach", it.get("audience", it.get("reachEstimate", 0))) or 0)
        except (TypeError, ValueError):
            alcance = 0.0
        recs.append(
            {
                "periodo": fecha[:7],
                "keyword": keyword,
                "fuente": str(
                    it.get("source") or it.get("domain") or it.get("site") or "desconocida"
                ).strip().lower(),
                "sentimiento": _norm_sentimiento(it.get("sentiment")),
                "alcance": alcance,
                "fecha_consulta": hoy,
            }
        )
    df = pd.DataFrame(recs).reindex(columns=COLUMNS)
    return df


def _headers(key: str) -> dict:
    return {"X-Api-Key": key, "Accept": "application/json"}


def _get(path: str, key: str, params: dict) -> dict | list | None:
    """GET defensivo: 401/429/cualquier error -> None (el caller hace SKIP/carry)."""
    try:
        r = requests.get(API_BASE + path, headers=_headers(key), params=params, timeout=40)
        if r.status_code in (401, 403, 429):
            print(f"[brand24][WARN] HTTP {r.status_code} en {path}")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[brand24][WARN] {path}: {e}")
        return None


def _fetch_projects(key: str, account_id: str) -> list:
    for path in PROJECT_PATHS:
        payload = _get(path, key, {"accountId": account_id, "account_id": account_id})
        items = _as_list(payload) if payload is not None else []
        if items:
            return [it for it in items if isinstance(it, dict)]
    return []


def _fetch_mentions(key: str, account_id: str, project_id: str = "", keyword: str = "") -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in MENTION_PATHS:
        payload = _get(
            path,
            key,
            {
                "accountId": account_id,
                "projectId": project_id,
                "project_id": project_id,
                "keyword": keyword,
                "limit": "100",
            },
        )
        if payload is None:
            continue
        df = parse_mentions(payload, keyword or project_id or "brand24")
        if not df.empty:
            frames.append(df)
            break
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(columns=COLUMNS)  # type: ignore[call-overload]


def _manual_fallback() -> Path | None:
    """Copia brand24*.csv/xlsx de manual/ a data/raw/<hoy>/brand24_menciones.csv."""
    manual = RAW / "manual"
    cands = sorted(manual.glob("brand24*.csv")) + sorted(manual.glob("brand24*.xlsx"))
    if not cands:
        return None
    src = cands[0]
    try:
        outdir = RAW / date.today().isoformat()
        outdir.mkdir(parents=True, exist_ok=True)
        dst = outdir / f"{OUT_NAME}.csv"
        if src.suffix.lower() == ".csv":
            shutil.copy(src, dst)
        else:
            df = pd.read_excel(src)
            df.to_csv(dst, index=False)
        print(f"[brand24] manual {src.name} -> {dst.name}")
        return dst
    except Exception as e:
        print(f"[brand24][WARN] fallback {src.name}: {e}")
        return None


def run() -> bool | None:
    key = os.environ.get("BRAND24_KEY", "")
    account_id = os.environ.get("BRAND24_ACCOUNT_ID", "")
    if not key or not account_id:
        dst = _manual_fallback()
        if dst is not None:
            return True
        print(
            "[brand24][SKIP] sin BRAND24_KEY/BRAND24_ACCOUNT_ID ni manual/brand24* -> "
            "crear trial Pro 14 dias en app.brand24.com/account/integrations-api-data "
            "(10 keywords, 30k menciones) y exportar keys en ~/.bureau_backend_env, "
            "o pegar export CSV/XLSX en data/raw/manual/"
        )
        return None
    try:
        hoy = date.today().isoformat()
        frames: list[pd.DataFrame] = []
        projects = _fetch_projects(key, account_id)
        if projects:
            for proj in projects:
                pid = str(proj.get("id", proj.get("projectId", "")))
                kw = str(proj.get("keyword", proj.get("name", ""))) or "brand24"
                if not pid:
                    continue
                df = _fetch_mentions(key, account_id, project_id=pid, keyword=kw)
                if not df.empty:
                    frames.append(df)
        else:
            # Sin proyectos (o endpoint distinto): menciones directas por keyword.
            for kw in KEYWORDS:
                df = _fetch_mentions(key, account_id, keyword=kw)
                if not df.empty:
                    frames.append(df)
                if sum(len(f) for f in frames) >= 30000:
                    print("[brand24] tope trial 30k menciones alcanzado")
                    break
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if not df.empty:
            df["fecha_consulta"] = hoy
        save_or_carry(df, OUT_NAME, COLUMNS)
        if df.empty:
            print("[brand24][SKIP] sin menciones nuevas -> verificar keywords/cuota trial")
            return False
        print(f"[brand24] OK ({len(df)} menciones)")
        return True
    except Exception as e:
        print(f"[brand24][SKIP] {e}")
        try:
            save_or_carry(pd.DataFrame(), OUT_NAME, COLUMNS)
        except Exception as e:
            print(f"[brand24][WARN] carry fallido: {e}")
        return False


if __name__ == "__main__":
    run()
