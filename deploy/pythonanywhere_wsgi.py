"""
Paste the contents of this file into PythonAnywhere's WSGI configuration file
(Web tab -> "WSGI configuration file"), replacing everything that is there.

Only change YOUR_USERNAME (and the folder name if you didn't call it `sarab`).
All other settings (SECRET_KEY, ALLOWED_HOSTS, n8n URL ...) come from the
`.env` file that lives next to manage.py — see DEPLOY_PYTHONANYWHERE.md.
"""
import os
import sys

PROJECT_DIR = '/home/YOUR_USERNAME/sarab'
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
