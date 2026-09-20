"""
توجيه الجذر.

كل نقاط API تحت /api/v1/ — docs/architecture/api-contract.md
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health_check

API = "api/v1/"

urlpatterns = [
    # فحص صحي — يستخدمه Docker healthcheck و Dokploy
    path("healthz", health_check, name="healthz"),
    # أداة تشغيلية للفريق التقني فقط، لا لوحة أعمال
    path("django-admin/", admin.site.urls),
    path(f"{API}auth/", include("apps.accounts.urls")),
    # تطبيق العميل وشاشة الكاشير
    path(f"{API}", include("apps.pos.urls")),
    # لوحة التاجر — موزّعة على تطبيقات المجال لا مجمّعة في تطبيق واحد
    path(f"{API}", include("apps.ledger.urls")),
    path(f"{API}", include("apps.tenancy.urls")),
    path(f"{API}", include("apps.loyalty.urls")),
    path(f"{API}", include("apps.fraud.urls")),
    path(f"{API}", include("apps.campaigns.urls")),
    path(f"{API}", include("apps.billing.urls")),
    path(f"{API}schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        f"{API}docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

# مؤجّل بمفتاح ميزة — docs/planning/scope.md
if settings.FEATURE_PUBLIC_API:
    urlpatterns.append(path("public/v1/", include("apps.publicapi.urls")))

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
