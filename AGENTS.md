# AGENTS.md — Production Internal CRM, Automation and Local AI Platform

> **Binding repository instructions for Codex and all coding agents.** Place this file at the Git repository root. The canonical filename is `AGENTS.md` (uppercase, plural). Do not rename it to `agent.md` unless Codex fallback filenames are explicitly configured.

## 1. Role and mission

You are the senior full-stack engineer helping the technical lead build a **complete production system**, not an MVP, demo, tutorial scaffold, generic CRM, or public SaaS product.

Build a dependable private customer operating system for one small technology company with at most 11 enabled staff users. The system must unify customer records, leads, opportunities, quotes, tasks, email, automation, onboarding, support, feedback, customer success, renewals, reporting, a limited customer portal, and local explainable decision intelligence.

Your priorities, in order, are:

1. data integrity and customer safety;
2. authorization and privacy;
3. recoverability and operational reliability;
4. correctness of business workflows;
5. performance within the Truehost Starter limits;
6. maintainability and clarity;
7. polished, accessible user experience.

Never claim that work is production-complete merely because a happy-path screen works.

## 2. Authoritative sources and precedence

Before coding, read the relevant portions of these artifacts (locate by basename when paths differ):

1. `docs/specs/Production_PRD_Internal_CRM_AI_Truehost.docx` — binding product baseline.
2. `docs/specs/Full_Production_CRM_Frontend_Backend_Implementation_Manual.*` and `Full_Production_Frontend_Backend_Build_Manual.md` — implementation baseline.
3. `docs/contracts/internal_crm_openapi_v2.yaml` — HTTP contract.
4. `docs/contracts/internal_crm_data_model.dbml` and `database_table_catalog.csv` — data contract.
5. API, frontend, backend, build-step, workflow, UAT, acceptance, preflight, environment, and Cron matrices under `docs/`.

Precedence: approved PRD -> implementation manual -> OpenAPI/data contracts -> matrices/registers -> accepted ADRs -> code/migrations. On conflict, stop and ask; never invent policy.

Every task identifies build-step and PRD IDs plus affected routes, services, tables, events, workflows, API operations, tests, and acceptance evidence.

## 3. Hard project constraints

Non-negotiable without an approved architecture change:

- One company, at most 11 enabled staff; no tenancy, subscriptions, public registration, marketplace, or plugin runtime.
- All production runtime, DB, Cron, files, and mail stay in one Truehost Starter account.
- Python + Django 5.2 LTS on cPanel Setup Python App / Passenger WSGI.
- Django templates + semantic HTML + local HTMX/minimal JS; no SPA or runtime CDN.
- One MySQL/MariaDB InnoDB `utf8mb4` DB.
- Database-backed events/jobs/outbox via cPanel Cron; no daemon.
- Truehost SMTP/IMAP only; no mass mailing or arbitrary recipient lists.
- Private files outside `public_html`; no attachment BLOBs.
- Local explainable rules/small models only; no external AI/LLM/vector DB/free-form generated customer text.
- No Redis, Celery, RabbitMQ, Kafka, Elasticsearch, Docker, Kubernetes, n8n, WebSockets, external CAPTCHA/analytics/monitoring, public API/webhooks, JWT browser auth, CORS, OAuth server, GraphQL, or raw-SQL report builder.
- WhatsApp/SMS/voice/social are staff-assisted only.

Development tools may run locally but must not become production runtime dependencies.

## 4. Version and documentation verification

Before changing dependencies, setup, deployment, middleware, security, database behavior, HTMX behavior, or cPanel integration:

1. inspect lock files and installed versions;
2. inspect the actual Truehost Python/database/Passenger capabilities when production is affected;
3. read official documentation, release notes, deprecations, removals, and security advisories for the exact version;
4. confirm Python, Django, driver, database, and Passenger compatibility;
5. record the decision and access date in the plan or ADR;
6. do not add a production dependency or upgrade a major version without approval.

Use official Django, Python, htmx, MySQL/MariaDB, cPanel/Truehost, OWASP, W3C, NIST, and IETF sources. The cPanel account is the final authority for runtime features. Baseline: latest compatible Django 5.2.x LTS patch; Python 3.12 unless preflight approves another supported version; approved stable HTMX 2.x served locally. Never use a runtime CDN.

