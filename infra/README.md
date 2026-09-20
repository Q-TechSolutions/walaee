> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/architecture/`


# `infra/` — البنية والنشر

```
infra/
├── docker/      Dockerfile.backend · Dockerfile.frontend · docker-compose.prod.yml
├── nginx/       الوكيل العكسي · TLS · تحديد المعدل · توجيه /api
├── postgres/    سكربتات التهيئة والامتدادات
├── scripts/     entrypoint · backup · restore · seed
└── ci/          فحوص الجودة وبوابات الدمج
```

## حاويات الإنتاج الست

| الحاوية | الصورة | الموارد |
|---|---|---|
| `nginx` | nginx:1.27-alpine | 128MB · 0.25 CPU |
| `api` | python:3.12-slim | 1GB · 1.0 CPU |
| `worker-realtime` | نفس api | 512MB · 0.5 CPU |
| `worker-default` | نفس api | 512MB · 0.5 CPU |
| `beat` | نفس api | **نسخة واحدة فقط** |
| `postgres` | postgres:16-alpine | 2GB · volume |
| `redis` | redis:7-alpine | 256MB |

## تنبيه

ملفات `Dockerfile` و`nginx.conf` و`docker-compose.yml` **في جذر المستودع**
تخص **موقع العرض** (`docs/demo`) وهي التي ينشرها Dokploy حاليًا.
لا تخلطها ببنية الإنتاج هنا.

المرجع: `docs/architecture/` — قسم ١٠.
