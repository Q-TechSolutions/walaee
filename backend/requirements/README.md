> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/architecture/`


# `requirements/`

| ملف | المحتوى |
|---|---|
| `base.txt` | Django · DRF · simplejwt · Celery · psycopg · redis · drf-spectacular |
| `dev.txt` | `-r base.txt` + pytest · pytest-django · factory-boy · ruff · black |
| `prod.txt` | `-r base.txt` + gunicorn · uvicorn · sentry-sdk |

الإصدارات المعتمدة في `docs/architecture/` — قسم ٢.