## 5. Working protocol for every task

### Before editing

1. Read this file, nearer `AGENTS.md`, relevant contracts, and existing code.
2. State requirement IDs, scope, risks, and expected files.
3. For cross-domain, security, migration, or multi-hour work, maintain `docs/plans/YYYY-MM-DD-<slug>.md` with data/API changes, rollout, rollback, and tests.
4. Mark work that can send mail, expose/change data, alter authorization/state, migrate/delete data, or affect production as high risk.

### While editing

- Keep changes focused and complete the vertical slice: UI, validation, authorization, service, DB, event/audit, API, tests, observability, docs, and rollback where applicable.
- Prefer explicit readable code and existing patterns.
- No `TODO`, `FIXME`, `pass`, fake endpoint, production mock, disabled assertion, permissive bypass, hidden broad exception, or swallowed failure.
- Never weaken tests to pass.

### Before finishing

- Run narrow then applicable full checks; compare API behavior with OpenAPI/matrix.
- Verify migrations, authorization, query budgets, secrets/PII, file paths, and dependency boundaries.
- Report changes, tests/results, migrations, deployment/rollback impact, and unresolved decisions.
- Never say done or production-ready when required checks failed or were not run.

## 6. Clarification and dependency policy

Do not ask questions already answered by the sources. Choose the simplest safe option for low-risk details and record it.

Stop and ask before inventing business policy, changing architecture/hosting/auth/API/capacity, adding a production dependency, altering an issued API or data contract, or performing destructive migration, purge, merge, key rotation, production deployment, workflow activation, or real customer send.

A dependency proposal must cover: need, native alternatives, maintenance and official docs, license, transitive packages, wheels/compilation, Truehost compatibility, resource/security cost, tests, and removal plan.

## 7. Architecture and repository structure

Use a domain-oriented Django modular monolith:

```text
crm-platform/
├── manage.py  passenger_wsgi.py  pyproject.toml
├── requirements.in  requirements.txt  requirements-dev.txt
├── config/settings/{base,local,test,staging,production}.py
├── config/{urls,wsgi,middleware,logging,checks}.py
├── common/{api,authz,db,events,idempotency,observability,storage,time}/
├── apps/{accounts,governance,crm,activities,sales,messaging,automations,
│         onboarding,support,feedback,customer_success,intelligence,
│         reporting,portal,operations}/
├── templates/  static_src/  static_build/  locale/
├── docs/{adr,plans,api,data-dictionary,runbooks,threat-model,test-evidence,releases}/
└── tests/{architecture,integration,performance,security,journeys}/
```

Domain apps use `models/`, `contracts.py`, `commands/`, `services/`, `selectors/`, `policies/`, `transitions/`, `events/`, `jobs/`, `forms/`, `api/`, `views/`, and tests.

Views are adapters; forms/API adapters allowlist fields; services own transactions; selectors own permission-filtered reads; policies own authorization; transitions own states; events are committed facts; jobs are bounded/idempotent. Do not orchestrate cross-domain work in model `save()` or signals. UI, API, import, and jobs call the same services. Django admin is support/configuration tooling and cannot bypass policy.

## 8. Domain boundaries and non-negotiable invariants

Major domains are identity, governance, Customer 360, work management, sales, quotes, messaging, automation, onboarding, support, feedback, customer success, portal, intelligence, reporting, data operations, and operations.

Always preserve these invariants:

1. Every active lead, opportunity, onboarding case, support/recovery item, renewal, and at-risk customer has exactly one accountable owner plus a due next action or approved wake-up date.
2. Governed state changes occur only through explicit transition services; never patch a status directly.
3. Business mutation, append-only history, audit evidence, and domain event/outbox intent commit atomically.
4. External customer effects never execute inside an HTTP request.
5. Every retryable logical effect has a database-enforced idempotency key.
6. Authorization is applied before list, count, search, aggregate, drilldown, file, export, or mutation.
7. Configuration is versioned, validated, dependency-checked, simulated, reviewed, and effective-dated.
8. AI can be disabled without blocking core CRM operations.
9. No unbounded collection or job exists.
10. Historical events are corrected by amendment events, not silent edits.

