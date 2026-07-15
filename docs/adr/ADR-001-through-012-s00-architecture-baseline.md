# ADR-001 through ADR-012 - S00 Architecture Baseline

Status: Accepted unless noted
Date: 2026-07-15
Owner: Oghenemaro
Build step: S00
Related requirements: CFG-001 through CFG-012, SEC-001 through SEC-037, NFR-001 through NFR-045, OPS-001 through OPS-030, TST-001 through TST-030

## Context

The approved PRD constrains the product to one internal company, at most 11 enabled staff users, one Truehost Starter account, Django 5.2 LTS over Passenger WSGI, one MySQL/MariaDB database, cPanel Cron, Truehost SMTP/IMAP, private filesystem storage, local assets, and local explainable AI only.

The architecture baseline is frozen in S00 so later steps do not introduce hidden runtime services, customer communication channels, or policy drift.

## Decision Set

| ADR | Decision | Status | Consequence |
|---|---|---|---|
| ADR-001 | Single-company modular monolith | Accepted | No tenant abstraction, public registration, subscription, marketplace, or plugin runtime is introduced. |
| ADR-002 | Django 5.2 LTS Python backend | Accepted | S02 must pin a compatible 5.2.x patch after S01 proves actual Truehost Python capability. |
| ADR-003 | Server-rendered templates with minimal local JavaScript and local HTMX | Accepted | No SPA, separate frontend deployment, runtime CDN, or browser-side authoritative state. |
| ADR-004 | One MySQL/MariaDB operational database | Accepted | No PostgreSQL dependency, alternate source of truth, attachment BLOB storage, or SQLite proof for production behavior. |
| ADR-005 | Database-backed Cron queue | Accepted | No Redis, Celery, RabbitMQ, Kafka, daemon, WebSocket worker, or long-running process. |
| ADR-006 | Truehost SMTP/IMAP only | Accepted | No mass mailing, arbitrary recipient upload, SMS, voice, WhatsApp, social automation, or external mail provider. |
| ADR-007 | Private filesystem for binaries and large bodies | Accepted | Files stay outside `public_html`; DB stores metadata/checksums, not attachment BLOBs or large raw message bodies. |
| ADR-008 | Local explainable AI only | Accepted | No external AI API, LLM, vector DB, free-form generated customer text, or opaque automatic high-impact decision. |
| ADR-009 | No general public API, webhooks, or plugin code | Accepted | API remains private same-origin; no OAuth server, CORS, JWT browser auth, GraphQL, public API key, marketplace, or arbitrary extension runtime. |
| ADR-010 | Production and lightweight staging in same Truehost account | Accepted with risk | Separate apps, DBs, paths, secrets, cookies, and mail behavior are required; correlated provider/account risk remains. |
| ADR-011 | Database-backed events/jobs/outbox with bounded retries | Accepted | External effects occur after durable intent through cPanel Cron; retry and dead-letter behavior must be explicit and idempotent. |
| ADR-012 | Monthly encrypted offline backup as non-runtime governance exception | Accepted with governance boundary | Recommended to reduce correlated provider-failure risk. It is not a production runtime dependency and requires signed operational procedure before go-live. |

## Cross-Cutting Consequences

- S01 remains mandatory before runtime approval.
- S02 must create pinned dependency locks and support evidence.
- S04 must implement private API conventions without public integration scope.
- S09 must implement default-deny authorization before customer records and workflows become available.
- S23/S24 must implement outbox and IMAP safety before customer mail automation.
- S35 must keep AI optional, explainable, and disableable.
- S37 must prove backup/restore rather than assume provider recovery.

## Alternatives Rejected by S00

| Alternative | Reason rejected |
|---|---|
| Public SaaS/multi-tenant architecture | Contradicts one-company, 11-staff model and increases authorization/privacy risk. |
| SPA/runtime CDN frontend | Contradicts server-rendered, local-asset, CSP-compatible architecture. |
| Redis/Celery/daemon workers | Contradicts Truehost Starter/cPanel Cron boundary. |
| External AI/LLM/vector DB | Contradicts local explainable AI and data-residency constraints. |
| External mail/SMS/WhatsApp automation providers | Contradicts Truehost-only runtime and low-volume relationship/service mail boundary. |
| Direct public API/webhooks | Contradicts private same-origin API and attack-surface constraints. |

## Change Control

Any change to these decisions requires a new ADR, PRD traceability update, owner approval from Oghenemaro, compatibility review, and affected matrix updates before implementation.
