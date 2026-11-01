"""Gated ICCA/Cvent + CRM interno (100% manual mensual, nunca scraping).

Espera en data/raw/manual/:
  - crm.xlsx (RFP/eventos: estado, asistentes, gasto_prom_usd, estadia_noches, valor_rfp_usd, prob)
  - icca*.xlsx/csv (ranking anual comprado o descargado)
  - cvent*.xlsx/csv (export manual)
Sin archivos -> SKIP con instrucciones. Con archivos -> valida columnas
minimas del CRM y deja copia fechada en data/raw/<hoy>/ para auditoria.
"""
import shutil
from datetime import date
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
MANUAL = RAW / "manual"
EXPECTED_CRM = {"estado", "asistentes"}


def run():
    hoy = date.today().isoformat()
    outdir = RAW / hoy
    outdir.mkdir(parents=True, exist_ok=True)
    if not MANUAL.exists():
        print("[gated][SKIP] sin data/raw/manual/ -> crear y pegar crm.xlsx")
        return None
    found = sorted(MANUAL.glob("crm.xlsx")) + sorted(MANUAL.glob("icca*")) + sorted(MANUAL.glob("cvent*"))
    if not found:
        print("[gated][SKIP] manual vacio: pegar crm.xlsx + icca/cvent si existen")
        return None
    for src in found:
        try:
            dst = outdir / f"manual_{src.name}"
            shutil.copy(src, dst)
            print(f"[gated] manual {src.name} -> {dst.name}")
        except Exception as e:
            print(f"[gated][WARN] {src.name}: {e}")
    # validacion minima CRM
    try:
        import pandas as pd
        crm = MANUAL / "crm.xlsx"
        if crm.exists():
            df = pd.read_excel(crm)
            missing = EXPECTED_CRM - set(df.columns)
            if missing:
                print(f"[gated][WARN] crm.xlsx sin columnas {sorted(missing)} -> KPIs MICE parciales")
            else:
                print(f"[gated] crm.xlsx OK: {len(df)} filas")
    except Exception as e:
        print(f"[gated][WARN] validar crm.xlsx: {e}")
    return found


if __name__ == "__main__":
    run()