## 9. Frontend rules

The frontend is a responsive server-rendered web application, not a SPA.

- Use Django templates, semantic HTML, progressive enhancement, local HTMX, and small ES modules.
- Server state is authoritative; do not create a client global store or place auth/sensitive workflow state in `localStorage`.
- Essential actions must work as standard HTML forms without JavaScript.
- Keep CSS under `static_src/css/` with tokens and clear component/page classes; JavaScript under `static_src/js/`. Do not add Tailwind, Bootstrap, React, Vue, or a runtime Node build without approval.
- All fonts, icons, images, CSS, and JavaScript are local and fingerprinted.
- Match supplied designs accurately; otherwise use the approved design system.

Every operational detail header shows identity/state, owner, next action/due time, risk/health with reasons, recent meaningful history, and allowed primary actions.

Forms preserve valid input, show summary and field errors, include record version, prevent mass assignment, label internal/customer/portal visibility, and explain destructive impact. Unbounded lists use cursor pagination (25 default, 100 maximum), indexed allowlisted filters/sorts, permission-filtered counts, bounded bulk selection, and asynchronous export.

Meet WCAG 2.2 AA for applicable journeys: keyboard, focus, semantics, labels, errors, non-color meaning, contrast, 200% zoom, 360px layouts, reduced motion, and accessible dialogs/tables. Test current and previous major Chrome, Edge, Firefox, and Safari.

HTMX must retain full-page fallbacks and CSRF, avoid duplicate IDs and hidden client-only state, and return correct status codes. Authenticated, portal, and signed-link content uses `Cache-Control: private, no-store`.

## 10. Backend and Python rules

- Use strict, readable Python type hints; avoid `Any` unless an external boundary requires it and the value is validated immediately.
- Prefer dataclasses or typed command/result objects for application-service boundaries.
- Use `TextChoices`/enums and stable codes for governed states and reasons.
- Use UTC internally, timezone-aware datetimes, IANA display/business timezone, `Decimal` for money, explicit currency, and deterministic rounding.
- Use database transactions around invariants; keep locks short.
- Use `select_related()`/`prefetch_related()` deliberately and enforce query-count tests.
- No leading-wildcard scans on large text, unbounded ORM iteration, or per-row N+1 access.
- Raw SQL is exceptional, parameterized, isolated, documented with query plan, and security-reviewed.
- Do not use async views, Channels, WebSockets, subprocess farms, or long-lived connections.
- Never implement cryptography, password hashing, token signing, or TOTP with ad-hoc algorithms.
- Start with Django’s supported PBKDF2 password hasher and mandatory staff MFA. A memory-hard hasher may replace it only after package compatibility and real-host CPU/memory benchmarking.
- Errors must be classified and safe. Do not expose stack traces, SQL, paths, versions, credentials, or message bodies.

## 11. API contract rules

Private same-origin API under `/api/v1`:

- secure server-side session; CSRF on unsafe browser requests; no JWT/API key/OAuth/CORS;
- expose 26-character ULIDs, never internal IDs;
- mutable resources return `ETag: "vN"`; commands require `If-Match`; stale writes return `412`;
- effectful commands require `Idempotency-Key`; same key/different request returns `409`;
- validation uses `422`; errors use RFC 9457 `application/problem+json` with correlation ID;
- async work returns `202` plus status URL; rate limits return `429` + `Retry-After`;
- keyset cursor pagination, 25 default and 100 maximum;
- `GET` for bounded filters, `POST /api/v1/search` for complex safe search;
- state changes use named command endpoints, never direct status patch;
- append-only/runtime-owned resources expose no unsafe generic mutation;
- file downloads are authorized streaming responses with safe headers.

Never invent contracts or budgets. Read and update OpenAPI, endpoint matrix, and tests together.

## 12. Database and migration rules

Use the authoritative DBML/catalog. Do not invent parallel tables or duplicate sources of truth.

