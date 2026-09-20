# يجعل تطبيق Celery متاحًا عند إقلاع Django — شرط عمل shared_task
from .celery import app as celery_app

__all__ = ("celery_app",)
