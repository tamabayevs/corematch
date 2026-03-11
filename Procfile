web: cd backend && gunicorn api.app:create_app() --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: cd backend && python -m rq worker default pipeline --url $REDIS_URL