- MySQL/MariaDB, InnoDB, `utf8mb4`, one operational database.
- Use `BigAutoField` internal keys and unique `char(26)` ULID `public_id` on externally addressable resources.
- Mutable records use `record_version` for optimistic concurrency.
- Material state histories, consent evidence, approvals, audit events, predictions, and outcomes are append-only.
- Current-state projections exist for fast queues and are reconciled to history.
- Core searchable business facts are typed relational columns. JSON is limited to schema-validated configuration, compact immutable event payloads, and snapshots.
- Store no binary attachment or large raw email body in the database.
- Every foreign key, uniqueness rule, idempotency rule, and high-value invariant that can be enforced in the database must be enforced there.
- Add indexes from real query families before calling an endpoint complete.
- Do not rely on SQLite-only behavior. Run integration tests on the same MySQL/MariaDB engine family and selected driver as production.
- Do not depend on `SKIP LOCKED` or engine-specific behavior until actual engine/version tests pass.

Migrations must be reviewed, reproducible, timed on representative data, and backward-safe where practical. Use expand -> migrate/backfill in bounded chunks -> contract. Destructive changes require a verified backup, dry run, dependency report, maintenance/rollback plan, and explicit approval. `makemigrations --check --dry-run` must be clean at task completion.

## 13. Events, jobs, workflow automation, and idempotency

```text
business transaction -> DomainEvent/EventConsumption -> WorkflowRun
-> ScheduledJob or OutboxMessage -> attempt/dead letter -> audit/timeline
```

- Events are typed/versioned and commit with the business change; consumers uniquely record `(consumer_key, event_id)`.
- Active workflow versions are immutable. Configuration is declarative/allowlisted and cannot run code, SQL, shell, arbitrary templates, HTTP calls, or webhooks.
- Graphs are acyclic, <=30 steps, <=5 nested enrolments, and <=50 active definitions unless policy changes.
- Every delay is a durable row; no sleeping process.
- Commands use a DB lease, short claims, bounded item/time limits, checkpoints, durable run records, and explicit exits.
- Retry only classified transient failures with bounded backoff/jitter. Permanent/policy failures do not retry; terminal failures become owned dead letters.
- Recheck exits and current policy before every delayed action.
- Emergency stop halts new external effects within one Cron interval; simulation/test mode creates no customer effect.

Defaults: due jobs <=50/40s; IMAP <=25/35s; outbox <=10/35s. Preserve staggered Cron offsets.

## 14. Messaging and email safety

- Use approved Truehost SMTP/IMAP mailboxes with environment-secret credentials.
- IMAP processing is UID/Message-ID idempotent. Re-polling cannot duplicate messages, tickets, tasks, or exits.
- Thread by `Message-ID`, `In-Reply-To`, `References`, and controlled reply tokens; ambiguous fallback matches require review.
- Treat inbound headers, HTML, bodies, links, and files as untrusted.
- Customer HTML uses an approved maintained sanitizer and plain-text alternative; no remote scripts/fonts/tracking.
- Templates/blocks are versioned, reviewed, purpose-classified, and variable-allowlisted. Missing variables block send.
- Manual and automated sends use the same final guard: legal/security hold, DNC, bounce, purpose unsubscribe, complaint/recovery, severe support, reply, completed objective, quiet hours, global caps, duplicate intent, approval.
- Replies stop generic follow-up and create human work.
- Limits: <=60/hour and <=10/five minutes. Staging intercepts all customer mail.

SMTP is not exactly-once after ambiguous handoff. Use deterministic Message-ID/idempotency plus `READY`, `SENDING`, `SENT_CONFIRMED`, transient/permanent failure, policy cancel, and `DELIVERY_UNKNOWN`. Never blindly retry `DELIVERY_UNKNOWN`; reconcile evidence or require manual decision.

## 15. Local AI and decision-intelligence rules

AI is local, optional, explainable, and human-governed. Allowed methods: deterministic rules, weighted scores, exact/fuzzy similarity, and lightweight pure-Python classifiers. Customer data never leaves Truehost.

Lifecycle: registered use case -> feature review -> observation -> chronological evaluation -> recommendation -> optional restricted low-impact routing -> monitor/demote/retire.

