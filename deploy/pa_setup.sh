#!/usr/bin/env bash
# One-shot setup for PythonAnywhere. Run from a Bash console INSIDE the project folder:
#     cd ~/sarab && bash deploy/pa_setup.sh
# Re-run it after every update (git pull / re-upload) — it is safe to repeat.
set -euo pipefail

PYVER="${PYVER:-3.12}"          # must match the Python version chosen in the Web tab
VENV="$HOME/.virtualenvs/sarab"

if [ ! -d "$VENV" ]; then
  echo "==> Creating virtualenv ($PYVER)"
  python"$PYVER" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "!! Created .env from .env.example — EDIT IT now (nano .env), then run this script again."
  exit 1
fi

echo "==> Installing requirements"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo "==> Database migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Django deployment check"
python manage.py check --deploy || true

cat <<MSG

Done. Next (first time only):
  * python manage.py seed_data          # optional demo menu/users — then CHANGE the admin password
  * python manage.py createsuperuser    # your own admin account
  * Web tab -> Reload
MSG
