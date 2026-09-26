# ولائي — أوامر التطوير
# التشغيل من جذر المستودع.  `make help` يعرض كل شيء.
.DEFAULT_GOAL := help

COMPOSE     := docker compose
# ‏--env-file إلزامي: Compose يقرأ متغيرات التداخل من الملف
# المجاور لملف compose لا من جذر المستودع
PROD        := docker compose --env-file .env -f infra/docker/docker-compose.prod.yml
PY          := .venv/Scripts/python.exe
MANAGE      := cd backend && ../$(PY) manage.py

# على لينكس و macOS المسار مختلف
ifeq ($(OS),)
PY := .venv/bin/python
endif

help:            ## عرض كل الأوامر
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ══════════════ البيئة ══════════════

venv:            ## إنشاء البيئة الافتراضية
	python -m venv .venv

install:         ## تثبيت اعتماديات التطوير
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r backend/requirements/dev.txt

env:             ## إنشاء .env من القالب
	@test -f .env || cp .env.example .env
	@echo "✓ .env جاهز — راجع القيم قبل التشغيل"

# ══════════════ الخدمات المحلية ══════════════

up:              ## تشغيل PostgreSQL و Redis
	$(COMPOSE) up -d

down:            ## إيقاف الخدمات
	$(COMPOSE) down

logs:            ## متابعة سجلات الخدمات
	$(COMPOSE) logs -f --tail=100

ps:              ## حالة الخدمات
	$(COMPOSE) ps

# ══════════════ Django ══════════════

run:             ## تشغيل خادم التطوير على 8000
	$(MANAGE) runserver 127.0.0.1:8000

migrate:         ## تطبيق الهجرات
	$(MANAGE) migrate

makemigrations:  ## توليد الهجرات
	$(MANAGE) makemigrations

superuser:       ## إنشاء مستخدم خارق
	$(MANAGE) createsuperuser

seed:            ## بيانات تجريبية للتطوير
	$(MANAGE) seed_demo

reseed:          ## مسح البيانات التجريبية وإعادة إنشائها
	$(MANAGE) seed_demo --reset

shell:           ## صدفة Django
	$(MANAGE) shell

schema:          ## توليد مخطط OpenAPI إلى infra/openapi.yaml
	$(MANAGE) spectacular --file ../infra/openapi.yaml

# ══════════════ Celery ══════════════

worker:          ## عامل الطابور الحسّاس
	cd backend && ../$(PY) -m celery -A config worker -Q realtime -c 4 -l info

worker-default:  ## عامل الطوابير الباقية
	cd backend && ../$(PY) -m celery -A config worker \
		-Q messaging,webhooks,analytics,billing,maintenance -c 2 -l info

beat:            ## مجدول المهام — نسخة واحدة فقط
	cd backend && ../$(PY) -m celery -A config beat \
		--scheduler django_celery_beat.schedulers:DatabaseScheduler -l info

# ══════════════ الواجهات ══════════════

web-install:     ## تثبيت اعتماديات الواجهات
	cd frontend && npm install

web-landing:     ## الصفحة العامة — 5172
	cd frontend && npm run dev:landing

web-customer:    ## تطبيق العميل — 5173
	cd frontend && npm run dev:customer

web-merchant:    ## لوحة المتجر — 5174
	cd frontend && npm run dev:merchant

web-admin:       ## لوحة إدارة المنصة — 5175
	cd frontend && npm run dev:admin

web-build:       ## بناء الواجهات الأربع للإنتاج
	cd frontend && npm run build

# ══════════════ الجودة ══════════════

test:            ## كل الاختبارات مع التغطية
	cd backend && ../$(PY) -m pytest --cov=apps --cov-report=term-missing

test-fast:       ## الاختبارات بلا تغطية ولا تزامن
	cd backend && ../$(PY) -m pytest -q -m "not concurrency" --no-cov

test-ledger:     ## محرك القيود — ١٠٠٪ إلزامية على المحرك
	# القاعدة المعمارية تخصّ المحرك نفسه: النماذج والخدمات، أي كل
	# سطر يمسّ الرصيد. التقارير والعروض في نفس التطبيق لكنها قراءة
	# فقط — لها بوابة أدنى منفصلة حتى لا تميّع الرقم الأهم.
	cd backend && ../$(PY) -m pytest apps/ledger \
		--cov=apps.ledger.services --cov=apps.ledger.models \
		--cov-report=term-missing --cov-fail-under=100

test-ledger-all: ## تطبيق القيود كاملًا — ٩٥٪ حد أدنى
	cd backend && ../$(PY) -m pytest apps/ledger \
		--cov=apps.ledger --cov-report=term-missing --cov-fail-under=95

lint:            ## فحص التنسيق والأنماط
	$(PY) -m ruff check backend
	$(PY) -m black --check backend

fmt:             ## تنسيق تلقائي
	$(PY) -m ruff check --fix backend
	$(PY) -m black backend

check:           ## فحص Django + هجرات غير مولَّدة
	$(MANAGE) check --deploy --fail-level WARNING || true
	$(MANAGE) makemigrations --check --dry-run

verify:          ## كل فحوص ما قبل الدمج
	$(MAKE) lint
	$(MAKE) web-build
	$(MAKE) test-ledger
	$(MAKE) test-ledger-all
	$(MAKE) test

# ══════════════ قاعدة البيانات ══════════════

reset-db:        ## حذف قاعدة البيانات وإعادة إنشائها (يمسح كل شيء)
	$(COMPOSE) down -v
	$(COMPOSE) up -d
	@echo "انتظر قليلًا ثم: make migrate seed"

psql:            ## صدفة psql
	$(COMPOSE) exec postgres psql -U walaee -d walaee

verify-ledger:   ## تدقيق سلامة كل الأرصدة مقابل قيودها
	$(MANAGE) verify_ledger

schedule:        ## تثبيت جدول المهام الدورية
	$(MANAGE) install_schedule

backup:          ## نسخة احتياطية من قاعدة الإنتاج
	bash infra/scripts/backup.sh

restore:         ## استرجاع نسخة — restore FILE=backups/x.sql.gz
	bash infra/scripts/restore.sh $(FILE)

harden-db:       ## تطبيق حارس append-only (للإنتاج لا للتطوير)
	$(COMPOSE) exec -T postgres psql -U walaee -d walaee \
		< infra/postgres/02-append-only.sql

# ══════════════ الإنتاج ══════════════

prod-build:      ## بناء صور الإنتاج
	$(PROD) build

prod-up:         ## تشغيل تركيبة الإنتاج
	$(PROD) up -d

prod-down:       ## إيقاف تركيبة الإنتاج
	$(PROD) down

prod-logs:       ## سجلات الإنتاج
	$(PROD) logs -f --tail=100

.PHONY: help venv install env up down logs ps run migrate makemigrations \
        web-install web-customer web-merchant web-admin web-build \
        superuser seed reseed shell schema worker worker-default beat \
        test test-fast test-ledger test-ledger-all lint fmt check verify reset-db psql \
        harden-db verify-ledger schedule backup restore \n        prod-build prod-up prod-down prod-logs