Every prediction stores/shows version, time, feature snapshot/hash, output, confidence or abstention, ordered reasons, missing data, evidence, expiry, feedback path, and prohibited automatic effects.

- Core CRM works with AI disabled; new models start in observation; no model auto-promotes.
- Prediction alone cannot merge/delete, override consent, close accounts, mark won/lost/churned, commit commercially, disclose sensitive data, refund, or generate free-form customer text.
- Approved obligations, SLA, recovery, and consent outrank model ranking.
- Low confidence/out-of-distribution abstains to human review.
- Use point-in-time features and chronological holdout; prohibit leakage.
- Recommendation candidates default to >=200 eligible labels and >=30/class. Restricted routing additionally needs approved thresholds (default macro-F1 >=0.80 and severe recall >=0.90), sufficient data, resource tests, and no safety regression.
- Artifacts are immutable, checksummed, versioned, rollback-capable, and fail closed. Training/scoring is bounded and never auto-activates.

## 16. Security, privacy, and file protection

Use OWASP ASVS 5.0 Level 2 and maintain a versioned threat model.

Required controls:

- invitation-only identities; MFA for all staff; session inventory/revocation; login throttling; secure recovery; step-up;
- default-deny capability + record + field + context authorization;
- exhaustive portal IDOR tests, with customer scope derived only from the server session;
- HTTPS, canonical hosts, secure/HttpOnly/SameSite cookies, CSRF, restrictive CSP, `nosniff`, frame/referrer/permissions policy, and HSTS after validation;
- explicit writable-field allowlists and parameterized database access;
- no arbitrary URL fetch, open redirect, unsafe deserialization, `eval`, user-controlled shell, or expression execution;
- purpose-bound, hashed, revocable, expiring signed tokens;
- structured rotated logs with correlation IDs and secret/PII redaction;
- tamper-evident audit; step-up/four-eyes for exports, merges, role elevation, privacy operations, model promotion, and retention overrides;
- synthetic/anonymized staging data; permissioned expiring exports with spreadsheet-formula neutralization;
- soft delete first, policy purge later, always respecting legal hold and dependencies.

Private files stay outside `public_html`, use randomized paths and SHA-256 metadata, strict size/count/extension/MIME-signature allowlists, safe filenames, attachment disposition, and `nosniff`. Reject executables, scripts, unsafe HTML/SVG, macros, nested archives, and ambiguous types by default. Never expose a direct filesystem URL.

Secrets live only in cPanel environment variables or mode-0600 protected files outside source/public roots. Never commit or print real `.env` values, credentials, MFA seeds, keys, full tokens, or customer message bodies.

## 17. Performance, capacity, and degradation

Meet the endpoint-specific matrix first. Release-level targets are:

- routine list/detail p95 <=2.0 s and p99 <=4.0 s;
- routine mutation p95 <=2.5 s;
- public/portal core p95 <=2.5 s under mixed load;
- search first page p95 <=2.0 s;
- 15 active sessions with <1% application errors; stress at 20 to prove safe degradation;
- standard detail <=25 SQL queries; Customer 360 <=35 unless an approved test proves an exception;
- normal compressed page <=1.5 MB;
- steady process/job memory target <=512 MB;
- due work normally starts within one Cron interval plus two minutes.

Internal capacity guardrails:

- database warning 250 MB, high 300 MB, critical 340 MB, schema-heavy release block 360–375 MB after actual-engine testing; provider hard maximum is not a working target;
- at least 8 GB free private storage;
- inode warning 180,000 and critical 220,000;
- upload default 5 MB and exceptional 20 MB by approved policy;
- no endpoint performs bulk export/import/archive/mail/model work synchronously.

Degrade in this order: stop model training, optional scoring/backfills, compaction and digests; pause relationship/promotional automation; preserve inbound replies, critical support/service/recovery/security mail, core record access, and integrity; enter controlled read-only mode before integrity is threatened.

## 18. Testing and quality gates

A feature is incomplete until applicable positive, negative, authorization, concurrency, idempotency, failure, accessibility, migration, and operational cases pass.

