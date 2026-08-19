# ============================================================
#  walaee — نموذج العرض التفاعلي (Static Demo)
#  صورة nginx خفيفة تخدم معرض الواجهات + العرض التقديمي + التقارير
#  جاهزة للنشر على Dokploy / Coolify / أي مضيف يدعم Docker
# ============================================================
FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="walaee-demo" \
      org.opencontainers.image.description="ولائي — معرض الواجهات والعرض التقديمي" \
      org.opencontainers.image.vendor="walaee"

# منطقة زمنية وأدوات الفحص الصحي
RUN apk add --no-cache tzdata curl \
 && cp /usr/share/zoneinfo/Africa/Cairo /etc/localtime \
 && echo "Africa/Cairo" > /etc/timezone \
 && rm -rf /usr/share/nginx/html/*

COPY nginx.conf /etc/nginx/conf.d/default.conf

# الواجهات
COPY demo/ /usr/share/nginx/html/demo/

# التقارير (المعرض يربط عليها بمسار نسبي ../)
COPY Walaee_Analysis_Report_AR.pdf      /usr/share/nginx/html/
COPY Walaee_Executive_Brief_Book_Mobile.pdf /usr/share/nginx/html/

# nginx:alpine يشتغل بمستخدم غير جذري داخليًا عبر master/worker
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
