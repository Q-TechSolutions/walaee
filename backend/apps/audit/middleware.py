"""يلتقط IP والمتصفح لكل طلب ليستخدمهما سجل التدقيق."""

from .context import clear_audit_context, set_audit_context


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")

        set_audit_context(
            ip=ip,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            path=request.path,
        )
        try:
            return self.get_response(request)
        finally:
            # التنظيف إلزامي: الخيط يُعاد استخدامه لطلب آخر
            clear_audit_context()
