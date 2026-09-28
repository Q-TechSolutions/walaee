# البنية على Docker والنشر

## تركيبة الإنتاج — ست حاويات

| | الخدمة | الصورة | الدور | الموارد |
|---|---|---|---|---|
| ◱ | `nginx` | `nginx:1.27-alpine` | الملفات الثابتة · إنهاء TLS · تحديد المعدل · توجيه `/api` | 128 MB · 0.25 CPU |
| ◈ | `api` | `python:3.12-slim` | Django + gunicorn بعمّال uvicorn · العمّال = ‎2×CPU+1‎ | 1 GB · 1.0 CPU |
| ◉ | `worker` | نفس صورة `api` | نسختان: واحدة لـ `realtime` وأخرى للباقي | 512 MB · 0.5 CPU |
| ◷ | `beat` | نفس صورة `api` | مجدول Celery — **نسخة واحدة فقط** | 256 MB · 0.1 CPU |
| ◫ | `postgres` | `postgres:16-alpine` | مجلد بيانات دائم + نسخ احتياطي يومي مشفّر | 2 GB · 1.0 CPU · volume |
| ◇ | `redis` | `redis:7-alpine` | رموز QR بـ TTL · كاش الجلسات · وسيط الطوابير · `appendonly yes` | 256 MB · 0.25 CPU |

---

## مقتطف `docker-compose.yml`

```yaml
services:
  api:
    build: { context: ., dockerfile: infra/docker/Dockerfile.backend }
    command: >
      gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker
      --bind 0.0.0.0:8000 --workers 4 --max-requests 1000
    env_file: [.env]
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_started }
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/healthz"]
      interval: 30s

  worker-realtime:                 # عامل معزول للطابور الحسّاس
    command: celery -A config worker -Q realtime -c 4 --max-tasks-per-child 200

  worker-default:
    command: celery -A config worker -Q messaging,webhooks,analytics,billing,maintenance -c 2

  beat:
    command: celery -A config beat --scheduler django_celery_beat.schedulers:DatabaseScheduler
    deploy: { replicas: 1 }        # نسخة واحدة فقط — إلزامي

  postgres:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
```

---

## خط النشر

| # | الخطوة | الأداة | يفشل البناء إذا |
|---|---|---|---|
| ١ | فحص التنسيق والأنماط | `ruff` + `black --check` | أي مخالفة |
| ٢ | تشغيل الاختبارات | `pytest --cov` | تغطية `ledger` أقل من ١٠٠٪ |
| ٣ | فحص الهجرات | `makemigrations --check` | وجود هجرة غير مُولَّدة |
| ٤ | فحص أمني | `pip-audit` + `bandit` | ثغرة عالية الخطورة |
| ٥ | بناء الصورة ودفعها | Docker Buildx → السجل | فشل البناء |
| ٦ | تطبيق الهجرات | `migrate --noinput` | خطأ في الهجرة ← تراجع تلقائي |
| ٧ | نشر متدرّج | Dokploy (Zero-downtime) | فشل الفحص الصحي |
