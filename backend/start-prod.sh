#!/bin/bash
# Production entrypoint: Django (gunicorn) and the Celery worker with beat share one
# container. If either process exits the container exits too, so Cloudflare restarts it
# on the next request instead of leaving half the app running.
set -e

# Web first, so the port is open quickly after a cold start
gunicorn config.wsgi:application \
    --bind 0.0.0.0:8080 --worker-class gthread --workers 1 --threads 4 \
    --timeout 60 --access-logfile - &

# Celery with beat. Migrations and the demo seed are off so a cold start stays fast. When a
# deploy adds a migration, uncomment the two lines, deploy, wait for the first request to
# finish, then comment them out again and redeploy. If a step fails the subshell exits, which
# stops the container (see wait -n below) and the error shows in the logs.
(
    # python manage.py migrate --noinput
    # python manage.py seed_demo_projects
    exec celery -A config worker --beat -Q default,integrations \
        --pool=threads --concurrency=4 --loglevel=info \
        --without-gossip --without-mingle --without-heartbeat
) &

# Forward the stop signal so every process shuts down cleanly
trap 'kill $(jobs -p) 2>/dev/null' TERM INT

wait -n
status=$?
kill $(jobs -p) 2>/dev/null || true
exit "$status"
