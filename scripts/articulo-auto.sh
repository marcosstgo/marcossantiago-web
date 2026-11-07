#!/bin/bash
# Corre el artículo automático desde la copia ~/marcossantiago-blog-auto (rama main). Lo llama el crontab:
#   0 8 * * 2,5  bash ~/marcossantiago-blog-auto/scripts/articulo-auto.sh
# Martes y viernes a las 8:00 AM (hora de PR). Registro en logs/auto.log de esa copia.
set -e
cd "$(dirname "$0")/.."
export PATH="$PWD/.tools/node_modules/node/bin:$PATH"
mkdir -p logs
git pull -q --rebase
# Si cambiaron las dependencias desde la última vez, reinstalar.
h=$(sha1sum package-lock.json | cut -c1-40)
[ "$(cat node_modules/.lock-hash 2>/dev/null)" = "$h" ] || { npm ci --silent && echo "$h" > node_modules/.lock-hash; }
.venv/bin/python scripts/articulo-auto.py "$@" >> logs/auto.log 2>&1
