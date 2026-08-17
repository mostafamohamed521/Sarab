#!/usr/bin/env bash
# Render runs this automatically on every deploy (see render.yaml's
# buildCommand, or set it manually in the dashboard as:
#   bash build.sh
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
