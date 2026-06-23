web: gunicorn "backend.api.app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
# Dedizierter Poll-Prozess. In Railway als eigenen Service starten und am
# Web-Service MAIL_POLL_IN_WEB=false setzen, sonst pollt jeder Web-Worker doppelt.
worker: python scripts/run_mail_poll_loop.py
