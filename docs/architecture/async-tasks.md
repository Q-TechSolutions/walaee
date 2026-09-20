# المهام غير المتزامنة — Celery

| المهمة | الجدولة | الطابور | الوظيفة |
|---|---|---|---|
| `pos.rotate_codes` | كل ٣٠ ثانية | `realtime` | توليد رموز جديدة لكل طرفية نشطة |
| `notify.push` | عند الحدث | `realtime` | إشعار Web Push — القناة المجانية |
| `webhooks.dispatch` | عند الحدث | `webhooks` | إطلاق مع توقيع وإعادة محاولة |
| `campaigns.send` | عند الجدولة | `messaging` | توجيه القنوات بالتكلفة وخصم الرصيد |
| `ledger.expire_balances` | يوميًا ٠٣:٠٠ | `maintenance` | قيد `expire` للأرصدة المنتهية |
| `ledger.notify_expiring` | يوميًا ١٠:٠٠ | `messaging` | تنبيه مجاني قبل الانتهاء بثلاثين يومًا |
| `reports.rollup` | كل ساعة | `analytics` | تجميع المؤشرات لتسريع اللوحات |
| `fraud.rescan` | يوميًا ٠٢:٠٠ | `analytics` | أنماط لا تُكتشف لحظيًا |
| `insights.generate` ○ | يوميًا ٠٤:٠٠ | `analytics` | التوصيات الذكية — مؤجّل |
| `billing.charge` | يوميًا ٠٦:٠٠ | `billing` | تحصيل الاشتراكات وإصدار الفواتير |
| `db.backup` | يوميًا ٠١:٠٠ | `maintenance` | نسخة احتياطية مشفّرة إلى التخزين البعيد |

---

## عزل الطوابير — غير قابل للتفاوض

طابور `realtime` له **عمّاله المستقلون** حتى لا تعطّل حملة رسائل ضخمة تدويرَ رموز الكاشير.

```
worker-realtime   celery -A config worker -Q realtime -c 4 --max-tasks-per-child 200
worker-default    celery -A config worker -Q messaging,webhooks,analytics,billing,maintenance -c 2
beat              celery -A config beat --scheduler django_celery_beat.schedulers:DatabaseScheduler
                  ⚠ نسخة واحدة فقط — نسختان تعنيان تنفيذًا مزدوجًا
```

---

## قاعدة الإطلاق

المهام التي تتبع عملية مالية تُطلَق من داخل `transaction.on_commit()` **فقط**.
إطلاقها قبل الـCOMMIT يعني احتمال إشعار العميل بنقاط لم تُكتب أصلًا.

```python
transaction.on_commit(lambda: notify_customer.delay(txn.id))
transaction.on_commit(lambda: dispatch_webhook.delay("transaction.created", txn.id))
```
