#!/bin/sh
set -eu

# Keep the demo convenient without shipping a reusable signing key. The named
# Docker volume preserves the generated key across normal container restarts.
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    secret_file="${DJANGO_SECRET_KEY_FILE:-/app/data/.django-secret}"
    if [ ! -s "$secret_file" ]; then
        umask 077
        python -c "from pathlib import Path; import secrets; Path('$secret_file').write_text(secrets.token_urlsafe(64))"
    fi
    export DJANGO_SECRET_KEY="$(cat "$secret_file")"
fi

python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8000
