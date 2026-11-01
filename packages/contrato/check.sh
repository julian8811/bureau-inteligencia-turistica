#!/bin/sh
# T4: verifica que el contrato ETL -> front siga idéntico. Sale 0 ok, 1 mismatch.
# Uso: sh packages/contrato/check.sh (desde la raíz del monorepo)
set -eu
ETL=apps/etl/export/tableros_bureau/informe_llm.json
FRONT=apps/tableros/data/open/informe_llm.json
for f in "$ETL" "$FRONT"; do
  test -f "$f" || { echo "[contrato][FAIL] falta $f"; exit 1; }
done
A=$(sha256sum "$ETL" | cut -d' ' -f1)
B=$(sha256sum "$FRONT" | cut -d' ' -f1)
if [ "$A" != "$B" ]; then
  echo "[contrato][FAIL] informe_llm difiere ETL=$A front=$B"
  exit 1
fi
python3 - "$ETL" "$FRONT" <<'EOF'
import json, sys
for p in sys.argv[1:]:
    d = json.load(open(p))
    assert isinstance(d.get("corte"), str), p
    secs = d.get("secciones", [])
    assert len(secs) >= 3, (p, len(secs))
    for s in secs:
        assert s.get("bullets"), (p, s.get("id"))
print("[contrato] ok sha + 3+ secciones con bullets en ambas copias")
EOF
