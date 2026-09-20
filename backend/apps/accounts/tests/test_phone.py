"""
تطبيع أرقام الهواتف.

هذه الاختبارات تحمي من أسوأ عطل صامت في المنصة: نفس العميل يُسجَّل
مرتين بصيغتين مختلفتين لرقمه، فينقسم رصيده ويشتكي للتاجر.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.validators import normalize_phone


class TestNormalizePhone:
    @pytest.mark.parametrize(
        "raw",
        [
            "01012345678",
            "+201012345678",
            "00201012345678",
            "201012345678",
            "010 1234 5678",
            "010-1234-5678",
            "(010) 1234 5678",
            "٠١٠١٢٣٤٥٦٧٨",
            "  01012345678  ",
        ],
    )
    def test_all_forms_converge(self, raw):
        assert normalize_phone(raw) == "+201012345678"

    def test_empty_returns_empty(self):
        assert normalize_phone("") == ""
        assert normalize_phone(None) == ""

    def test_eastern_arabic_digits(self):
        assert normalize_phone("۰۱۰۱۲۳۴۵۶۷۸") == "+201012345678"

    def test_foreign_number_preserved(self):
        assert normalize_phone("+966501234567") == "+966501234567"

    def test_letters_rejected(self):
        with pytest.raises(ValidationError):
            normalize_phone("+2010ABCD5678")


@pytest.mark.django_db
class TestCustomerPhoneStorage:
    def test_saved_normalized(self):
        from apps.accounts.models import Customer

        customer = Customer.objects.create(phone="01099887766")
        assert customer.phone == "+201099887766"

    def test_duplicate_forms_collide(self):
        """
        الصيغتان تشيران لنفس الشخص، فالقيد الفريد يجب أن يمنع الثانية.
        هذا هو الضمان الحقيقي ضد انقسام الرصيد.
        """
        from django.db import IntegrityError

        from apps.accounts.models import Customer

        Customer.objects.create(phone="01099887766")

        with pytest.raises(IntegrityError):
            Customer.objects.create(phone="+201099887766")
