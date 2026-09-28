<div align="center">

# walaee · ولائي

**A multi-merchant loyalty platform for the Egyptian market**

[**Live demo →**](https://walaee.deplois.net) · [بالعربية](README.ar.md)

`Django 5` · `DRF` · `PostgreSQL 16` · `Redis 7` · `Celery` · `React 18` · `Vite`

</div>

---

## Try it now

Open <https://walaee.deplois.net> and sign in — no registration, no setup.
Every login screen shows the accounts and fills them in for you.

| Role | Where | Phone | Code / password |
|---|---|---|---|
| Customer | [`/app/`](https://walaee.deplois.net/app/) | `01111111111` | `123456` |
| Merchant owner | [`/merchant/`](https://walaee.deplois.net/merchant/) | `01000000001` | `Walaee@2026` |
| Branch manager | [`/merchant/`](https://walaee.deplois.net/merchant/) | `01000000002` | `Walaee@2026` |
| Cashier | [`/merchant/`](https://walaee.deplois.net/merchant/) | `01000000003` | `Walaee@2026` |
| Platform admin | [`/admin/`](https://walaee.deplois.net/admin/) | `01000000000` | `Walaee@2026` |

Two more customers exist — `01222222222` and `01333333333`, same code.

The deployment carries twelve months of generated history: ~5,000 customers,
~23,000 transactions, 96 branches across 27 governorates. Every balance
reconciles against its ledger.

> **These are demo accounts on a demo deployment.** Anyone who reads this page
> can sign in. Only the phone numbers listed in `DEMO_LOGIN_PHONES` accept a
> fixed code; every other number goes through the full OTP path.

Also live: [`/demo/`](https://walaee.deplois.net/demo/) — the approved
interactive prototype the screens were built against, and
[`/api/v1/public/network`](https://walaee.deplois.net/api/v1/public/network) —
the merchant directory, no authentication.

---

## What it does

Small and mid-size merchants lose customers without knowing why, and the
loyalty tools available to them force one model on everyone. walaee gives each
merchant **six loyalty models in one system** — points, stamps, visits,
cashback, rewards, gifts — and lets them run more than one at a time. A café
wants stamps, a pharmacy wants points, a restaurant wants cashback.

For the customer it is one app holding every card, with a single identity
across merchants.

**Proof of purchase is the hard part**, and it is answered concretely: the
merchant's screen shows a QR code that rotates every 30 seconds and is consumed
once. The customer scans it, enters the invoice amount, and the merchant
confirms from their dashboard. Every grant is tied to an invoice number, its
amount, a branch and a cashier. No new hardware; a phone or a cheap tablet is
enough. A manual path exists for when scanning is not possible.

### Three interfaces, one domain

| Path | What |
|---|---|
| `/` | Public page — coverage map and merchant directory |
| `/app/` | Customer wallet (PWA) — cards, rewards, scan, activity |
| `/merchant/` | Merchant dashboard — 11 screens including the cashier terminal |
| `/admin/` | Platform console — 7 screens |
| `/api/v1/` | REST API · [`/api/v1/docs/`](https://walaee.deplois.net/api/v1/docs/) for the interactive schema |

---

## How it is built

### The ledger is the centre of the system

Loyalty points are a financial promise. A merchant who cannot defend the
number does not trust the platform, and a customer who loses points leaves.
So the balance is **not** a column someone updates:

- **`LedgerEntry` is append-only.** No update, no delete — corrections are a
  reversing entry. PostgreSQL triggers enforce it below the ORM, so even `psql`
  cannot rewrite history.
- **`apply_entry()` is the only writer.** It locks the balance row with
  `SELECT FOR UPDATE` before reading anything it decides on, so two concurrent
  taps cannot grant twice.
- **`verify_ledger` re-sums every entry** against its snapshot and exits
  non-zero on any drift. It runs nightly, and after every restore.

A balance is a cached sum. The entries are the truth.

### Layout

```
backend/apps/          12 Django apps, split by domain
  ledger/              the engine — entries, balances, reports, insights
  loyalty/             programmes, rules, rewards, memberships
  pos/                 QR codes, scanning, transaction confirmation
  fraud/               anomaly rules over confirmed transactions
  campaigns/           segments and the channel router
  billing/             plans, subscriptions, invoices, message credit
  tenancy/             organisation → brand → branch → terminal → staff
  accounts/  audit/  common/  publicapi/  insights/

frontend/              npm workspaces, one shared package
  shared/              components, i18n, theme, API client, design tokens
  landing/  customer-pwa/  merchant-dashboard/  admin-panel/

infra/                 Dockerfiles, nginx, PostgreSQL hardening, backup scripts
docs/                  architecture, deployment, and the interactive prototype
```

Business logic lives in `services.py` (or `rules.py` for loyalty). Views stay
thin. The hierarchy — organisation, brand, branch, terminal, user — exists from
day one even where it is not used yet, because adding it after launch means
migrating data and rewriting permissions and reports.

### Interface decisions

- **Arabic-first, right to left.** All source CSS uses logical properties
  exclusively, so switching to English flips the whole layout with no style
  changes at all.
- **gettext-style i18n**: the Arabic string *is* the message id, so a missing
  translation falls back to Arabic rather than to a bare key. ~1,030 strings.
- Numerals, currency, dates and plural forms follow the chosen locale.
- Light / dark / system theme, applied before first paint, shared across all
  four apps on one origin.
- The customer app is a **PWA** — no app store, no review cycles, no separate
  iOS and Android teams, and near-zero install friction for someone standing at
  a till.

### Tests

569 tests. The ledger engine holds **100% coverage as a merge gate**; the
ledger app as a whole holds 95%. CI also fails on an ungenerated migration or
an OpenAPI schema warning.

Tests are written against the behaviour that matters rather than the method
that implements it — what breaks, who notices, and what it costs.

---

## Run it locally

You need Docker 24+ and Compose v2. Python 3.12 and Node 22 if you want to run
the backend outside a container.

### Everything in containers

```bash
git clone https://github.com/mohamedN2018/walaee.git
cd walaee
cp .env.local .env          # works as-is — nothing to fill in
docker compose up -d --build
```

First start takes a couple of minutes: it migrates, seeds 96 branches, creates
the demo accounts, and then serves while twelve months of activity generate in
the background.

Open <http://localhost:8081> and sign in with the accounts in the table above.

### Backend on the host, services in containers

Faster to iterate on — you get auto-reload and breakpoints.

```bash
cp .env.local .env
make up                     # PostgreSQL + Redis only
make install
make migrate
make seed                   # demo data
make run                    # http://localhost:8000
```

In another terminal:

```bash
make web-landing            # http://localhost:5172
make web-customer           # http://localhost:5173
make web-merchant           # http://localhost:5174
make web-admin              # http://localhost:5175
```

`make help` lists everything.

### Tests and checks

```bash
make test                   # full suite with coverage
make test-ledger            # the engine — 100% required
make lint                   # ruff + black
make verify-ledger          # every balance against its entries
```

---

## Deploy it

The repository deploys from its root with no configuration:

```bash
cp .env.production .env     # change SECRET_KEY and POSTGRES_PASSWORD
docker compose -f docker-compose.yml up -d --build
```

On Dokploy, Coolify or anything that builds from Git: point it at the
repository, paste `.env.production` into the environment panel, and attach your
domain to the **`web`** service on port **80**. The deploy file publishes no
host port — the reverse proxy reaches the container over the Docker network,
which avoids both port collisions on a shared host and a side door serving the
app over plain http.

[`docs/DEPLOY.md`](docs/DEPLOY.md) covers the rest: hardening the database,
backups and restore, scheduled tasks, and a table of deployment failures with
their causes.

---

## Status

Working and deployed. What is deliberately **not** built:

- **Public API and webhooks** — behind `FEATURE_PUBLIC_API`, unused until there
  is a real integration partner.
- **Machine learning** — the report this was scoped from rejects the label for
  year one. Three statistical rules ship instead, and they are honest about
  their sample size: at-risk customers measured against each customer's own
  visit interval, a suggested reward value from the average invoice, and the
  best day and hour to send a campaign. Each refuses to answer below a
  threshold rather than return a number built on nothing.
- **SMS and WhatsApp delivery** — the channel router is built and ordered by
  cost (web push → WhatsApp → SMS), but no provider is contracted, so messages
  are logged rather than sent.

Three decisions are still the owner's: the target sector and geography, the
local SMS provider, and the payment gateway.

---

## Documentation

| | |
|---|---|
| [`README.ar.md`](README.ar.md) | This document in Arabic |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Deployment, backups, troubleshooting |
| [`docs/architecture/`](docs/architecture/) | Data model, API contract, async tasks, security, testing |
| [`docs/planning/`](docs/planning/) | Approved scope and the decisions behind it |
| [`/demo/`](https://walaee.deplois.net/demo/) | The interactive prototype |

Code comments and commit messages are in Arabic — that is the working language
of the team that maintains it.
