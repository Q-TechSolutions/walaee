"""نقاط تشغيلية لا تخص مجالًا بعينه."""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    """
    فحص صحي لـ Docker و Dokploy.

    يتحقق من قاعدة البيانات فعليًا: خادم يرد 200 وقاعدته ساقطة
    يعني نشرًا يبدو ناجحًا بينما كل طلب حقيقي يفشل.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # pragma: no cover - يُختبر يدويًا بإسقاط القاعدة
        return JsonResponse({"status": "unhealthy", "database": str(exc)}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