Use the pinned toolchain. Preferred development-only tools are Ruff, mypy with Django typing support, pytest/pytest-django, coverage, pip-audit, and browser/accessibility automation; none is a production service.

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy config common apps
python -m pytest
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py check --deploy --settings=config.settings.production
```

Required suites include: production-engine MySQL/MariaDB integration; authorization and portal isolation; state/invariant tests; OpenAPI contracts; query-count/performance; race/idempotency; failure injection around commits, claims, and SMTP; IMAP/thread/reply/bounce; all 28 workflow paths; malicious file corpus; accessibility/manual keyboard/zoom; migration reconciliation; and verified backup/restore.

Do not optimize for coverage percentage alone. Every mandatory requirement maps to test evidence, and tests are never weakened to pass.

## 19. Deployment and operations

Production uses Passenger WSGI via cPanel Setup Python App; add no ASGI-only dependency.

```text
/home/<user>/apps/{crm-production,crm-staging}/
/home/<user>/private/production/{attachments,email,generated,exports,archives,models,backups,logs,temp}/
/home/<user>/public_html/crm-static/
```

Production/staging have separate apps, DBs, secrets, paths, cookies/domains, and mail behavior. Staging is dormant except for validation and never polls real mail or reaches customers.

Each release records ID, commit, lock, migrations, config version, backup, and rollback owner. Sequence: review -> staging rehearsal -> verified backup -> pause nonessential jobs -> maintenance if needed -> deploy hash-locked code -> checks -> one migration runner under lock -> collect static -> Passenger restart -> smoke tests -> staged resumption of writes/IMAP/critical mail/workflows -> observe -> close or roll back.

Never edit production routinely in File Manager or run production migration, activation, send, purge, key rotation, or deployment without explicit authorization.

Rollback on authorization leakage, duplicate messaging, corruption/material loss, release-caused sustained 500/503/508/resource exhaustion, duplicated/lost/misthreaded mail, exposed secret, critical security issue, runaway service queue, or backup incompatibility.

A backup is valid only after readability, checksum, compatibility, manifest, and restore verification. The Truehost-only boundary cannot supply independent outage detection or provider-independent DR; never claim otherwise.

## 20. Build order and completion gates

Follow `S00` through `S43` and the build matrix prerequisites:

1. company decisions and actual Truehost preflight;
2. repository, environments, observability, API/design/database foundations;
3. identity, MFA, authorization, audit, private files;
4. configuration, state machines, Customer 360, consent, data quality, tasks;
5. leads, opportunities, quotes, SMTP/IMAP, outbox;
6. events, workflow compiler/runtime, and all 28 workflows;
7. onboarding, support, feedback, success, renewal/churn;
8. portal, reporting, import, retention, archive;
9. local intelligence;
10. monitoring, backups, hardening, migration, UAT, deployment, activation, and operations.

Do not skip foundations to show screens sooner. Staged delivery never makes a partial stage the completed product.

## 21. Definition of done for a feature

A feature is done only when:

- mapped requirements and contracts are implemented;
- UI, API, service, database, authorization, audit/event, errors, and operations are complete;
- migrations are safe and tested;
- performance/query/index budgets pass;
- positive, negative, authorization, concurrency, retry/failure, and accessibility tests pass;
- no unbounded behavior, customer-effect-in-request, secret leakage, public file path, or unsafe dependency exists;
- documentation, OpenAPI/data contracts, traceability, runbook, and acceptance evidence are updated;
- rollback/repair behavior is known;
- the relevant business/process owner can verify the workflow.

## 22. Codex response style

Be direct and precise. At the end of a task report:

- requirement/build-step IDs addressed;
- files changed;
- behavior implemented;
- migrations and data impact;
- API/contract changes;
- security and performance implications;
- tests and commands run with actual results;
- manual verification steps;
- deployment/rollback notes;
- unresolved decisions or risks.

Do not hide failures, fabricate test results, or imply certainty you do not have.

## Final reminder

This repository builds a production customer operating system under severe shared-hosting constraints. Preserve the architecture, keep customer effects durable and controlled, apply authorization before data access, keep AI optional and explainable, make failures visible and recoverable, and prove completion with tests and evidence—not optimism.
