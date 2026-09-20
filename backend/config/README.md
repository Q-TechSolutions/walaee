> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/architecture/`


# `config/` — إعدادات المشروع

| ملف | الغرض |
|---|---|
| `settings/base.py` | إعدادات مشتركة · التطبيقات · JWT · DRF · Celery |
| `settings/dev.py` | التطوير المحلي |
| `settings/prod.py` | الإنتاج — أسرار من البيئة فقط |
| `urls.py` | توجيه الجذر: `/api/v1/` · `/api/public/v1/` · `/django-admin/` |
| `celery.py` | تعريف التطبيق والطوابير المعزولة |
| `asgi.py` · `wsgi.py` | نقاط دخول الخادم |

**الطوابير:** `realtime` بعمّال مستقلين (تدوير الرموز والإشعارات) ·
`messaging` · `webhooks` · `analytics` · `billing` · `maintenance`.
عزل `realtime` غير قابل للتفاوض — حملة رسائل ضخمة يجب ألا تعطّل رموز الكاشير.

المرجع: `docs/architecture/` — قسم ٨ و ١١.
