# ولائي — أوامر التطوير الشائعة
.DEFAULT_GOAL := help
COMPOSE := docker compose -f docker-compose.dev.yml

help:            ## عرض كل الأوامر
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up:              ## تشغيل خدمات التطوير (قاعدة البيانات و Redis)
	$(COMPOSE) up -d

down:            ## إيقاف الخدمات
	$(COMPOSE) down

logs:            ## متابعة السجلات
	$(COMPOSE) logs -f --tail=100

ps:              ## حالة الخدمات
	$(COMPOSE) ps

migrate:         ## تطبيق الهجرات
	cd backend && python manage.py migrate

makemigrations:  ## توليد الهجرات
	cd backend && python manage.py makemigrations

seed:            ## بيانات بذرة للتطوير
	cd backend && python manage.py seed_demo

test:            ## كل الاختبارات مع التغطية
	cd backend && pytest --cov=apps --cov-report=term-missing

test-ledger:     ## اختبارات محرك القيود — التغطية 100% إلزامية
	cd backend && pytest apps/ledger --cov=apps.ledger --cov-fail-under=100

lint:            ## فحص التنسيق والأنماط
	cd backend && ruff check . && black --check .

fmt:             ## تنسيق تلقائي
	cd backend && ruff check --fix . && black .

schema:          ## توليد مخطط OpenAPI
	cd backend && python manage.py spectacular --file ../infra/openapi.yaml

reset-db:        ## حذف قاعدة البيانات وإعادة إنشائها (يمسح كل البيانات)
	$(COMPOSE) down -v && $(COMPOSE) up -d postgres redis

.PHONY: help up down logs ps migrate makemigrations seed test test-ledger lint fmt schema reset-db
