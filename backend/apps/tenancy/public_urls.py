"""
مسارات الدليل العام.

مفصولة عن `urls.py` لا مضافة إليه: كل ما في `urls.py` خلف مصادقة
ودور، وخلط مسار مفتوح بينها يجعل مراجعة «ما الذي يخرج بلا مصادقة؟»
تتطلب قراءة الملف كله بدل ملف من عشرة أسطر.
"""

from django.urls import path

from . import public_views

app_name = "public"

urlpatterns = [
    path("network", public_views.NetworkView.as_view(), name="network"),
]
