# ══════════════════════════════════════════════════════════════
#  ولائي — نسخة العميل
#  تُخدَم على الجذر /  ولا تحتوي إلا ما يُعرض على العميل.
#  المحتوى المحذوف غير موجود في الصورة أصلًا — لا مجرد غير مرتبط.
# ══════════════════════════════════════════════════════════════
FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="walaee-client" \
      org.opencontainers.image.description="ولائي — العرض التقديمي والواجهات وعرض السعر"

RUN apk add --no-cache tzdata curl \
 && cp /usr/share/zoneinfo/Africa/Cairo /etc/localtime \
 && echo "Africa/Cairo" > /etc/timezone \
 && rm -rf /usr/share/nginx/html/*

# عدد عمّال متناسب مع حد المعالج — auto كان يشغّل 20 عاملًا على نصف نواة
RUN sed -i 's/^worker_processes.*/worker_processes 2;/' /etc/nginx/nginx.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

# الواجهات على الجذر مباشرة
COPY docs/demo/index.html    /usr/share/nginx/html/
COPY docs/demo/assets/       /usr/share/nginx/html/assets/
COPY docs/demo/present/      /usr/share/nginx/html/present/
COPY docs/demo/preview/      /usr/share/nginx/html/preview/
COPY docs/demo/customer/     /usr/share/nginx/html/customer/
COPY docs/demo/merchant/     /usr/share/nginx/html/merchant/
COPY docs/demo/admin/        /usr/share/nginx/html/admin/
COPY docs/demo/pricing/      /usr/share/nginx/html/pricing/

# المستند الوحيد المسموح
COPY docs/reports/Walaee_Pricing_Proposal_AR.pdf /usr/share/nginx/html/reports/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
