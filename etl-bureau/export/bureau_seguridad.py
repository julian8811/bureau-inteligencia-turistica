"""Builder seguridad -> export/tableros_bureau/seguridad_2025_2026.json.

Lee RAW SIEDCO (homicidios + hurtos Medellin), agrega serie mensual
city-wide + top zonas + top modalidades (homicidios), escribe JSON simple
para `alimentar_bureau.py` (repo tableros-bureau).

Defensivo: archivo ausente o vacio -> {"estado":"skip","motivo":...},
exit 0, nunca tumba. Solo stdlib + pandas. No toca /tmp/tableros-bureau.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]  # etl-bureau/
RAW_ROOT = BASE / "data" / "raw"
OUT = BASE / "export" / "tableros_bureau" / "seguridad_2025_2026.json"

ID = "bureau-seguridad"
FUENTE = "ETL Bureau, SIEDCO Policia Nacional"
TOP_N = 8


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres: trim, minusculas, sin '_' lider (el raw trae
    `_modalidad_presunta` en homicidios)."""
    df = df.copy()
    df.columns = [str(c).strip().lstrip("_").lower() for c in df.columns]
    return df


def _latest_raw_dir() -> Path | None:
    if not RAW_ROOT.is_dir():
        return None
    cands = sorted(p for p in RAW_ROOT.iterdir() if p.is_dir())
    return cands[-1] if cands else None


def _skip(motivo: str) -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": ID,
        "generado": date.today().isoformat(),
        "ventana": "",
        "fuente": FUENTE,
        "estado": "skip",
        "motivo": motivo,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"estado": "skip", "motivo": motivo}, ensure_ascii=False))
    return 0


def _load_csv(path: Path, que: str) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"ausente: {path.name} ({que})")
    if path.stat().st_size == 0:
        raise ValueError(f"vacio: {path.name} ({que})")
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"vacio (solo header o sin filas): {path.name} ({que})")
    return _norm_cols(df)


def _monthly(df: pd.DataFrame, col_fecha: str = "fecha_hecho") -> pd.Series:
    fechas = pd.to_datetime(df[col_fecha], errors="coerce")
    periodos = fechas.dt.strftime("%Y-%m")
    cant = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)
    s = cant.groupby(periodos).sum()
    s = s[s.index.notna()]
    s.index.name = "periodo"
    return s.sort_index()


def main() -> int:
    try:
        raw = _latest_raw_dir()
        if raw is None:
            return _skip("sin directorio data/raw/*")
        f_hom = raw / "seguridad_homicidios_med.csv"
        f_hur = raw / "seguridad_hurtos_med.csv"
        try:
            hom = _load_csv(f_hom, "homicidios")
            hur = _load_csv(f_hur, "hurtos")
        except (FileNotFoundError, ValueError) as e:
            return _skip(str(e))

        for col in ("fecha_hecho", "cantidad"):
            if col not in hom.columns or col not in hur.columns:
                return _skip(f"columna requerida '{col}' ausente en el raw")

        m_hom = _monthly(hom)
        m_hur = _monthly(hur)
        idx = sorted(set(m_hom.index) | set(m_hur.index))
        serie = [
            {
                "periodo": p,
                "homicidios": int(m_hom.get(p, 0)),
                "hurtos": int(m_hur.get(p, 0)),
            }
            for p in idx
        ]
        ventana = f"{idx[0]} a {idx[-1]}" if idx else ""

        # Top zonas (el raw de hurtos no trae dimension zona -> hurtos None).
        top_zonas: list[dict] = []
        if "zona" in hom.columns:
            g = hom.assign(
                cantidad=pd.to_numeric(
                    hom["cantidad"], errors="coerce"
                ).fillna(0).astype(int)
            )
            g = g.dropna(subset=["zona"])
            zh = g.groupby("zona")["cantidad"].sum().sort_values(ascending=False)
            zh_hur = None
            if "zona" in hur.columns:
                gh = hur.assign(
                    cantidad=pd.to_numeric(
                        hur["cantidad"], errors="coerce"
                    ).fillna(0).astype(int)
                ).dropna(subset=["zona"])
                zh_hur = gh.groupby("zona")["cantidad"].sum()
            for zona, n in zh.head(TOP_N).items():
                top_zonas.append(
                    {
                        "zona": str(zona),
                        "homicidios": int(n),
                        "hurtos": int(zh_hur.get(zona, 0))
                        if zh_hur is not None
                        else None,
                    }
                )

        # Top modalidades (homicidios).
        top_mods: list[dict] = []
        mod_col = next(
            (c for c in hom.columns if "modalidad" in c), None
        )
        if mod_col is not None:
            g = hom.assign(
                cantidad=pd.to_numeric(
                    hom["cantidad"], errors="coerce"
                ).fillna(0).astype(int)
            ).dropna(subset=[mod_col])
            zm = (
                g.groupby(mod_col)["cantidad"]
                .sum()
                .sort_values(ascending=False)
            )
            for mod, n in zm.head(TOP_N).items():
                top_mods.append({"modalidad": str(mod), "n": int(n)})

        payload = {
            "id": ID,
            "generado": date.today().isoformat(),
            "ventana": ventana,
            "fuente": FUENTE,
            "serie_mensual": serie,
            "top_zonas": top_zonas,
            "top_modalidades": top_mods,
            "estado": "ok",
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "estado": "ok",
                    "out": str(OUT),
                    "meses": len(serie),
                    "ventana": ventana,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as e:  # jamás tumba: skip honesto
        try:
            return _skip(f"error no controlado: {type(e).__name__}: {e}")
        except Exception:
            print(
                json.dumps({"estado": "skip", "motivo": "falla escribiendo skip"}),
                file=sys.stderr,
            )
            return 0


if __name__ == "__main__":
    sys.exit(main())
