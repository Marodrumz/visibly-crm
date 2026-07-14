# Full Production Frontend and Backend Build Manual
## Internal CRM, Automation and Local AI Decision-Intelligence Platform

**Build classification:** complete production implementation; not an MVP, prototype, demo, generic scaffold or public SaaS  
**Deployment boundary:** one Truehost WebHosting Starter account; cPanel Setup Python App / Passenger WSGI; one MySQL/MariaDB database; cPanel Cron; Truehost SMTP/IMAP; private account filesystem; no external runtime service  
**Company model:** one internal company, up to 11 enabled staff, invite-only portal users  
**Source baseline:** `Production_PRD_Internal_CRM_AI_Truehost.docx`, version 1.0, 77 pages, issued 11 July 2026  
**Companion contracts:** complete endpoint matrix, OpenAPI 3.1 contract, frontend screen matrix, backend service matrix, database catalogue/DBML, requirements/workflows/UAT/acceptance registers

---

## 1. How to use this manual

This manual is an execution order. The numbered steps are not separate MVP releases. They are dependency-controlled work packages that together form the complete production release. The company must not represent the product as complete until all steps, production acceptance checks, migration, independent security review and restore drill have passed.

Every step contains:

- a plain-language objective and reason;
- exact frontend screens and interaction behavior;
- backend services, transaction boundaries and persistence;
- the API operations introduced in that step;
- representative exact wire contracts, while the companion endpoint matrix and OpenAPI file contain every operation;
- security, performance, test and failure requirements;
- an objective definition of success.

“Without errors” cannot be guaranteed by a document or by any engineer. Production engineering replaces that impossible promise with stronger controls: explicit invariants, schemas, database constraints, independent review, negative tests, failure injection, endpoint budgets, staged deployment, rollback, verified backups and measured restore. A step is incomplete when only its happy-path screen works.

---

## 2. Locked production architecture

```text
Staff browser / customer portal / signed public forms
                         |
                       HTTPS
                         |
              cPanel web server + Passenger WSGI
                         |
               Django 5.2 LTS modular monolith
       +-----------------+-------------------+
       |                 |                   |
Server-rendered UI   Private JSON API   Domain/policy services
       |                 |                   |
       +--------- short DB transaction ------+
                         |
                  MySQL / MariaDB
 records | histories | events | jobs | outbox | audit | aggregates
                         |
          +--------------+----------------+
          |                               |
 Private filesystem                 cPanel Cron commands
 files, bodies, exports,            IMAP, SMTP, due jobs,
 archives, models, logs             SLA, metrics, backups
                                          |
                                  Truehost SMTP / IMAP
```

### 2.1 Technology lock

| Concern | Production choice | What must not be introduced |
|---|---|---|
| Backend | Python supported by actual cPanel; Django 5.2 LTS latest compatible 5.2.x patch | Microservices, always-on worker, Docker, VPS-only service |
| Web runtime | cPanel Setup Python App / Passenger WSGI | Custom daemon, WebSocket dependency |
| Frontend | Django templates, semantic HTML, locally bundled HTMX and minimal vanilla JS | Separate React/Next/Vue deployment, runtime CDN |
| Database | One InnoDB MySQL/MariaDB database, `utf8mb4` | PostgreSQL dependency, BLOB attachment storage, alternate source of truth |
| Queue | Durable database events/jobs/outbox with cPanel Cron | Redis, Celery, RabbitMQ, Kafka |
| Cache | Browser/static caching and small request-local memoization only | Redis/Memcached/file cache or cached authorization/consent |
| Files | Private filesystem outside public root; metadata/checksum in DB | Public media URLs, user-controlled paths |
| Email | Truehost SMTP/IMAP, low-volume relationship/service messages | Mass mailing, arbitrary recipient upload |
| AI | Local rules, weighted scores and small pure-Python statistical models | External model API, LLM, vector database, generated free-form customer text |
| Monitoring | Internal health evidence, command heartbeats, logs, cPanel Resource Usage | Claim of independent provider-outage detection |

### 2.2 Non-negotiable invariants

1. No external customer effect is performed inside an HTTP request.
2. No governed state is changed by directly patching a status field.
3. Every active operational record has one accountable owner and a next action or approved wake-up date.
4. Business change, history, audit and domain-event/outbox intent commit atomically.
5. Every retryable effect has a database uniqueness key.
6. Authorization is applied before list, count, search, drilldown, export or file retrieval.
7. Automation configuration cannot execute code, SQL, shell, templates or arbitrary network calls.
8. AI may be disabled without blocking core operation.
9. Every unbounded collection is paginated or processed by a bounded job.
10. Provider, database, mailbox and backup limits are measured and trigger controlled degradation before hard failure.

---

## 3. Repository and code organization

```text
crm-platform/
├── manage.py
├── passenger_wsgi.py
├── pyproject.toml
├── requirements.in
├── requirements.txt                 # pinned with hashes
├── config/
│   ├── settings/{base,local,test,staging,production}.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── middleware.py
│   ├── logging.py
│   └── checks.py
├── common/
│   ├── api/                          # envelopes, problems, pagination
│   ├── authz/                        # capability/record/field policies
│   ├── db/                           # base models, locks, transactions
│   ├── events/                       # shared event contracts
│   ├── idempotency/
│   ├── observability/
│   ├── storage/
│   └── time/
├── apps/
│   ├── accounts/ governance/ crm/ activities/ sales/
│   ├── messaging/ automations/ onboarding/ support/
│   ├── feedback/ customer_success/ intelligence/
│   ├── reporting/ portal/ operations/
├── templates/
├── static_src/
├── static_build/
├── locale/
├── docs/{adr,api,data-dictionary,runbooks,threat-model,test-evidence,releases}/
└── tests/{architecture,integration,performance,security,journeys}/
```

Inside each domain app, keep persistence, commands, services, selectors, policies, events, jobs, forms, API views and HTML views separate. HTML, API, imports and jobs call the same application service; they do not duplicate business logic.

---

## 4. Frontend production rules

- Server-render the authoritative state. HTMX may replace bounded fragments but never becomes a client-side state store.
- Every operational detail header shows status, owner, next action/due time, risk/score and recent history.
- Mutating forms retain valid input, display an error summary and field errors, and use clear destructive-impact text.
- Every long operation returns a job/status page. No spinner waits for import, export, archive, model training, bulk recalculation or mail batch.
- Every list supports bounded pagination, allowlisted filters/sort, saved views where useful, column selection and export only by permission.
- Internal, restricted, customer-visible and portal-visible artifacts have persistent labels.
- Status never relies on color alone. Critical flows work at 360 CSS pixels, 200% zoom and keyboard-only.
- A `412 Precondition Failed` conflict shows the newer values and permits safe refresh/reapply; it never silently overwrites.
- All CSS, JavaScript, icons and fonts are local, fingerprinted and CSP-compatible.

## 5. Backend production rules

- Views are adapters; services own transactions and invariants; selectors own permission-filtered reads; policies decide authorization and state transitions.
- Use current-state columns for fast work and append-only events for reconstruction.
- Do not orchestrate business workflows in model `save()` methods or Django signals.
- Use UTC internally, IANA timezone display/business calendars, `Decimal` money and explicit currency/rate source.
- Attachments and large/raw email bodies are private files, never database BLOBs.
- Use pure-Python DB driver when a compatible native wheel cannot install on the actual account; run the complete engine integration suite either way.
- Any expensive work is a durable job with a lease, batch/time budget, checkpoint, exit code and run record.

## 6. Private API rules

The API is an internal implementation contract, not a public integration platform.

- Prefix: `/api/v1`.
- Authentication: secure server-side staff or portal session. No permanent bearer token, API key, OAuth client or CORS.
- Unsafe same-origin methods require CSRF.
- Mutable resource response includes `ETag: "vN"`; update/transition requires matching `If-Match`.
- Commands that could duplicate an effect require `Idempotency-Key`.
- Lists use keyset cursor pagination, default 25, maximum 100.
- Errors use `application/problem+json` with a correlation ID.
- `429` includes `Retry-After`.
- Complex safe search uses `POST /api/v1/search`; the HTTP QUERY method is not required at launch because the complete shared-host path must first prove support.
- Every endpoint has a p95/p99, SQL count, request/response size, query-plan and required-index budget in the companion matrix.

### 6.1 Standard error document

```json
{
  "type": "https://crm.example.internal/problems/stale-version",
  "title": "Resource version is stale",
  "status": 412,
  "detail": "A newer record version has been saved.",
  "instance": "/api/v1/opportunities/01K2...",
  "correlation_id": "01K2CORR...",
  "errors": [
    {
      "pointer": "/headers/If-Match",
      "code": "expected_v8",
      "message": "Refresh and reapply your changes."
    }
  ]
}
```

### 6.2 Standard asynchronous acknowledgement

```http
HTTP/1.1 202 Accepted
Location: /api/v1/jobs/01K2JOB...
Cache-Control: private, no-store
Content-Type: application/json
```

```json
{
  "data": {
    "type": "job",
    "id": "01K2JOB...",
    "attributes": {
      "state": "QUEUED",
      "submitted_at": "2026-07-14T08:00:00Z",
      "status_url": "/api/v1/jobs/01K2JOB..."
    }
  },
  "meta": {
    "request_id": "01K2REQ...",
    "correlation_id": "01K2CORR..."
  }
}
```

---

## 7. Endpoint-wide performance classes

| Endpoint class | p95 | p99 | Typical SQL maximum | Rule |
|---|---:|---:|---:|---|
| Staff detail/read | 1.2 s | 2.8 s | 25 | Customer 360/timeline may use 35 with approved query-count tests |
| Staff list | 1.5 s | 3.2 s | 18–22 | Cursor page ≤100; actor scope before count/page |
| Staff mutation/command | 1.8 s | 3.5 s | 22 | External effects persist intent only |
| Search/report | 2.0 s | 4.0 s | 20–24 | Indexed normalized fields or precomputed aggregates |
| Portal read/mutation | 1.4/1.8 s | 3.0/3.5 s | 18–20 | Organization scope derived from session |
| Public/signed flow | 1.8 s | 3.5 s | 12 | Rate limits and validation enabled |
| Async submission | 1.2 s | 2.5 s | 12 | Returns `202` and job URL |

The release-level NFR remains p95 ≤2.0 seconds for routine authenticated list/detail, p99 ≤4.0 seconds, mutation p95 ≤2.5 seconds, mixed portal/public p95 ≤2.5 seconds and <1% application errors at 15 active sessions.

---


## 8. Critical implementation patterns

### 8.1 Thin view, shared application service

```python
from dataclasses import dataclass
from django.db import transaction

@dataclass(frozen=True)
class TransitionLeadCommand:
    lead_id: str
    expected_version: int
    target_state: str
    reason_code: str | None
    next_action_at: object | None

@transaction.atomic
def transition_lead(*, actor, command: TransitionLeadCommand):
    lead = lead_selectors.for_update(actor=actor).get(public_id=command.lead_id)
    optimistic_lock.require(lead, command.expected_version)
    authorization.require(actor, "lead.transition", lead)
    transition = lead_state_machine.validate(lead, command)

    before = lead.audit_snapshot()
    transition.apply(lead)
    lead.record_version += 1
    lead.save(update_fields=transition.changed_fields + ["record_version", "updated_at"])

    event = domain_events.append(
        event_type="lead.state_changed.v1",
        subject=lead,
        actor=actor,
        payload=transition.event_payload(),
    )
    audit.append_change(actor=actor, target=lead, before=before, after=lead.audit_snapshot())
    return ServiceResult(resource=lead, event_ids=[event.public_id])
```

The HTML view and JSON endpoint both validate their transport input and call this service. Imports and automation use a separately authorized command adapter but do not patch `lead.state` directly.

### 8.2 Permission-filtered selector

```python
class OrganizationSelectors:
    @staticmethod
    def visible_to(actor):
        qs = Organization.objects.filter(deleted_at__isnull=True)
        scope = authorization.scope_for(actor, "organization.view")
        if scope.company_wide:
            return qs
        return qs.filter(
            Q(owner_id__in=scope.user_ids)
            | Q(account_team__user_id__in=scope.user_ids)
            | Q(record_grants__user_id=actor.id, record_grants__active=True)
        ).distinct()
```

List, count, search, detail and export start from this selector. Loading an unrestricted object and checking later is prohibited.

### 8.3 Transactional domain event and outbox intent

```python
@transaction.atomic
def approve_and_queue_message(*, actor, draft_id: str, expected_version: int):
    draft = Draft.objects.select_for_update().get(public_id=draft_id)
    optimistic_lock.require(draft, expected_version)
    authorization.require(actor, "message.send", draft)
    decision = communication_policy.evaluate(draft=draft, at=timezone.now())
    decision.require_allowed()

    outbox = OutboxMessage.objects.create(
        public_id=ulid(),
        idempotency_key=draft.logical_send_key(),
        rendered_body_hash=draft.rendered_body_hash,
        state=OutboxState.READY,
        policy_snapshot=decision.as_json(),
        scheduled_at=decision.eligible_at,
    )
    event = domain_events.append(
        event_type="message.send_intent_created.v1",
        subject=outbox,
        actor=actor,
        payload={"draft_id": draft.public_id},
    )
    audit.append_command(actor=actor, target=outbox, reason="approved send intent")
    return ServiceResult(resource=outbox, event_ids=[event.public_id])
```

SMTP occurs later in `send_outbox`, never inside the request transaction.

### 8.4 Bounded Cron runner

```python
def handle(self, *, max_items: int = 50, max_seconds: int = 40):
    with command_lease("run_due_jobs", ttl_seconds=120) as lease:
        if not lease.acquired:
            return CommandResult.skipped("active lease")

        deadline = monotonic() + max_seconds
        processed = 0
        while processed < max_items and monotonic() < deadline:
            job = claim_one_due_job()
            if job is None:
                break
            process_job_idempotently(job)
            processed += 1
        return CommandResult.success(processed=processed)
```

A job is claimed in a short transaction, executed outside that claim transaction where safe, and finalized in another short transaction. The runner never holds a table lock during SMTP, file generation or model scoring.

### 8.5 SMTP ambiguity

```text
READY → CLAIMED → SENDING
                    ├─ SENT_CONFIRMED
                    ├─ FAILED_TRANSIENT → READY after backoff
                    ├─ FAILED_PERMANENT
                    └─ DELIVERY_UNKNOWN → manual/Sent-folder reconciliation
```

`DELIVERY_UNKNOWN` is not retried automatically. The system preserves its deterministic Message-ID and rendered-body hash, searches available evidence, then requires an authorized reconciliation decision.

### 8.6 Server-rendered HTMX form with fallback

```html
<form method="post"
      action="{% url 'sales:lead-transition' lead.public_id %}"
      hx-post="{% url 'sales:lead-transition' lead.public_id %}"
      hx-target="#lead-workspace"
      hx-swap="outerHTML">
  {% csrf_token %}
  <input type="hidden" name="expected_version" value="{{ lead.record_version }}">
  {% include "components/form_error_summary.html" %}
  {{ form }}
  <button type="submit">Apply transition</button>
</form>
```

Without JavaScript, the form posts normally and redirects. With HTMX, the server returns the same authoritative workspace fragment. Validation and authorization remain on the server.

### 8.7 Query-count test

```python
def test_customer_overview_query_budget(authorised_client, customer):
    with django_assert_max_num_queries(35):
        response = authorised_client.get(f"/customers/{customer.public_id}")
    assert response.status_code == 200
```

Query budgets use the representative MySQL/MariaDB dataset. Passing SQLite tests alone is not acceptable for locks, collations, constraints or query plans.

---

# 9. Complete step-by-step production build


---

## S00 — Freeze product, policy and company configuration

**Phase:** Phase 0 — Decision and hosting lock

**Objective:** Turn the PRD into approved company-specific dictionaries, owners, policies and a traceable implementation baseline.

**Why this step exists:** Code cannot correctly infer the company timezone, products, roles, consent purposes, stages, SLA, retention or recovery authority. Building before these decisions creates hidden rework and unsafe defaults.

**Prerequisites:** Approved PRD; named sponsor, product, technical, security/privacy and process owners.

### What to build in the frontend

Build no customer UI yet. Produce information architecture diagrams, role journey maps, screen inventory, content vocabulary, status labels and accessibility content rules. Prototype only to validate flow, not to ship.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Create ADR template, requirement registry, threat-model template, data dictionary, domain glossary, capability catalogue, state-machine catalogue, event catalogue, API style guide and change-control process.

_No domain service is introduced in this step._

### How to build the backend services


### Database work

Define canonical identifiers, timezone/currency semantics, record classes, retention classes and preliminary table/storage budgets. No production migrations yet.

### Ordered implementation procedure

1. Name owners.
2. Complete Section 19.4 decisions.
3. Walk every lifecycle.
4. Define normal/exception/failure paths.
5. Approve status/reason codes.
6. Map every PRD ID to planned component/test.
7. Sign build-freeze record.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

Complete threat model, data classification, privacy purpose map, privilege conflicts and accepted boundary risks before implementation.

### Performance and resource budget

Estimate record volumes, file growth, mail volume, concurrency and database size. Reject requirements that exceed the shared-host envelope unless architecture change is approved.

### Testing required

Review workshops; requirement completeness audit; state-transition walkthrough; role authorization matrix; threat-model review.

### What success looks like

Every mandatory requirement has an owner, module, acceptance method and no unresolved ambiguous policy. Process owners can explain exactly who acts, when, with what evidence and what stops automation.

### Required deliverables

Signed configuration decision register; ADR set; threat model v1; capability matrix; state/event dictionaries; screen/API inventories; traceability matrix.


---

## S01 — Execute the actual Truehost Starter preflight

**Phase:** Phase 0 — Decision and hosting lock

**Objective:** Prove the account can run the selected production architecture and record exact versions/limits/paths.

**Why this step exists:** Marketing pages are not the runtime contract. Python, Passenger, database engine, Cron, mail, backup and access methods must be verified in the real account.

**Prerequisites:** Truehost Starter credentials and cPanel access; preflight checklist.

### What to build in the frontend

No production frontend. Create a temporary non-public diagnostic page only if needed, then remove it.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Deploy a minimal Django probe through Setup Python App, verify Passenger startup/restart, environment settings, database transaction/Unicode, private paths, cron, SMTP/IMAP, logs and backup interface.

_No domain service is introduced in this step._

### How to build the backend services


### Database work

Create disposable preflight database/user with utf8mb4; measure engine/version, transaction isolation, foreign keys, select-for-update and size reporting. Delete after evidence.

### Ordered implementation procedure

1. Record cPanel features.
2. Create Python app.
3. Install pinned probe dependencies.
4. Test WSGI.
5. Test DB driver candidates.
6. Run cron overlap test.
7. Send/receive only test mailboxes.
8. verify SSL/DNS/logs/backup.
9. Record resource baselines.
10. sign compatibility matrix.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

Never expose diagnostics publicly; do not place secrets in commands/logs; use test mailboxes; remove probe tokens/data.

### Performance and resource budget

Record cold/warm request latency, process memory, connection behavior, cron runtime and database migration temporary space.

### Testing required

Passenger restart; HTTPS/host; DB transaction/locking; SMTP/IMAP dedupe; cron lease; private file denial; backup readability.

### What success looks like

The actual account passes all mandatory capabilities. Exact Python/Django/driver/DB/Cron/mail paths are frozen. Any missing mandatory capability triggers an approved architecture decision rather than a workaround hidden in code.

### Required deliverables

Signed Truehost preflight report; compatibility matrix; selected Python/driver; directory paths; Cron/mail settings; capacity baseline.


---

## S02 — Create repository, dependency lock and delivery controls

**Phase:** Phase 1 — Platform foundation

**Objective:** Establish a reproducible codebase and review process before domain work.

**Why this step exists:** A production system is not dependable when dependencies, migrations, releases or ownership cannot be reconstructed.

**Prerequisites:** S00 decisions; S01 compatibility matrix.

### What to build in the frontend

Create `templates`, `static_src`, `static_build`, locale folders, design-token source and browser-test harness. Add a plain base page proving local assets and no CDN dependency.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Create Django project/settings split, domain app shells, common packages, typing/lint/test configuration, requirements input/lock, release manifest generator, architecture tests and secure contribution workflow.

_No domain service is introduced in this step._

### How to build the backend services


### Database work

Create no business tables beyond a migration metadata probe. Define migration naming/review policy and test database creation.

### Ordered implementation procedure

1. Initialize version control.
2. Add protected main/release branches.
3. Create app boundaries.
4. Pin dependencies with hashes.
5. Add SBOM/license/vulnerability tasks.
6. Configure unit/integration/browser/security test commands.
7. Add CI-equivalent local release script.
8. document review/merge/release rules.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

Secret scan, dependency review, signed/reviewed commits where practical, least access to repository, no production credentials in fixtures.

### Performance and resource budget

Dependency installation must fit account without compilation; test suite startup should remain fast; static bundle target established.

### Testing required

Clean environment rebuild; locked hash install; architecture import rules; secret scan; dependency vulnerability review.

### What success looks like

A new engineer can clone, install, run MySQL/MariaDB tests and build assets exactly from documented commands. A release manifest identifies commit, dependencies and migrations.

### Required deliverables

Repository skeleton; requirements lock; SBOM; engineering standards; review checklist; release script; local environment guide.


---

## S03 — Build environment configuration, observability and health foundation

**Phase:** Phase 1 — Platform foundation

**Objective:** Make every request and scheduled command diagnosable, environment-safe and release-identifiable.

**Why this step exists:** Failures on shared hosting must be understood without root access or an external monitoring service.

**Prerequisites:** S02 repository; exact cPanel paths and environment support.

### What to build in the frontend

Build base layout, branded error pages, maintenance page, correlation-ID display for errors, build badge visible only to admins and progressive enhancement hooks.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| All | `/errors/{status}` | Branded errors | Provide plain, accessible, non-disclosing errors with correlation ID and safe contact path. | 700 ms | ≤2 | ≤120 KB |

### How to build the frontend


#### `/errors/{status}` — Branded errors

- **Purpose:** Provide plain, accessible, non-disclosing errors with correlation ID and safe contact path.
- **Components:** ErrorTitle; CorrelationId; SafeActions
- **API/data:** Server-rendered view; API selected from implementation matrix by capability
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** 
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** No internal paths/stack/version disclosure
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤700 ms, ≤2 SQL, ≤120 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤700 ms, SQL count ≤2, compressed transfer ≤120 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement production/staging settings validation, `DEBUG=False` refusal, exact hosts/origins, correlation middleware, typed errors, structured redacted logs, command-run records, freshness-based health evidence, build/config compatibility and maintenance flag.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| common | `RequestContext` | Create correlation ID, actor identity, effective/original actor, locale, timezone and release context for every request/command. | auth_events, command_runs, audit_events |
| common | `ProblemDetailsService` | Map typed application exceptions to stable RFC 9457 problem documents without secrets. | system_incidents |
| operations | `StructuredLoggingService` | Emit redacted JSON lines with correlation, release, actor class, duration and outcome. | command_runs, system_incidents |
| operations | `HealthEvidenceService` | Record freshness-based dependency state instead of treating absence of errors as green. | system_metrics, command_runs |

### How to build the backend services


#### `RequestContext`

- **Responsibility:** Create correlation ID, actor identity, effective/original actor, locale, timezone and release context for every request/command.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** auth_events, command_runs, audit_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ProblemDetailsService`

- **Responsibility:** Map typed application exceptions to stable RFC 9457 problem documents without secrets.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** system_incidents
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `StructuredLoggingService`

- **Responsibility:** Emit redacted JSON lines with correlation, release, actor class, duration and outcome.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** command_runs, system_incidents
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `HealthEvidenceService`

- **Responsibility:** Record freshness-based dependency state instead of treating absence of errors as green.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** system_metrics, command_runs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create releases, system_metrics, command_runs, system_incidents/incident_events and feature_flags foundations with indexes by state/time/severity.

### Ordered implementation procedure

1. Define environment schema.
2. Implement startup checks.
3. Add request correlation.
4. Add structured logging/redaction.
5. Add Problem Details mapping.
6. Create minimal public-safe and privileged health endpoints.
7. Add branded 400/403/404/409/412/422/429/500/503 pages.
8. prove logs rotate.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

Detailed health is privileged; public errors disclose no stack/path/version; log filters redact passwords, tokens, secrets, message bodies and unnecessary PII.

### Performance and resource budget

Middleware overhead target <20 ms p95; public error response <700 ms; health endpoint ≤15 SQL queries and <1 second p95.

### Testing required

Settings refusal, host-header, HTTPS proxy assumptions, log redaction corpus, correlation propagation, stale-evidence state, error content review.

### What success looks like

Every request/command has one correlation ID and release ID; support can trace failures without secrets; stale dependencies become warning/critical; production never exposes debug details.

### Required deliverables

Settings schema; environment example; logging policy; health model/endpoints; error templates; maintenance framework; operations dashboard shell.


---

## S04 — Implement the private API contract, concurrency and idempotency

**Phase:** Phase 1 — Platform foundation

**Objective:** Create one consistent HTTP contract shared by all later modules.

**Why this step exists:** Without a fixed contract, different modules drift in errors, pagination, authorization, retries and concurrent-update behavior.

**Prerequisites:** S03 request context/error framework.

### What to build in the frontend

Build reusable form/HTMX response conventions: full-page vs fragment negotiation, progressive fallback, optimistic-conflict component, async job status component and toast/live-region policy.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Implement `/api/v1` response envelopes, RFC 9457 errors, keyset pagination, allowlisted filters/sorts/includes/fields, CSRF/session auth, media-type validation, ETag generation, If-Match enforcement, idempotency reservation/replay and request/payload limits.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| common | `ApiContractService` | Enforce media types, request size, schema validation, ETag/If-Match, idempotency and response envelopes. | none |
| common | `CursorPaginationService` | Generate tamper-resistant keyset cursors and bounded page metadata. | none |
| common | `IdempotencyService` | Reserve, replay and expire command keys with request hash and immutable result reference. | domain_events, outbox_messages, scheduled_jobs |
| common | `OptimisticLockService` | Compare expected record version and return field-aware conflict evidence. | all mutable current-state tables |

### How to build the backend services


#### `ApiContractService`

- **Responsibility:** Enforce media types, request size, schema validation, ETag/If-Match, idempotency and response envelopes.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** none
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `CursorPaginationService`

- **Responsibility:** Generate tamper-resistant keyset cursors and bounded page metadata.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** none
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `IdempotencyService`

- **Responsibility:** Reserve, replay and expire command keys with request hash and immutable result reference.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** domain_events, outbox_messages, scheduled_jobs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OptimisticLockService`

- **Responsibility:** Compare expected record version and return field-aware conflict evidence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** all mutable current-state tables
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create reusable idempotency storage or integrate uniqueness into effect tables; add row-version/public-ID fields and query-budget instrumentation. Do not create generic database-driven API definitions.

### Ordered implementation procedure

1. Freeze naming/status/header rules.
2. Implement response factories.
3. Implement cursor signing.
4. Implement schema validation.
5. implement optimistic lock.
6. implement idempotency request hash/result replay.
7. add rate-limit response with Retry-After.
8. generate OpenAPI.
9. contract-test every pattern.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

No CORS, bearer tokens, public keys, GraphQL, raw query language, arbitrary includes or mass assignment. Authorization occurs before counting/pagination.

### Performance and resource budget

Envelope overhead small; simple read p95 ≤1.2s; mutation acknowledgement p95 ≤1.8s; list query ≤18 SQL; max page size 100.

### Testing required

Contract tests for 200/201/202/204, every Problem status, stale edit, replay same/different body, cursor tamper, excessive page/filter/include, CSRF and content type.

### What success looks like

All later endpoints inherit identical headers, errors and limits. Duplicate command replay returns the original logical result; stale updates never silently overwrite; unauthorized counts stay hidden.

### Required deliverables

API style guide; middleware/decorators; pagination/idempotency/locking libraries; common schemas; OpenAPI generation; contract test suite.


---

## S05 — Build the frontend design system, application shell and interaction rules

**Phase:** Phase 1 — Platform foundation

**Objective:** Create a fast, accessible, reusable server-rendered UI foundation for every staff and portal workflow.

**Why this step exists:** A large CRM becomes inconsistent and error-prone if each screen invents forms, tables, status, validation and responsive behavior.

**Prerequisites:** S03 errors/maintenance; S04 HTTP conventions; approved information architecture.

### What to build in the frontend

Implement design tokens, typography, spacing, focus, contrast, buttons, links, fields, error summaries, tables/cards, badges, tabs, breadcrumbs, dialogs, drawers, pagination, filters, saved-view controls, timeline, activity composer, file component, skeletons, empty states, 412 conflict UI, async job status and responsive shell. Bundle HTMX locally; every enhanced flow has normal HTTP fallback.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/account/preferences` | Staff UI preferences | Set timezone display, density, notification and accessibility preferences. | 900 ms | ≤8 | ≤250 KB |
| Staff | `/` | Operational home | Show personal priorities, replies, approvals, overdue items, escalations and recent changes. | 1600 ms | ≤30 | ≤1000 KB |

### How to build the frontend


#### `/account/preferences` — Staff UI preferences

- **Purpose:** Set timezone display, density, notification and accessibility preferences.
- **Components:** PreferenceForm; Preview
- **API/data:** Server-rendered view; API selected from implementation matrix by capability
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Update permitted settings
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Own account
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤900 ms, ≤8 SQL, ≤250 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤900 ms, SQL count ≤8, compressed transfer ≤250 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/` — Operational home

- **Purpose:** Show personal priorities, replies, approvals, overdue items, escalations and recent changes.
- **Components:** AppShell; GlobalNav; PriorityQueue; KPIExceptionCards; RecentChanges
- **API/data:** GET /work-queue; GET /notifications; GET /operations/health (privileged card only)
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Claim/complete/open work
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Scope-aware dashboard
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤30 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤30, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Create view mixins/context processors for navigation permissions, active module, breadcrumbs, correlation, feature flags, messages and fragment rendering. Centralize form field policy and template component APIs.

_No domain service is introduced in this step._

### How to build the backend services


### Database work

No domain tables. Optionally persist staff UI preferences in a small governed profile table or user settings JSON with strict schema.

### Ordered implementation procedure

1. Define tokens/content rules.
2. Build semantic base shell.
3. Build components in isolation.
4. add keyboard/focus behaviors.
5. add responsive 360px variants.
6. add HTMX loading/error/conflict handling.
7. add local asset fingerprint/build.
8. create visual/accessibility regression checklist.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

CSP-compatible local assets; no unsafe inline script; auto-escaping; sanitized rich text only through reviewed component; destructive actions require impact/reason.

### Performance and resource budget

Normal compressed page ≤1.5 MB; CSS/JS initial bundle target ≤250 KB compressed; shell server render ≤900 ms; no layout-shifting external fonts.

### Testing required

Keyboard-only, focus not obscured, 200% zoom, 360px reflow, screen-reader landmarks/forms/status, no-color-only meaning, JS-disabled core flow, CSP test.

### What success looks like

Every later screen can be assembled from reviewed components, behaves consistently on errors/conflicts/mobile, and completes critical operations without a SPA or mouse-only action.

### Required deliverables

Design system documentation; component templates; local asset pipeline; shell/navigation; accessibility checklist; frontend test helpers.


---

## S06 — Implement database conventions, constraints and migration safety

**Phase:** Phase 1 — Platform foundation

**Objective:** Create the relational foundation that protects data even when application code fails.

**Why this step exists:** Production reliability depends on database uniqueness, foreign keys, append-only history and safe migrations—not only Python validation.

**Prerequisites:** S01 database/driver evidence; S02 repository; data model approval.

### What to build in the frontend

No user feature beyond admin compatibility page. Add developer-only schema documentation generated from models/migrations.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Implement abstract current-state model, immutable event model, public ULID generation, UTC timestamps, row version, actor references, soft deletion, money/currency types, schema-validated JSON helper, check/unique constraints, transaction helper and migration lock.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| common | `DatabasePolicy` | Provide base models, public IDs, UTC timestamps, soft deletion, row versions, check constraints and migration helpers. | all tables |

### How to build the backend services


#### `DatabasePolicy`

- **Responsibility:** Provide base models, public IDs, UTC timestamps, soft deletion, row versions, check constraints and migration helpers.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** all tables
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create foundational account/governance/operations tables in dependency order. Use InnoDB/utf8mb4; explicit index names; no BLOBs; no cascade that destroys audit/history.

### Ordered implementation procedure

1. Confirm engine/strict mode/collation.
2. implement base fields/managers.
3. define deletion semantics.
4. create initial migrations.
5. test constraints against concurrent writes.
6. establish expand-migrate-contract process.
7. measure migration space/time on copy-sized data.
8. document rollback/forward repair.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

Least-privileged DB user; parameterized ORM; raw SQL isolated/reviewed; sensitive migrations require backup and maintenance plan.

### Performance and resource budget

Standard point lookup uses public ID unique index; no migration approaches provider ceiling; locks remain short; schema-heavy deployment blocked at safe measured threshold.

### Testing required

MySQL/MariaDB integration, Unicode/Decimal/timezone, FK/check/unique, concurrent insert/update, migration forward/back/repair, table-size projection.

### What success looks like

The database rejects duplicate identities/idempotency keys and invalid state even under race conditions. A migration rehearsal predicts time/space and has an approved recovery path.

### Required deliverables

Base models; initial migrations; DB compatibility tests; migration runbook; schema/index conventions; size measurement command.


---

## S07 — Build invitation-only identity, login and account recovery

**Phase:** Phase 1 — Platform foundation

**Objective:** Create accountable staff/portal identities without public registration.

**Why this step exists:** Every later action requires stable actor identity, secure authentication and revocable access.

**Prerequisites:** S04 API; S05 forms; S06 account tables.

### What to build in the frontend

Build staff invitation acceptance, login, password reset request/confirm, neutral success pages and administrator user/invitation screens. Preserve form values safely and never reveal account existence.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/login` | Staff login | Authenticate invitation-only staff and start provisional/full session. | 1000 ms | ≤8 | ≤250 KB |
| Public | `/password-reset/request` | Password reset request | Request a non-enumerating reset link. | 1000 ms | ≤8 | ≤200 KB |
| Public | `/password-reset/confirm` | Password reset confirmation | Consume signed single-use token, set password and revoke sessions. | 1200 ms | ≤10 | ≤220 KB |

### How to build the frontend


#### `/login` — Staff login

- **Purpose:** Authenticate invitation-only staff and start provisional/full session.
- **Components:** LoginPanel; EmailField; PasswordField; RateLimitNotice
- **API/data:** POST /auth/login
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Submit credentials; preserve safe return path
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Public rate-limited; uniform account existence response
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1000 ms, ≤8 SQL, ≤250 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1000 ms, SQL count ≤8, compressed transfer ≤250 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/password-reset/request` — Password reset request

- **Purpose:** Request a non-enumerating reset link.
- **Components:** EmailField; NeutralConfirmation
- **API/data:** POST /auth/password-reset/request
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Queue reset intent
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Public rate-limited
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1000 ms, ≤8 SQL, ≤200 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1000 ms, SQL count ≤8, compressed transfer ≤200 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/password-reset/confirm` — Password reset confirmation

- **Purpose:** Consume signed single-use token, set password and revoke sessions.
- **Components:** PasswordFields; TokenStatus; SuccessPanel
- **API/data:** POST /auth/password-reset/confirm
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Confirm reset
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Signed token scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1200 ms, ≤10 SQL, ≤220 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1200 ms, SQL count ≤10, compressed transfer ≤220 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement custom user model, normalized verified email, invitation issuance/consumption, password policy/hash upgrade, login throttles, provisional/full session creation, reset token hash/expiry/replay prevention and auth event recording.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| accounts | `InvitationService` | Issue, resend, expire and consume single-use staff/portal invitations without public registration. | staff_invitations, portal_invitations, users |
| accounts | `AuthenticationService` | Normalize email, verify password, throttle failures and establish provisional/full server-side sessions. | users, login_throttles, auth_events, user_sessions |
| accounts | `PasswordResetService` | Create non-enumerating signed reset intents, consume once and revoke relevant sessions. | users, auth_events, user_sessions |

### How to build the backend services


#### `InvitationService`

- **Responsibility:** Issue, resend, expire and consume single-use staff/portal invitations without public registration.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** staff_invitations, portal_invitations, users
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `AuthenticationService`

- **Responsibility:** Normalize email, verify password, throttle failures and establish provisional/full server-side sessions.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** users, login_throttles, auth_events, user_sessions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `PasswordResetService`

- **Responsibility:** Create non-enumerating signed reset intents, consume once and revoke relevant sessions.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** users, auth_events, user_sessions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create users, staff_invitations, portal_invitations, login_throttles, auth_events and user_sessions with normalized-email uniqueness and token-hash indexes.

### Ordered implementation procedure

1. Create custom user before dependent migrations.
2. implement admin invitation.
3. implement token hashing.
4. implement login and throttle.
5. implement reset.
6. revoke sessions after reset.
7. add security notifications.
8. prohibit registration routes.
9. add complete negative tests.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/staff-invitations` | List staff invitation records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/staff-invitations` | Create one staff invitation | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/staff-invitations/{id}` | Retire or soft-delete one staff invitation | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/staff-invitations/{id}` | Get one staff invitation | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/staff-invitations/{id}/resend` | Resend a still-valid invitation without changing identity | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/auth/login` | Authenticate a staff user and begin a provisional or full session | public | 200 | 1800 ms | ≤12 | standard |
| `POST` | `/auth/logout` | Revoke the current session | staff | 204 | 1800 ms | ≤22 | standard |
| `POST` | `/auth/password-reset/confirm` | Consume a single-use reset token and revoke sessions | public | 204 | 1800 ms | ≤12 | standard |
| `POST` | `/auth/password-reset/request` | Request a non-enumerating password reset link | public | 202 | 1800 ms | ≤12 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/staff-invitations?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List staff invitation records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "staff-invitation",
      "id": "01K2STAFFINV00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Staff Invitation"
      }
    }
  ],
  "links": {
    "self": "/api/v1/staff-invitations?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/staff-invitations?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM staff_invitations WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/staff-invitations/{id}/resend`

**Purpose:** Resend a still-valid invitation without changing identity

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "resend",
    "attributes": {
      "state": "ACTIVE",
      "name": "Resend"
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "resend",
    "id": "01K2RESEND0000000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Resend",
      "last_action": "RESEND",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM resends with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Uniform failure text/timing; Secure/HttpOnly/SameSite cookies; compromised/common password controls; no password/token logging; reset links single-use and purpose-bound.

### Performance and resource budget

Login/reset p95 ≤1.0s excluding email delivery; ≤8 DB queries; throttle checks indexed and bounded; password hasher benchmarked on actual host.

### Testing required

Invitation expiry/reuse/wrong email; enumeration; brute force; reset replay; disabled user; hash upgrade; session revocation; CSRF; open redirect.

### What success looks like

Only an authorized invitation creates access; account history survives email change/disable; repeated attack traffic is limited without locking out the whole application.

### Required deliverables

Identity models/services; auth screens/endpoints; admin invitation UI; password policy; auth event/security tests; staff onboarding guide.


---

## S08 — Build MFA, session inventory and privileged step-up

**Phase:** Phase 1 — Platform foundation

**Objective:** Protect high-impact staff actions and make sessions individually controllable.

**Why this step exists:** Password-only compromise is an unacceptable risk for a system containing all customer data and automation controls.

**Prerequisites:** S07 identity/login.

### What to build in the frontend

Build TOTP enrollment/confirmation, MFA challenge, recovery-code display/rotation, session inventory/revoke and step-up dialog preserving intended action.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/mfa/verify` | MFA verification | Complete privileged staff login using TOTP or a single-use recovery code. | 900 ms | ≤8 | ≤220 KB |
| Staff | `/account/security` | Account security | Enroll MFA, rotate recovery codes and inspect recent authentication events. | 1200 ms | ≤15 | ≤450 KB |
| Staff | `/account/sessions` | Session inventory | Review and revoke active server-side sessions. | 1000 ms | ≤12 | ≤350 KB |

### How to build the frontend


#### `/mfa/verify` — MFA verification

- **Purpose:** Complete privileged staff login using TOTP or a single-use recovery code.
- **Components:** OtpInput; RecoveryCodeMode; TrustedContextNotice
- **API/data:** POST /auth/mfa/verify
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Verify code; rotate provisional session
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Provisional session only
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤900 ms, ≤8 SQL, ≤220 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤900 ms, SQL count ≤8, compressed transfer ≤220 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/account/security` — Account security

- **Purpose:** Enroll MFA, rotate recovery codes and inspect recent authentication events.
- **Components:** MfaCard; RecoveryCodes; AuthEventList; StepUpDialog
- **API/data:** Server-rendered view; API selected from implementation matrix by capability
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Enroll/confirm MFA; rotate codes
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Own identity; step-up for rotation
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1200 ms, ≤15 SQL, ≤450 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1200 ms, SQL count ≤15, compressed transfer ≤450 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/account/sessions` — Session inventory

- **Purpose:** Review and revoke active server-side sessions.
- **Components:** SessionTable; RevokeDialog
- **API/data:** Server-rendered view; API selected from implementation matrix by capability
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Revoke one/all sessions
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Own sessions; admin separate capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1000 ms, ≤12 SQL, ≤350 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1000 ms, SQL count ≤12, compressed transfer ≤350 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement encrypted/secret-safe TOTP storage, two-code enrollment confirmation, hashed recovery codes, role enforcement/grace period, provisional session, session registry, idle/absolute expiry, password/role/disable revocation and recent-auth policy.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| accounts | `MfaService` | Enroll and verify TOTP, hash recovery codes, enforce role policy and audit resets. | mfa_devices, mfa_recovery_codes, auth_events |
| accounts | `SessionService` | List, touch, rotate and revoke server-side sessions with idle/absolute expiry. | user_sessions, auth_events |
| accounts | `StepUpService` | Require fresh password/MFA proof before privileged actions while preserving intended command context. | user_sessions, auth_events |

### How to build the backend services


#### `MfaService`

- **Responsibility:** Enroll and verify TOTP, hash recovery codes, enforce role policy and audit resets.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** mfa_devices, mfa_recovery_codes, auth_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SessionService`

- **Responsibility:** List, touch, rotate and revoke server-side sessions with idle/absolute expiry.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** user_sessions, auth_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `StepUpService`

- **Responsibility:** Require fresh password/MFA proof before privileged actions while preserving intended command context.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** user_sessions, auth_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create mfa_devices and mfa_recovery_codes; index active device/user and code hash; retain auth events without secrets.

### Ordered implementation procedure

1. Generate local secret/QR.
2. verify two codes.
3. issue codes once.
4. enforce privileged role MFA.
5. list/revoke sessions.
6. implement step-up token bound to session/action/age.
7. create admin reset process.
8. test recovery/break-glass.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/auth/events` | List the current user security and authentication events | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/auth/mfa/confirm` | Confirm TOTP enrollment using two consecutive valid codes | staff | 201 | 1800 ms | ≤22 | standard |
| `POST` | `/auth/mfa/enroll` | Create a pending TOTP enrollment and QR payload | staff | 201 | 1800 ms | ≤22 | standard |
| `POST` | `/auth/mfa/recovery-codes/rotate` | Rotate hashed single-use recovery codes after step-up | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/auth/mfa/verify` | Verify TOTP/recovery code and elevate session | provisional | 200 | 1800 ms | ≤22 | standard |
| `GET` | `/auth/sessions` | List the current user session inventory | staff | 200 | 1500 ms | ≤18 | standard |
| `DELETE` | `/auth/sessions/{id}` | Revoke one session | staff | 204 | 1800 ms | ≤22 | standard |
| `POST` | `/auth/step-up` | Re-authenticate for a privileged action | staff | 200 | 1800 ms | ≤22 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/auth/events?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List the current user security and authentication events

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "event",
      "id": "01K2EVENT00000000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Event"
      }
    }
  ],
  "links": {
    "self": "/api/v1/auth/events?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/auth/events?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM events WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/auth/mfa/verify`

**Purpose:** Verify TOTP/recovery code and elevate session

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Content-Type: application/json
```

**Request body**

```json
{
  "challenge_id": "01K2CHALLENGE00000000000001",
  "code": "123456"
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "authentication-session",
    "id": "01K2AUTHENTI00000000000000",
    "version": 8,
    "attributes": {
      "state": "AUTHENTICATED",
      "mfa_verified_at": "2026-07-14T08:00:00Z",
      "idle_expires_at": "2026-07-14T08:30:00Z",
      "absolute_expires_at": "2026-07-14T18:00:00Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001"
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM verifys with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

### Security controls

Never log/display seed after enrollment; recovery codes hashed and one-use; step-up cannot be replayed across session/action; privileged session revocation immediate.

### Performance and resource budget

MFA verify p95 ≤900ms and ≤8 queries; no long-lived QR/seed page cache; session lookup indexed.

### Testing required

Clock skew boundaries, recovery reuse, code exhaustion, role elevation, session theft/expiry, password reset revocation, step-up age/action binding, accessible authentication.

### What success looks like

Privileged users cannot proceed without MFA; every session is visible/revocable; recovery works through audited policy without bypassing accountability.

### Required deliverables

MFA/session services and screens; recovery procedure; step-up middleware; break-glass runbook and quarterly drill script.


---

## S09 — Build authorization, roles, teams, queues, delegation and offboarding

**Phase:** Phase 1 — Platform foundation

**Objective:** Enforce least privilege for every object, field, count, export, file and background action.

**Why this step exists:** Broken object-level authorization is the highest-impact failure for staff and customer portal data.

**Prerequisites:** S07-S08 identity; approved capability and scope matrix.

### What to build in the frontend

Build role/capability, teams, queues, memberships, delegations, record grants and controlled offboarding screens. Hide unavailable actions but never rely on hiding for security.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Admin | `/admin/users` | Users and invitations | Invite, activate, disable and offboard staff/portal identities. | 1500 ms | ≤24 | ≤950 KB |
| Admin | `/admin/roles` | Roles and grants | Manage versioned capability bundles and exceptional record grants. | 1500 ms | ≤24 | ≤950 KB |
| Admin | `/admin/teams` | Teams, queues and delegation | Manage team/queue membership, capacity and absence delegation. | 1500 ms | ≤24 | ≤950 KB |

### How to build the frontend


#### `/admin/users` — Users and invitations

- **Purpose:** Invite, activate, disable and offboard staff/portal identities.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET/POST/PATCH /users; staff invitations; offboard/reactivate
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/admin/roles` — Roles and grants

- **Purpose:** Manage versioned capability bundles and exceptional record grants.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET/POST/PATCH /roles; activate; record grants
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/admin/teams` — Teams, queues and delegation

- **Purpose:** Manage team/queue membership, capacity and absence delegation.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET/POST/PATCH /teams and queues; memberships/delegations
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement central authorization service and permission-scoped selectors; capability bundles/versioning; own/team/queue/specific/company scope; field read/write/export policy; contextual constraints; immediate permission changes; offboarding inventory/reassignment.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| accounts | `AuthorizationService` | Apply capability, record scope, field sensitivity, contextual constraints and portal boundary to every read/action. | roles, capabilities, user_roles, record_grants, teams, queues |
| accounts | `RoleService` | Create versioned least-privilege role bundles and prevent grant beyond actor authority. | roles, capabilities, role_capabilities, user_roles |
| accounts | `TeamQueueService` | Manage effective-dated teams, queues, membership, claim eligibility and capacity. | teams, team_members, work_queues, queue_memberships |
| accounts | `DelegationService` | Create time-bounded scoped delegation without rewriting historical ownership. | delegations |
| accounts | `RecordGrantService` | Grant exceptional object scope with reason, expiry and authority ceiling. | record_grants |
| accounts | `OffboardingService` | Inventory and reassign work, approvals, jobs and portal grants before user disable and session revocation. | users, user_roles, tasks, approval_requests, scheduled_jobs, delegations, user_sessions |

### How to build the backend services


#### `AuthorizationService`

- **Responsibility:** Apply capability, record scope, field sensitivity, contextual constraints and portal boundary to every read/action.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** roles, capabilities, user_roles, record_grants, teams, queues
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RoleService`

- **Responsibility:** Create versioned least-privilege role bundles and prevent grant beyond actor authority.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** roles, capabilities, role_capabilities, user_roles
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `TeamQueueService`

- **Responsibility:** Manage effective-dated teams, queues, membership, claim eligibility and capacity.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** teams, team_members, work_queues, queue_memberships
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `DelegationService`

- **Responsibility:** Create time-bounded scoped delegation without rewriting historical ownership.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** delegations
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RecordGrantService`

- **Responsibility:** Grant exceptional object scope with reason, expiry and authority ceiling.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** record_grants
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OffboardingService`

- **Responsibility:** Inventory and reassign work, approvals, jobs and portal grants before user disable and session revocation.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** users, user_roles, tasks, approval_requests, scheduled_jobs, delegations, user_sessions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create roles, capabilities, role_capabilities, user_roles, teams, team_members, work_queues, queue_memberships, delegations and record_grants with effective dates and authority constraints.

### Ordered implementation procedure

1. Seed atomic capabilities.
2. implement role versions.
3. implement scope query builders.
4. implement object checks.
5. implement field policy.
6. enforce on list/count/search/detail/mutation/export/file/job.
7. add delegation.
8. add offboarding.
9. generate authorization matrix tests.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/delegations` | List delegation records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/delegations` | Create one delegation | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/delegations/{id}` | Retire or soft-delete one delegation | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/delegations/{id}` | Get one delegation | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/delegations/{id}` | Update one delegation | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/delegations/{id}/end` | End a delegation while preserving historical attribution | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/queues` | List work queue records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/queues` | Create one work queue | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/queues/{id}` | Retire or soft-delete one work queue | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/queues/{id}` | Get one work queue | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/queues/{id}` | Update one work queue | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/queues/{id}/members` | Add an effective-dated queue membership | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/queues/{id}/members/{user_id}` | End queue membership | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/record-grants` | List record grant records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/record-grants` | Create one record grant | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/record-grants/{id}` | Retire or soft-delete one record grant | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/record-grants/{id}` | Get one record grant | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/record-grants/{id}` | Update one record grant | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/roles` | List role records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/roles` | Create one role | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/roles/{id}` | Retire or soft-delete one role | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/roles/{id}` | Get one role | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/roles/{id}` | Update one role | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/roles/{id}/activate` | Activate an approved role version | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/teams` | List team records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/teams` | Create one team | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/teams/{id}` | Retire or soft-delete one team | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/teams/{id}` | Get one team | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/teams/{id}` | Update one team | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/users` | List staff or portal user records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/users` | Create one staff or portal user | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/users/{id}` | Retire or soft-delete one staff or portal user | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/users/{id}` | Get one staff or portal user | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/users/{id}` | Update one staff or portal user | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/users/{id}/offboard` | Run controlled offboarding, reassignment and session revocation | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/users/{id}/reactivate` | Reactivate an eligible disabled user after review | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/delegations?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List delegation records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "delegation",
      "id": "01K2DELEGATI00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Delegation"
      }
    }
  ],
  "links": {
    "self": "/api/v1/delegations?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/delegations?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM delegations WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/roles/{id}/activate`

**Purpose:** Activate an approved role version

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "role",
    "id": "01K2ROLE000000000000000000",
    "version": 8,
    "attributes": {
      "code": "SALES",
      "name": "Sales",
      "state": "ACTIVE",
      "version": 3,
      "last_action": "ACTIVATE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM roles with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); UNIQUE(code, version); INDEX(state, updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Default deny; actor cannot grant beyond own authority; portal boundary is separate policy; high-risk grants and offboarding require reason/step-up; no superuser shortcut in application services.

### Performance and resource budget

Permission filtering must use indexes and occur before pagination; authorization overhead target <50ms p95 on standard queries; no per-row policy N+1.

### Testing required

Role × scope × field × action matrix; direct URL; altered IDs; counts; search; aggregates; export; file; job replay; delegation expiry; inactive owner; four-eyes conflict.

### What success looks like

A single test suite proves each role sees and changes exactly its permitted data across every path. Offboarding leaves no active object assigned to disabled users.

### Required deliverables

Capability registry; authorization/selectors; admin UI; matrix tests; role defaults; offboarding/delegation runbooks.


---

## S10 — Build immutable audit and security-event evidence

**Phase:** Phase 1 — Platform foundation

**Objective:** Make sensitive business and administrative actions reconstructable and tamper-evident.

**Why this step exists:** A production CRM must explain who changed customer state, permissions, exports, merges, workflows and models.

**Prerequisites:** S03 correlation/logging; S06 database; S09 actor/authorization.

### What to build in the frontend

Build privileged audit search/detail, security event queue and verification-manifest screen. Show diffs/reasons without exposing restricted values.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Admin | `/admin/audit` | Audit evidence | Review immutable events and verification manifests. | 1500 ms | ≤24 | ≤950 KB |

### How to build the frontend


#### `/admin/audit` — Audit evidence

- **Purpose:** Review immutable events and verification manifests.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET /audit-events; POST /audit/verify
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement audit append API used by services, actor types, before/after hashes or field-safe diffs, correlation, original/effective actor, hash chain/periodic manifest and verification command. Separate operational logs from audit.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| governance | `AuditService` | Append tamper-evident business/security evidence with actor, target, reason, diff/hash and correlation. | audit_events, audit_manifests |

### How to build the backend services


#### `AuditService`

- **Responsibility:** Append tamper-evident business/security evidence with actor, target, reason, diff/hash and correlation.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** audit_events, audit_manifests
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create audit_events and audit_manifests with append-only controls, target/time indexes and previous/hash fields. Prevent routine deletion/update.

### Ordered implementation procedure

1. Define audited action catalogue.
2. create safe diff/redaction.
3. append within business transaction.
4. hash chain batches.
5. verify manifests.
6. add access auditing for restricted fields/files.
7. create incident on gap/tamper.
8. test archive retention.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/audit-events` | List permission-scoped immutable audit events | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/audit/verify` | Queue audit hash-chain verification and manifest creation | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `GET` | `/security-events` | List security incidents and authentication anomalies | staff | 200 | 1500 ms | ≤18 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/audit-events?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List permission-scoped immutable audit events

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "audit-event",
      "id": "01K2AUDITEVE00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Audit Event"
      }
    }
  ],
  "links": {
    "self": "/api/v1/audit-events?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/audit-events?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM audit_events WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/audit/verify`

**Purpose:** Queue audit hash-chain verification and manifest creation

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 202`

**Response body**

```json
{
  "data": {
    "type": "job",
    "id": "01K2JOB000000000000000001",
    "attributes": {
      "state": "QUEUED",
      "submitted_at": "2026-07-14T08:00:00Z",
      "status_url": "/api/v1/jobs/01K2JOB000000000000000001"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001"
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1200 ms**; p99 ≤ **2500 ms** under the representative mixed workload.

- Maximum **12 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM verifys with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1200 ms and p99 ≤2500 ms on the representative mixed workload, uses ≤12 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Audit contains no secrets/plain sensitive values; audit viewing itself is permissioned; administrators cannot erase evidence; impersonation records both actors.

### Performance and resource budget

Audit append should add bounded queries (<3 typical) and not materially increase p95; verification runs as bounded job, never HTTP.

### Testing required

Completeness for sensitive commands; rollback creates no false audit; altered row/gap detection; disabled/merged actors; restricted value redaction; authorization.

### What success looks like

For every high-risk action, an auditor can reconstruct actor, authority, reason, target, time, version and outcome. Verification detects simulated alteration within one scheduled run.

### Required deliverables

Audit service/models/UI; audited-action map; verification command; manifests; security queue; evidence retention policy.


---

## S11 — Build private file storage and secure upload/download

**Phase:** Phase 1 — Platform foundation

**Objective:** Store customer files without database BLOB growth or public-path exposure.

**Why this step exists:** Attachments, quotes, exports and inbound files are a major confidentiality, inode and active-content risk on shared hosting.

**Prerequisites:** S06 file metadata conventions; S09 authorization; actual private path from S01.

### What to build in the frontend

Build reusable upload field, validation progress, classification/visibility labels, private file list, safe download action, rejection reason and no-inline active-content behavior.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/customers/{id}/files` | Files tab | Show classified private files with upload/download audit. | 1500 ms | ≤25 | ≤950 KB |

### How to build the frontend


#### `/customers/{id}/files` — Files tab

- **Purpose:** Show classified private files with upload/download audit.
- **Components:** TabHeader; FilterBar; SourceLinkedCards; TimelineOrTable; PermissionLabels
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Context-specific create/update commands
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer object + field sensitivity
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤25 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤25, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement custom storage outside public root, randomized two-level paths, streaming upload with byte limit, signature/MIME/extension checks, filename normalization, SHA-256, classification, linkage, safe Content-Disposition/nosniff and download audit.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| common | `PrivateStorageService` | Generate randomized two-level paths, stream safe downloads, checksum, classify and age temporary files. | file_assets, archive_manifests |
| crm | `FileAssetService` | Validate extension/signature/size, persist metadata, link business records and mediate audited download. | file_assets |

### How to build the backend services


#### `PrivateStorageService`

- **Responsibility:** Generate randomized two-level paths, stream safe downloads, checksum, classify and age temporary files.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** file_assets, archive_manifests
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `FileAssetService`

- **Responsibility:** Validate extension/signature/size, persist metadata, link business records and mediate audited download.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** file_assets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create file_assets and file-link associations with checksum, size, type, path, validation, retention, uploader and soft-delete state; index business owner and retention dates.

### Ordered implementation procedure

1. Establish allowlist.
2. create temp quarantine.
3. stream and cap bytes/count.
4. sniff signatures safely.
5. reject scripts/macros/HTML/SVG/nested archives by default.
6. move accepted file atomically.
7. persist metadata.
8. authorize every stream.
9. schedule cleanup/archive.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `POST` | `/files` | Upload and validate one private file | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/files/{id}` | Soft-delete a private file after dependency and hold checks | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/files/{id}` | Get private file metadata | staff | 200 | 1200 ms | ≤25 | standard |
| `GET` | `/files/{id}/download` | Authorize and stream one private file with safe headers | staff | 200 | 1200 ms | ≤25 | standard |
| `GET` | `/organizations/{id}/files` | List authorized private files for a customer | staff | 200 | 1200 ms | ≤25 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/files/{id}?fields[file]=id,state,owner_id,updated_at&include=owner`

**Purpose:** Get private file metadata

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "file",
    "id": "01K2FILE000000000000000000",
    "version": 8,
    "attributes": {
      "original_name": "requirements.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 245678,
      "classification": "CONFIDENTIAL",
      "validation_state": "ACCEPTED",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb924..."
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1200 ms**; p99 ≤ **2800 ms** under the representative mixed workload.

- Maximum **25 SQL statements**, request **16 KB**, response **512 KB**.

- Query shape: SELECT the authorized file by public_id with actor scope in the same query; join current owner/state only; prefetch bounded child collections requested by include; return 404 before unrestricted data is materialized.

- Required indexes: UNIQUE(public_id); UNIQUE(sha256, size_bytes); INDEX(owner_type, owner_id, deleted_at, public_id); INDEX(validation_state, created_at)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1200 ms and p99 ≤2800 ms on the representative mixed workload, uses ≤25 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/files`

**Purpose:** Upload and validate one private file

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: multipart/form-data
```

**Request body**

```json
{
  "data": {
    "type": "file",
    "attributes": {
      "original_name": "requirements.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 245678,
      "classification": "CONFIDENTIAL",
      "validation_state": "ACCEPTED",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb924..."
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "file",
    "id": "01K2FILE000000000000000000",
    "version": 8,
    "attributes": {
      "original_name": "requirements.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 245678,
      "classification": "CONFIDENTIAL",
      "validation_state": "ACCEPTED",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb924...",
      "last_action": "FILES",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **5120 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM file_assets with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); UNIQUE(sha256, size_bytes); INDEX(owner_type, owner_id, deleted_at, public_id); INDEX(validation_state, created_at)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

No public URL; no path from user input; no active inline rendering; strict allowlist because no malware scanner; step-up/access audit for restricted files; traversal and symlink defenses.

### Performance and resource budget

Default upload 5 MB, policy exception 20 MB; upload request p95 depends on transfer but validation CPU bounded; metadata detail ≤15 queries; file stream does not load whole file in memory.

### Testing required

Traversal, double extension, MIME mismatch, oversized/truncated, macro, SVG/HTML, archive bomb, unsafe filename, cross-scope download, deleted/held file, range/stream behavior.

### What success looks like

A file cannot be fetched through a guessed path or wrong customer scope, cannot execute active content through the app, and storage/inode use remains measurable and recoverable.

### Required deliverables

Private storage backend; upload/download endpoints/components; allowlist policy; malicious corpus tests; cleanup and capacity metrics.


---

## S12 — Build governed configuration, reference data, custom fields and policies

**Phase:** Phase 1 — Platform foundation

**Objective:** Turn business behavior into versioned, validated, reviewable configuration rather than scattered constants.

**Why this step exists:** Pipelines, SLA, forms, templates, caps and reason dictionaries will change; unsafe runtime configuration can become code execution or retroactive history corruption.

**Prerequisites:** S00 approved defaults; S09 admin authorization; S10 audit.

### What to build in the frontend

Build administration screens for company settings, dictionaries, calendars, teams/queues preview, custom fields, tags, feature flags and configuration version diff/activation/rollback.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Admin | `/admin/configuration` | Configuration versions | Review checksummed bundles, dependencies, activation and rollback. | 1500 ms | ≤24 | ≤950 KB |
| Admin | `/admin/policies` | Business and policy settings | Manage calendars, SLA, assignment, communication caps and quiet hours. | 1500 ms | ≤24 | ≤950 KB |
| Admin | `/admin/custom-fields` | Custom fields | Manage typed, validated, visible and searchable field definitions. | 1500 ms | ≤24 | ≤950 KB |
| Admin | `/admin/tags` | Governed tags | Manage stable tag codes, scope and retirement. | 1500 ms | ≤24 | ≤950 KB |

### How to build the frontend


#### `/admin/configuration` — Configuration versions

- **Purpose:** Review checksummed bundles, dependencies, activation and rollback.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET/POST/PATCH /configuration-versions; validate/activate/rollback; feature flags
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/admin/policies` — Business and policy settings

- **Purpose:** Manage calendars, SLA, assignment, communication caps and quiet hours.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** business calendars, SLA, assignment and communication policy endpoints
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/admin/custom-fields` — Custom fields

- **Purpose:** Manage typed, validated, visible and searchable field definitions.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET/POST/PATCH /custom-field-definitions
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/admin/tags` — Governed tags

- **Purpose:** Manage stable tag codes, scope and retirement.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET/POST/PATCH /tags
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement schema-validated configuration bundles, effective dating, dependency analysis, checksums, staged activation, rollback for new behavior, typed custom fields, governed tags, business calendars, SLA/assignment policy versions and feature flags.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| governance | `ConfigurationService` | Validate, checksum, schedule, activate and roll back versioned company configuration. | configuration_versions, feature_flags |
| policy | `BusinessCalendarService` | Calculate business minutes, holidays, DST-safe due times and SLA intervals. | business_calendars, sla_policies |
| crm | `CustomFieldService` | Manage versioned typed definitions and validate values/visibility/dependencies. | custom_field_definitions, custom_field_values |
| crm | `TagService` | Manage governed stable tags and type-restricted assignments. | tags, entity_tags |

### How to build the backend services


#### `ConfigurationService`

- **Responsibility:** Validate, checksum, schedule, activate and roll back versioned company configuration.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** configuration_versions, feature_flags
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `BusinessCalendarService`

- **Responsibility:** Calculate business minutes, holidays, DST-safe due times and SLA intervals.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** business_calendars, sla_policies
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `CustomFieldService`

- **Responsibility:** Manage versioned typed definitions and validate values/visibility/dependencies.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** custom_field_definitions, custom_field_values
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `TagService`

- **Responsibility:** Manage governed stable tags and type-restricted assignments.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tags, entity_tags
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create configuration_versions, feature_flags, business_calendars, sla_policies, assignment_rule_versions, custom_field_definitions/values and tags/entity_tags.

### Ordered implementation procedure

1. Seed opinionated default codes.
2. define JSON schemas and stable codes.
3. create draft/review/active/retired lifecycle.
4. calculate dependency impact.
5. simulate routing/policy.
6. require reviewer for high impact.
7. schedule activation.
8. retain historical version references.
9. support safe rollback.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/assignment-rules` | List assignment rule version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/assignment-rules` | Create one assignment rule version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/assignment-rules/{id}` | Retire or soft-delete one assignment rule version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/assignment-rules/{id}` | Get one assignment rule version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/assignment-rules/{id}` | Update one assignment rule version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/business-calendars` | List business calendar records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/business-calendars` | Create one business calendar | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/business-calendars/{id}` | Retire or soft-delete one business calendar | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/business-calendars/{id}` | Get one business calendar | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/business-calendars/{id}` | Update one business calendar | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/configuration-versions` | List configuration version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/configuration-versions` | Create one configuration version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/configuration-versions/{id}` | Retire or soft-delete one configuration version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/configuration-versions/{id}` | Get one configuration version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/configuration-versions/{id}` | Update one configuration version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/configuration-versions/{id}/activate` | Activate approved configuration at effective time | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/configuration-versions/{id}/rollback` | Restore prior configuration for new behavior | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/configuration-versions/{id}/validate` | Validate configuration schema, dependencies and compatibility | staff | 200 | 1800 ms | ≤22 | standard |
| `GET` | `/feature-flags` | List server-side feature flag records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/feature-flags` | Create one server-side feature flag | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/feature-flags/{id}` | Retire or soft-delete one server-side feature flag | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/feature-flags/{id}` | Get one server-side feature flag | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/feature-flags/{id}` | Update one server-side feature flag | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/feature-flags/{id}/set-state` | Set scoped feature state without bypassing security policy | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/sla-policies` | List SLA policy records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/sla-policies` | Create one SLA policy | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/sla-policies/{id}` | Retire or soft-delete one SLA policy | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/sla-policies/{id}` | Get one SLA policy | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/sla-policies/{id}` | Update one SLA policy | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/custom-field-definitions` | List custom-field definition records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/custom-field-definitions` | Create one custom-field definition | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/custom-field-definitions/{id}` | Retire or soft-delete one custom-field definition | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/custom-field-definitions/{id}` | Get one custom-field definition | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/custom-field-definitions/{id}` | Update one custom-field definition | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/tags` | List governed tag records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/tags` | Create one governed tag | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/tags/{id}` | Retire or soft-delete one governed tag | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/tags/{id}` | Get one governed tag | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/tags/{id}` | Update one governed tag | staff | 200 | 1800 ms | ≤22 | If-Match |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/assignment-rules?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List assignment rule version records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "assignment-rule",
      "id": "01K2ASSIGNME00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Assignment Rule"
      }
    }
  ],
  "links": {
    "self": "/api/v1/assignment-rules?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/assignment-rules?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM assignment_rules WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/configuration-versions/{id}/activate`

**Purpose:** Activate approved configuration at effective time

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "activate",
    "id": "01K2ACTIVATE00000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Activate",
      "last_action": "ACTIVATE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM activates with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

No Python/SQL/template expression in configuration; secrets excluded; actor cannot activate beyond capability; label edit cannot trigger mass customer effects; feature flags cannot bypass security/consent.

### Performance and resource budget

Admin lists/details p95 ≤1.5s; activation request only writes configuration/events and never performs mass backfill inline; dependency analysis bounded/indexed.

### Testing required

Schema tamper, unknown field/operator, dependency retirement, activation conflict, historical effective date, rollback, unsafe feature flag, localization extraction, permission/four-eyes.

### What success looks like

Every effective business rule shows version, author, reviewer, time, dependency impact and rollback. Historical calculations remain tied to the version valid when facts occurred.

### Required deliverables

Configuration engine/UI; default bundle; policy services; custom fields/tags; dependency reports; activation tests.


---

## S13 — Build reusable state-machine and invariant engine

**Phase:** Phase 2 — Core domain

**Objective:** Create one explicit transition pattern for lead, opportunity, onboarding, support, recovery, success and operational states.

**Why this step exists:** Directly editing status fields leads to missing evidence, broken SLA, unowned work and automation on uncommitted data.

**Prerequisites:** S06 transactions/history; S09 policy; S10 audit; S12 state definitions.

### What to build in the frontend

Build reusable stage/status stepper, allowed-action menu, evidence form, transition preview, rejection explanation and historical interval view. Never expose arbitrary status dropdown for governed states.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Implement typed transition definitions with allowed edges, permission, required fields/evidence, entry/exit actions, owner/action invariant, terminal outcomes, corrective/reopen events and committed domain-event creation.

_No domain service is introduced in this step._

### How to build the backend services


### Database work

Create append-only stage/event table patterns and current-state projections. Add constraints for owner/next action/wake-up where representable and nightly invariant checks otherwise.

### Ordered implementation procedure

1. Define transition contract.
2. implement validator.
3. lock target row/version.
4. validate edge/authority/evidence.
5. append event and update current state.
6. write audit/domain event atomically.
7. schedule effects later.
8. implement correction/reopen.
9. add reconstruction tests.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

No transition from client-supplied state alone; object/field policy; terminal and destructive transitions require reason/step-up where configured; automation sees committed event only.

### Performance and resource budget

Typical transition p95 ≤1.8s and ≤22 queries; lock only target/current dependencies; no table scans; events indexed by entity/effective time.

### Testing required

Every valid/invalid edge; missing evidence; stale If-Match; concurrent transitions; rollback; historical reconstruction; reopen/correction; owner/action invariant; permission matrix.

### What success looks like

No governed state can be bypassed through HTML, API, import or job. Reports reconstruct historical state and elapsed intervals exactly from append-only events.

### Required deliverables

State-machine library; transition UI; history models; invariant checker; test fixture DSL; transition documentation.


---

## S14 — Build canonical organizations, contacts and relationships

**Phase:** Phase 2 — Core domain

**Objective:** Create one trustworthy customer identity model before leads, tickets and automation depend on it.

**Why this step exists:** Embedding contacts inside companies or allowing duplicates destroys customer history and authorization correctness.

**Prerequisites:** S06 schema; S09 policy; S11 files; S12 custom fields; normalization rules.

### What to build in the frontend

Build organization/contact lists, create/edit forms, contact-point editor, relationship history, address forms, account-owner/team controls and duplicate candidate preview during creation.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/customers` | Customer organizations | List canonical organizations with lifecycle, owner, health and next action. | 1400 ms | ≤20 | ≤800 KB |
| Staff | `/customers/new` | Create organization | Create a canonical organization after duplicate preview. | 1500 ms | ≤18 | ≤550 KB |
| Staff | `/contacts` | Contacts | List canonical contacts across organization relationships without embedding employment identity. | 1400 ms | ≤20 | ≤750 KB |
| Staff | `/contacts/new` | Create contact | Create contact, points and relationship after identity checks. | 1600 ms | ≤20 | ≤650 KB |
| Staff | `/contacts/{id}` | Contact detail | Manage canonical person identity, contact points, organization roles, consent and history. | 1500 ms | ≤30 | ≤850 KB |

### How to build the frontend


#### `/customers` — Customer organizations

- **Purpose:** List canonical organizations with lifecycle, owner, health and next action.
- **Components:** CustomerFilters; OrganizationTable; SavedViews; CreateButton
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/update/open customer
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/customers/new` — Create organization

- **Purpose:** Create a canonical organization after duplicate preview.
- **Components:** OrganizationForm; DuplicateCandidatePanel; ConsentNotice
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create after confirm-existing/new decision
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** create_organization capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤18 SQL, ≤550 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤18, compressed transfer ≤550 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/contacts` — Contacts

- **Purpose:** List canonical contacts across organization relationships without embedding employment identity.
- **Components:** ContactFilters; ContactTable; RelationshipBadges
- **API/data:** GET/POST/PATCH /contacts; contact points, relationships, consent and preferences
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/update/open contact
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Contact record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤750 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤750 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/contacts/new` — Create contact

- **Purpose:** Create contact, points and relationship after identity checks.
- **Components:** ContactForm; ContactPointRepeater; RelationshipForm; DuplicatePanel
- **API/data:** GET/POST/PATCH /contacts; contact points, relationships, consent and preferences
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create contact and atomic relationship
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** create_contact capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤20 SQL, ≤650 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤20, compressed transfer ≤650 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/contacts/{id}` — Contact detail

- **Purpose:** Manage canonical person identity, contact points, organization roles, consent and history.
- **Components:** ContactHeader; RelationshipTimeline; ContactPoints; ConsentSummary; ActivityList
- **API/data:** GET/POST/PATCH /contacts; contact points, relationships, consent and preferences
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Update fields, points, relationships and preferences
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Contact object + field policy
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤30 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤30, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement normalization, canonical services, relationship effective dates, contact-point primary/verification, address minimization, ownership/account team and lifecycle derivation/controlled override.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| crm | `NormalizationService` | Normalize name, email, phone, domain and address deterministically while retaining display values. | organizations, contacts, contact_points, addresses |
| crm | `OrganizationService` | Create/update canonical organization identity, ownership and derived lifecycle override evidence. | organizations |
| crm | `ContactService` | Create/update canonical person identity independent of employer relationship. | contacts |
| crm | `RelationshipService` | Manage effective-dated contact-to-organization roles, influence and primary relation. | contact_organizations |
| crm | `ContactPointService` | Manage typed verified/suppressible email and phone values with primary uniqueness. | contact_points |

### How to build the backend services


#### `NormalizationService`

- **Responsibility:** Normalize name, email, phone, domain and address deterministically while retaining display values.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** organizations, contacts, contact_points, addresses
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OrganizationService`

- **Responsibility:** Create/update canonical organization identity, ownership and derived lifecycle override evidence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** organizations
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ContactService`

- **Responsibility:** Create/update canonical person identity independent of employer relationship.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** contacts
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RelationshipService`

- **Responsibility:** Manage effective-dated contact-to-organization roles, influence and primary relation.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** contact_organizations
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ContactPointService`

- **Responsibility:** Manage typed verified/suppressible email and phone values with primary uniqueness.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** contact_points
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create organizations, contacts, contact_organizations, contact_points, addresses and account-team relations with normalized indexes and opaque public IDs.

### Ordered implementation procedure

1. Implement deterministic normalizers with fixtures.
2. create canonical models.
3. add forms/selectors.
4. create identity match checks before commit.
5. implement relationship moves without history loss.
6. add owner/team.
7. emit timeline/events.
8. add import-safe service path.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/addresses` | List address records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/addresses` | Create one address | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/addresses/{id}` | Retire or soft-delete one address | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/addresses/{id}` | Get one address | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/addresses/{id}` | Update one address | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/contact-points` | List contact point records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/contact-points` | Create one contact point | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/contact-points/{id}` | Retire or soft-delete one contact point | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/contact-points/{id}` | Get one contact point | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/contact-points/{id}` | Update one contact point | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/contact-relationships` | List contact-to-organization relationship records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/contact-relationships` | Create one contact-to-organization relationship | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/contact-relationships/{id}` | Retire or soft-delete one contact-to-organization relationship | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/contact-relationships/{id}` | Get one contact-to-organization relationship | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/contact-relationships/{id}` | Update one contact-to-organization relationship | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/contacts` | List contacts | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/contacts` | Create a contact | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/contacts/{id}` | Soft-delete or cancel one contact | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/contacts/{id}` | Get one contact | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/contacts/{id}` | Patch one contact | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/contacts/{id}/organizations` | List organization relationships for a contact | staff | 200 | 1200 ms | ≤25 | standard |
| `GET` | `/organizations` | List organizations | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/organizations` | Create a organization | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/organizations/{id}` | Soft-delete or cancel one organization | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/organizations/{id}` | Get one organization | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/organizations/{id}` | Patch one organization | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/organizations/{id}/contacts` | List active and historical contact relationships for an organization | staff | 200 | 1200 ms | ≤25 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/addresses?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List address records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "addresse",
      "id": "01K2ADDRESSE00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Addresse"
      }
    }
  ],
  "links": {
    "self": "/api/v1/addresses?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/addresses?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM addresses WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/addresses`

**Purpose:** Create one address

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "addresse",
    "attributes": {
      "state": "ACTIVE",
      "name": "Addresse"
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "addresse",
    "id": "01K2ADDRESSE00000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Addresse",
      "last_action": "ADDRESSES",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM addresses with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Field-level policy for private/restricted data; enumeration-safe IDs; collect only configured address fields; original/display values retained; changes audited.

### Performance and resource budget

List p95 ≤1.4s, detail ≤1.5s; standard detail ≤25 queries; indexes on public ID, normalized name/email/phone/domain, owner/state/updated.

### Testing required

Normalization locales, duplicate exact cases, primary uniqueness, relationship end/new employer, concurrent edit, unauthorized field POST, soft delete/restore, search performance.

### What success looks like

Staff can find one canonical customer/person, see current and historical relationships, and no creation path silently starts a second active identity when a strong match exists.

### Required deliverables

Customer models/services/selectors; organization/contact UI/API; normalization library; relationship/contact-point tests; seed data/import mappings.


---

## S15 — Build consent, preferences, suppression and communication policy precedence

**Phase:** Phase 2 — Core domain

**Objective:** Ensure no manual or automated customer message bypasses purpose/channel choice or higher-priority holds.

**Why this step exists:** Communication automation is dangerous unless eligibility changes immediately after reply, opt-out, bounce, complaint or security/legal restriction.

**Prerequisites:** S12 policy configuration; S14 customer/contact points; S10 audit.

### What to build in the frontend

Build consent history/effective preference UI, global/purpose/channel hold display, signed preference center, suppression administration and a clear policy-explanation component on every draft/outbox item.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Admin | `/messaging/suppressions` | Communication suppression | Review purpose/channel/global holds, bounce suppression and effective precedence. | 1400 ms | ≤20 | ≤750 KB |

### How to build the frontend


#### `/messaging/suppressions` — Communication suppression

- **Purpose:** Review purpose/channel/global holds, bounce suppression and effective precedence.
- **Components:** SuppressionTable; EvidenceDrawer; CreateHoldForm
- **API/data:** GET/POST/DELETE suppressions; consent/preferences/holds
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/end suppression
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** consent/suppression capability + audit
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤750 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤750 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement append-only consent evidence/current projection, signed preference link, global DNC, address/channel/purpose suppression and a single communication-policy engine with fixed precedence and reason codes.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| crm | `ConsentService` | Append purpose/channel evidence and maintain effective projection without overwriting history. | consent_preferences |
| crm | `PreferenceService` | Update customer choice immediately and expose only permitted preference controls. | consent_preferences, communication_policy_versions |
| crm | `SuppressionService` | Apply global/address/channel/purpose holds, bounce evidence and timed recovery holds by precedence. | suppression_entries |
| messaging | `UnsubscribeService` | Verify signed purpose link and append preference withdrawal before any subsequent claim. | consent_preferences, suppression_entries |

### How to build the backend services


#### `ConsentService`

- **Responsibility:** Append purpose/channel evidence and maintain effective projection without overwriting history.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** consent_preferences
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `PreferenceService`

- **Responsibility:** Update customer choice immediately and expose only permitted preference controls.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** consent_preferences, communication_policy_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SuppressionService`

- **Responsibility:** Apply global/address/channel/purpose holds, bounce evidence and timed recovery holds by precedence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** suppression_entries
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `UnsubscribeService`

- **Responsibility:** Verify signed purpose link and append preference withdrawal before any subsequent claim.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** consent_preferences, suppression_entries
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create consent_preferences, suppression_entries and communication_policy_versions; index contact/address/purpose/channel/effective dates.

### Ordered implementation procedure

1. Classify every communication purpose.
2. define precedence.
3. implement evidence append/projection.
4. implement signed tokens.
5. implement guard API shared by manual/automation.
6. persist guard decision/reasons.
7. re-evaluate at outbox claim.
8. add immediate cancellation hooks.
9. test conflicting policies.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/communication-policies` | List communication policy version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/communication-policies` | Create one communication policy version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/communication-policies/{id}` | Retire or soft-delete one communication policy version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/communication-policies/{id}` | Get one communication policy version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/communication-policies/{id}` | Update one communication policy version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/contacts/{id}/consent` | Get effective consent and evidence history | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/contacts/{id}/consent-events` | Append purpose/channel consent or withdrawal evidence | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `PATCH` | `/contacts/{id}/preferences` | Update allowed communication preferences | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/contacts/{id}/preferences/link` | Create a signed expiring preference-center link | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/organizations/{id}/communication-hold` | Create a scoped customer communication hold | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/organizations/{id}/communication-hold/{hold_id}` | End a communication hold with authority and reason | staff | 204 | 1800 ms | ≤22 | If-Match |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/communication-policies?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List communication policy version records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "communication-policie",
      "id": "01K2COMMUNIC00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Communication Policie"
      }
    }
  ],
  "links": {
    "self": "/api/v1/communication-policies?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/communication-policies?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM communication_policies WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/communication-policies`

**Purpose:** Create one communication policy version

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "communication-policie",
    "attributes": {
      "state": "ACTIVE",
      "name": "Communication Policie"
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "communication-policie",
    "id": "01K2COMMUNIC00000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Communication Policie",
      "last_action": "COMMUNICATION_POLICIES",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM communication_policies with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Token purpose/object/action binding; no consent inference from opens; service/legal classification separate; changes audited and effective before next claim; only authorized override with expiry.

### Performance and resource budget

Guard evaluation target <100ms p95 and ≤10 indexed queries; no full contact history scans; signed pages p95 ≤1.4s.

### Testing required

DNC vs service notice; unsubscribe vs quiet hours; hard bounce; reply after scheduling; low feedback; complaint; legal hold; expired/tampered token; manual-send bypass attempts.

### What success looks like

Every send intent displays a deterministic allow/hold/cancel result and reasons. Changing a preference or receiving a reply prevents an otherwise due message before transmission.

### Required deliverables

Consent/suppression models/services/UI; preference center; guard contract; purpose dictionary; precedence test matrix.


---

## S16 — Build Customer 360, normalized timeline and universal search

**Phase:** Phase 2 — Core domain

**Objective:** Give authorized staff a complete, fast, source-linked view of every customer situation.

**Why this step exists:** The product promise depends on eliminating fragmented context without creating a second copy of source data.

**Prerequisites:** S14 identity; S15 consent; source modules may initially contribute placeholders.

### What to build in the frontend

Build Customer 360 header and tabs, normalized timeline filters, source deep links, visibility labels, universal search with keyboard navigation, safe empty states and mobile priority layout.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/search` | Universal search | Find permitted customers, contacts, leads, opportunities, tickets, cases and message subjects. | 1800 ms | ≤20 | ≤750 KB |
| Staff | `/customers/{id}` | Customer 360 overview | Provide one trustworthy summary of identity, owner, active obligations, commercial status, health, next action and alerts. | 1600 ms | ≤35 | ≤1000 KB |
| Staff | `/customers/{id}/timeline` | Timeline | Chronological normalized messages, calls, notes, tasks, stage changes, support, onboarding, feedback, files and automation. | 1500 ms | ≤35 | ≤950 KB |
| Staff | `/customers/{id}/sales` | Sales tab | Show leads, opportunities, quotes, outcomes and commercial stage history. | 1500 ms | ≤25 | ≤950 KB |
| Staff | `/customers/{id}/onboarding` | Onboarding tab | Show active/completed onboarding cases, requests, blockers and progress. | 1500 ms | ≤25 | ≤950 KB |
| Staff | `/customers/{id}/support` | Support tab | Show open/recent tickets, SLA state and recurring causes. | 1500 ms | ≤25 | ≤950 KB |
| Staff | `/customers/{id}/feedback` | Feedback tab | Show survey requests/responses, themes and recovery. | 1500 ms | ≤25 | ≤950 KB |
| Staff | `/customers/{id}/success` | Success tab | Show health reasons, plans, renewals, churn/win-back and advocacy. | 1500 ms | ≤25 | ≤950 KB |

### How to build the frontend


#### `/search` — Universal search

- **Purpose:** Find permitted customers, contacts, leads, opportunities, tickets, cases and message subjects.
- **Components:** SearchBox; TypeFilters; ResultsByType; KeyboardNavigator
- **API/data:** GET /search; POST /search
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open result; save bounded search
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Permission filtering before counts
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤20 SQL, ≤750 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤20, compressed transfer ≤750 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/customers/{id}` — Customer 360 overview

- **Purpose:** Provide one trustworthy summary of identity, owner, active obligations, commercial status, health, next action and alerts.
- **Components:** CustomerHeader; LifecycleBadge; OwnerCard; NextActionCard; AlertStack; SummaryTabs
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Update permitted header fields; create action/note
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer object + field policy
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤35 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤35, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/customers/{id}/timeline` — Timeline

- **Purpose:** Chronological normalized messages, calls, notes, tasks, stage changes, support, onboarding, feedback, files and automation.
- **Components:** TabHeader; FilterBar; SourceLinkedCards; TimelineOrTable; PermissionLabels
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Context-specific create/update commands
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer object + field sensitivity
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤35 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤35, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/customers/{id}/sales` — Sales tab

- **Purpose:** Show leads, opportunities, quotes, outcomes and commercial stage history.
- **Components:** TabHeader; FilterBar; SourceLinkedCards; TimelineOrTable; PermissionLabels
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Context-specific create/update commands
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer object + field sensitivity
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤25 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤25, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/customers/{id}/onboarding` — Onboarding tab

- **Purpose:** Show active/completed onboarding cases, requests, blockers and progress.
- **Components:** TabHeader; FilterBar; SourceLinkedCards; TimelineOrTable; PermissionLabels
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Context-specific create/update commands
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer object + field sensitivity
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤25 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤25, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/customers/{id}/support` — Support tab

- **Purpose:** Show open/recent tickets, SLA state and recurring causes.
- **Components:** TabHeader; FilterBar; SourceLinkedCards; TimelineOrTable; PermissionLabels
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Context-specific create/update commands
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer object + field sensitivity
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤25 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤25, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/customers/{id}/feedback` — Feedback tab

- **Purpose:** Show survey requests/responses, themes and recovery.
- **Components:** TabHeader; FilterBar; SourceLinkedCards; TimelineOrTable; PermissionLabels
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Context-specific create/update commands
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer object + field sensitivity
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤25 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤25, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/customers/{id}/success` — Success tab

- **Purpose:** Show health reasons, plans, renewals, churn/win-back and advocacy.
- **Components:** TabHeader; FilterBar; SourceLinkedCards; TimelineOrTable; PermissionLabels
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Context-specific create/update commands
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer object + field sensitivity
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤25 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤25, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement permission-aware overview selector, timeline projector/registry, incremental source event projection, bounded search across normalized fields and read models for active obligations/alerts.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| crm | `Customer360Selector` | Assemble permission-aware overview from source domains without copying operational truth. | organizations, contacts, opportunities, tickets, onboarding_cases, feedback_responses, health_snapshots, renewals |
| crm | `TimelineProjector` | Create normalized deep-linkable timeline projections from committed source events. | timeline_events, domain_events |
| crm | `UniversalSearchService` | Search normalized indexed fields across allowed types after actor scope is applied. | organizations, contacts, leads, opportunities, tickets, onboarding_cases, email_messages |
| crm | `NoteService` | Create structured sanitized notes with explicit internal/restricted/portal visibility and correction history. | notes, timeline_events |

### How to build the backend services


#### `Customer360Selector`

- **Responsibility:** Assemble permission-aware overview from source domains without copying operational truth.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** organizations, contacts, opportunities, tickets, onboarding_cases, feedback_responses, health_snapshots, renewals
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `TimelineProjector`

- **Responsibility:** Create normalized deep-linkable timeline projections from committed source events.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** timeline_events, domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `UniversalSearchService`

- **Responsibility:** Search normalized indexed fields across allowed types after actor scope is applied.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** organizations, contacts, leads, opportunities, tickets, onboarding_cases, email_messages
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `NoteService`

- **Responsibility:** Create structured sanitized notes with explicit internal/restricted/portal visibility and correction history.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** notes, timeline_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create timeline_events and optional small projection tables; indexes on organization/contact/event time/type/visibility/source. Search uses existing normalized columns.

### Ordered implementation procedure

1. Define timeline event schema.
2. register source event renderers.
3. project from committed events idempotently.
4. build overview selector.
5. build search union/query services.
6. apply actor scope before counts.
7. paginate by time/public ID.
8. add reconciliation command.
9. profile representative data.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/notes` | List structured note records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/notes` | Create one structured note | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/notes/{id}` | Retire or soft-delete one structured note | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/notes/{id}` | Get one structured note | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/notes/{id}` | Update one structured note | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/organizations/{id}/overview` | Get Customer 360 overview projection | staff | 200 | 1200 ms | ≤35 | standard |
| `GET` | `/organizations/{id}/timeline` | Get permission-filtered customer 360 timeline | staff | 200 | 1200 ms | ≤35 | standard |
| `GET` | `/search` | Run bounded universal permission-filtered search | staff | 200 | 2000 ms | ≤20 | standard |
| `POST` | `/search` | Run complex structured read-only search | staff | 201 | 2000 ms | ≤20 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/notes?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List structured note records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "note",
      "id": "01K2NOTE000000000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Note"
      }
    }
  ],
  "links": {
    "self": "/api/v1/notes?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/notes?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM notes WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/notes`

**Purpose:** Create one structured note

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "note",
    "attributes": {
      "state": "ACTIVE",
      "name": "Note"
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "note",
    "id": "01K2NOTE000000000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Note",
      "last_action": "NOTES",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM notes with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

No restricted summaries in search/timeline; visibility change audited; count leakage prevented; file and source links reauthorize at destination.

### Performance and resource budget

Customer overview p95 ≤1.6s, ≤35 queries; timeline/search first page p95 ≤2.0s; page size 25–50; no leading wildcard on large text.

### Testing required

Cross-role results/counts, deep links, correction events, source deletion/soft delete, pagination stability, N+1, 20k contacts/300k events, mobile/keyboard.

### What success looks like

An authorized user identifies status, owner, next action, risk and recent history above the fold; search returns only permitted records within target and every timeline item links to authoritative evidence.

### Required deliverables

Customer 360 pages; timeline/search services/endpoints; projections; renderer registry; query-budget and reconciliation tests.


---

## S17 — Build duplicate review, atomic merge, data quality and customer governance

**Phase:** Phase 2 — Core domain

**Objective:** Protect canonical identity and surface incomplete/stale records as owned work.

**Why this step exists:** Uncontrolled merges are irreversible business harm; poor data silently breaks assignment, automation, scoring and reporting.

**Prerequisites:** S14 identity; S16 timeline/search; S10 audit; S34 governance may be partially scaffolded.

### What to build in the frontend

Build duplicate candidate queue, evidence comparison, field-level merge preview, dependency impact, step-up/approval, reversible map, data-quality dashboard and privacy/legal-hold customer tab.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/customers/{id}/governance` | Governance tab | Show consent, preferences, holds, privacy cases and legal hold. | 1500 ms | ≤25 | ≤950 KB |
| Staff | `/duplicates` | Duplicate review | Review exact/fuzzy evidence and perform safe previewed merge only with approval. | 1700 ms | ≤28 | ≤1000 KB |
| Staff | `/data-quality` | Data quality exceptions | Resolve missing, invalid, stale, duplicate and orphan-risk records. | 1500 ms | ≤22 | ≤800 KB |

### How to build the frontend


#### `/customers/{id}/governance` — Governance tab

- **Purpose:** Show consent, preferences, holds, privacy cases and legal hold.
- **Components:** TabHeader; FilterBar; SourceLinkedCards; TimelineOrTable; PermissionLabels
- **API/data:** GET/POST/PATCH /organizations; GET /organizations/{id}/overview; GET /organizations/{id}/timeline; customer subresources
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Context-specific create/update commands
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Customer object + field sensitivity
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤25 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤25, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/duplicates` — Duplicate review

- **Purpose:** Review exact/fuzzy evidence and perform safe previewed merge only with approval.
- **Components:** CandidateTable; EvidenceComparison; ConflictGrid; MergePreview; DecisionDialog
- **API/data:** GET /duplicate-candidates; POST /duplicate-candidates/{id}/decision; merge preview/execute
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Accept/reject/not-duplicate; execute merge
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** merge capability + step-up
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1700 ms, ≤28 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1700 ms, SQL count ≤28, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/data-quality` — Data quality exceptions

- **Purpose:** Resolve missing, invalid, stale, duplicate and orphan-risk records.
- **Components:** RuleSummary; IssueTable; FieldEvidence; ResolutionForm
- **API/data:** GET /data-quality/issues; POST /data-quality/issues/{id}/resolve
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Resolve/accept exception
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Operations scope + source record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement exact/fuzzy candidate generation, human decisions, atomic merge re-parenting and alias map, integrity checks, completeness rules, soft-delete/restore/purge hooks, restricted-field access audit and governance case links.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| crm | `DuplicateDetectionService` | Generate explainable exact/fuzzy candidate pairs without automatic merge. | duplicate_candidates, organizations, contacts, contact_points |
| crm | `MergeService` | Preview field/relationship conflicts, atomically re-parent safe references, preserve aliases and reversible mapping. | merge_records, organizations, contacts and dependent foreign keys |
| crm | `DataQualityService` | Evaluate lifecycle-specific completeness, invalid/stale/orphan rules and create actionable issues. | data quality projections, organizations, contacts and operational tables |

### How to build the backend services


#### `DuplicateDetectionService`

- **Responsibility:** Generate explainable exact/fuzzy candidate pairs without automatic merge.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** duplicate_candidates, organizations, contacts, contact_points
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `MergeService`

- **Responsibility:** Preview field/relationship conflicts, atomically re-parent safe references, preserve aliases and reversible mapping.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** merge_records, organizations, contacts and dependent foreign keys
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `DataQualityService`

- **Responsibility:** Evaluate lifecycle-specific completeness, invalid/stale/orphan rules and create actionable issues.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** data quality projections, organizations, contacts and operational tables
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create duplicate_candidates, merge_records/maps/field decisions, data-quality issue projection, privacy_cases and legal_holds foundations.

### Ordered implementation procedure

1. Define match signals/thresholds.
2. generate candidates asynchronously/bounded.
3. build preview.
4. lock both records and dependencies.
5. apply chosen field/relationship mappings atomically.
6. preserve source IDs/history.
7. create reversible period.
8. run post-merge reconciliation.
9. implement quality rules/ownership.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/data-quality/issues` | List actionable data-quality exceptions | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/data-quality/issues/{id}/resolve` | Resolve or accept a data-quality exception with evidence | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/duplicate-candidates` | List explainable duplicate candidates awaiting review | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/duplicate-candidates/{id}/decision` | Accept, reject, or mark a duplicate candidate as not duplicate | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/organizations/{id}/merge` | Execute an approved atomic organization merge | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/organizations/{id}/merge-preview` | Create a no-side-effect merge preview | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/data-quality/issues?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List actionable data-quality exceptions

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "issue",
      "id": "01K2ISSUE00000000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Issue"
      }
    }
  ],
  "links": {
    "self": "/api/v1/data-quality/issues?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/data-quality/issues?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM issues WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/data-quality/issues/{id}/resolve`

**Purpose:** Resolve or accept a data-quality exception with evidence

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "resolve",
    "id": "01K2RESOLVE000000000000000",
    "version": 8,
    "attributes": {
      "state": "RESOLVED",
      "name": "Resolve",
      "last_action": "RESOLVE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM resolves with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Never auto-merge; step-up/four-eyes for destructive merge; portal grants/consent/files checked; legal hold blocks purge; restricted access audited.

### Performance and resource budget

Candidate list p95 ≤1.5s; preview p95 ≤1.7s; merge duration bounded and measured, with maintenance/queued path if unusually large; indexed normalized signals.

### Testing required

Race with concurrent edit, failed child re-parent rollback, conflicting consent/contact points, portal isolation after merge, undo before compaction, quality rule reconciliation, held records.

### What success looks like

No merge loses history, consent, files or authorship; a failed merge leaves no partial state; every quality exception has exact record/field, severity, owner and resolution evidence.

### Required deliverables

Duplicate/merge engine and UI; data-quality rules/dashboard; privacy/legal-hold scaffolding; merge and rollback tests.


---

## S18 — Build tasks, activities, approvals and unified work queue

**Phase:** Phase 2 — Core domain

**Objective:** Convert every lifecycle obligation and customer signal into owned, due, traceable human work.

**Why this step exists:** Zero-drop operation is impossible without one cross-module queue and durable reminders.

**Prerequisites:** S09 users/queues/delegation; S13 state patterns; S16 customer context.

### What to build in the frontend

Build operational home queue, task list/detail, activity composer, approval queue/detail, calendar, notifications, transparent rank reasons and bounded bulk actions.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/work` | Unified work queue | Rank mandatory work transparently across tasks, replies, approvals, SLA exceptions, recovery and failures. | 1500 ms | ≤22 | ≤900 KB |
| Staff | `/work/tasks` | Task list | Search and manage owned/team tasks with due-state and source context. | 1400 ms | ≤20 | ≤750 KB |
| Staff | `/work/tasks/{id}` | Task detail | Complete an obligation with structured outcome and linked customer context. | 1200 ms | ≤22 | ≤650 KB |
| Staff | `/work/approvals` | Approval queue | Review quote, message, workflow, model and sensitive-operation approvals. | 1300 ms | ≤20 | ≤700 KB |
| Staff | `/work/approvals/{id}` | Approval decision | Inspect immutable request snapshot and record approve/reject/request-change. | 1300 ms | ≤22 | ≤700 KB |
| Staff | `/work/calendar` | CRM calendar | View due tasks, renewals, onboarding milestones and SLA reminders without external calendar. | 1500 ms | ≤18 | ≤850 KB |
| Staff | `/notifications` | Notifications | Review deduplicated alerts and acknowledge them. | 1100 ms | ≤14 | ≤500 KB |

### How to build the frontend


#### `/work` — Unified work queue

- **Purpose:** Rank mandatory work transparently across tasks, replies, approvals, SLA exceptions, recovery and failures.
- **Components:** QueueFilters; RankedWorkList; BulkActionBar; QueueReason
- **API/data:** GET /work-queue; GET/POST/PATCH /tasks; POST task commands; GET/POST /activities
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Claim, complete, delegate, snooze, release
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Queue membership + source-object permission
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤900 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤900 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/work/tasks` — Task list

- **Purpose:** Search and manage owned/team tasks with due-state and source context.
- **Components:** FilterBar; TaskTable; SavedViewPicker; QuickCreate
- **API/data:** GET /work-queue; GET/POST/PATCH /tasks; POST task commands; GET/POST /activities
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/update/complete/cancel/snooze/delegate
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Task object scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤750 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤750 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/work/tasks/{id}` — Task detail

- **Purpose:** Complete an obligation with structured outcome and linked customer context.
- **Components:** TaskHeader; OutcomeForm; SourceContext; TaskHistory
- **API/data:** GET /work-queue; GET/POST/PATCH /tasks; POST task commands; GET/POST /activities
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Edit, complete, cancel, snooze, delegate
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Task + source object scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1200 ms, ≤22 SQL, ≤650 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1200 ms, SQL count ≤22, compressed transfer ≤650 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/work/approvals` — Approval queue

- **Purpose:** Review quote, message, workflow, model and sensitive-operation approvals.
- **Components:** ApprovalTable; DeadlineBadges; SnapshotDiff
- **API/data:** GET /approval-requests; GET /approval-requests/{id}; POST /approval-requests/{id}/decision
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open/decide request
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Reviewer capability and request scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1300 ms, ≤20 SQL, ≤700 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1300 ms, SQL count ≤20, compressed transfer ≤700 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/work/approvals/{id}` — Approval decision

- **Purpose:** Inspect immutable request snapshot and record approve/reject/request-change.
- **Components:** ApprovalHeader; SnapshotViewer; DiffPanel; DecisionForm
- **API/data:** GET /approval-requests; GET /approval-requests/{id}; POST /approval-requests/{id}/decision
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Record immutable decision
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Reviewer + four-eyes constraints
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1300 ms, ≤22 SQL, ≤700 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1300 ms, SQL count ≤22, compressed transfer ≤700 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/work/calendar` — CRM calendar

- **Purpose:** View due tasks, renewals, onboarding milestones and SLA reminders without external calendar.
- **Components:** CalendarToolbar; DayWeekMonthGrid; AccessibleAgenda
- **API/data:** GET /calendar
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open work; reschedule where policy permits
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Actor scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤18 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤18, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/notifications` — Notifications

- **Purpose:** Review deduplicated alerts and acknowledge them.
- **Components:** NotificationList; SeverityFilter; AcknowledgeAction
- **API/data:** Server-rendered view; API selected from implementation matrix by capability
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Acknowledge/open
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Own or team notification scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1100 ms, ≤14 SQL, ≤500 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1100 ms, SQL count ≤14, compressed transfer ≤500 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement task lifecycle/recurrence, durable reminder jobs, activity logging/meaningful interaction, derived work queue projection, atomic claim/release, approvals/snapshot invalidation, escalation and digest preparation.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| activities | `TaskService` | Create, update, complete, cancel, delegate and policy-snooze owned obligations with structured outcomes. | tasks, task_events, work_queue_items |
| activities | `RecurrenceService` | Expand bounded future task occurrences with DST/month-end-safe rules and distinct skip/completion. | tasks, task_events, scheduled_jobs |
| activities | `ActivityService` | Log calls, meetings and assisted channels with meaningful interaction and next step. | activities, timeline_events |
| activities | `WorkQueueService` | Project and transparently rank tasks, replies, approvals, SLA exceptions, recovery and automation failures. | work_queue_items and source tables |
| activities | `ClaimService` | Atomically claim/release shared queue work without double ownership. | work_queue_items, queue_memberships |
| work | `ApprovalService` | Create immutable request snapshots, invalidate stale requests and record four-eyes decisions. | approval_requests, approval_decisions |
| activities | `NotificationService` | Deduplicate, deliver and acknowledge permission-aware staff notifications. | notifications |
| activities | `EscalationService` | Create/update one escalation per logical breach with owner, elapsed time and required decision. | tasks, work_queue_items, notifications, domain_events |

### How to build the backend services


#### `TaskService`

- **Responsibility:** Create, update, complete, cancel, delegate and policy-snooze owned obligations with structured outcomes.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tasks, task_events, work_queue_items
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RecurrenceService`

- **Responsibility:** Expand bounded future task occurrences with DST/month-end-safe rules and distinct skip/completion.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tasks, task_events, scheduled_jobs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ActivityService`

- **Responsibility:** Log calls, meetings and assisted channels with meaningful interaction and next step.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** activities, timeline_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `WorkQueueService`

- **Responsibility:** Project and transparently rank tasks, replies, approvals, SLA exceptions, recovery and automation failures.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** work_queue_items and source tables
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ClaimService`

- **Responsibility:** Atomically claim/release shared queue work without double ownership.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** work_queue_items, queue_memberships
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ApprovalService`

- **Responsibility:** Create immutable request snapshots, invalidate stale requests and record four-eyes decisions.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** approval_requests, approval_decisions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `NotificationService`

- **Responsibility:** Deduplicate, deliver and acknowledge permission-aware staff notifications.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** notifications
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `EscalationService`

- **Responsibility:** Create/update one escalation per logical breach with owner, elapsed time and required decision.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tasks, work_queue_items, notifications, domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create tasks, task_events, activities, work_queue_items, approval_requests/decisions and notifications with state/owner/queue/due indexes.

### Ordered implementation procedure

1. Define source-to-work projection contract.
2. implement task service.
3. implement recurrence.
4. implement claim atomicity.
5. implement approvals.
6. project replies/SLA/recovery/failures.
7. implement ranking.
8. add calendar/timezone.
9. add integrity checks and dashboards.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/activities` | List logged activity records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/activities` | Create one logged activity | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/activities/{id}` | Retire or soft-delete one logged activity | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/activities/{id}` | Get one logged activity | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/activities/{id}` | Update one logged activity | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/approval-requests` | List approval-requests | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/approval-requests` | Create a approval request | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/approval-requests/{id}` | Soft-delete or cancel one approval request | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/approval-requests/{id}` | Get one approval request | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/approval-requests/{id}` | Patch one approval request | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/approval-requests/{id}/decision` | Record immutable approval decision | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/calendar` | Get bounded CRM work calendar in company/user timezone | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/notifications` | List permission-filtered staff notifications | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/notifications/{id}/acknowledge` | Acknowledge a notification | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/tasks` | List tasks | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/tasks` | Create a task | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/tasks/{id}` | Soft-delete or cancel one task | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/tasks/{id}` | Get one task | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/tasks/{id}` | Patch one task | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/tasks/{id}/cancel` | Cancel a task with reason | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/tasks/{id}/complete` | Complete a task with required structured outcome | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/tasks/{id}/delegate` | Delegate an open task within allowed scope and interval | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/tasks/{id}/snooze` | Policy-bounded task snooze | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/work-queue` | List the operational home queue ordered by transparent rank | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/work-queue/{id}/claim` | Atomically claim a shared queue item | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/work-queue/{id}/release` | Release a claimed queue item safely | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/activities?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN`

**Purpose:** List logged activity records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "activitie",
      "id": "01K2ACTIVITI00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Activitie"
      }
    }
  ],
  "links": {
    "self": "/api/v1/activities?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN",
    "next": "/api/v1/activities?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM activities WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/tasks/{id}/complete`

**Purpose:** Complete a task with required structured outcome

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "task",
    "id": "01K2TASK000000000000000000",
    "version": 8,
    "attributes": {
      "subject": "Call prospect about technical requirements",
      "state": "COMPLETED",
      "priority": "HIGH",
      "owner_id": "01K2OWNER000000000000000001",
      "due_at": "2026-07-15T09:00:00Z",
      "last_action": "COMPLETE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM tasks with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); INDEX(state, owner_id, due_at, priority, public_id); INDEX(queue_id, state, due_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Queue and source object both authorize access; private activity summaries omitted; snooze cannot hide hard SLA; approval actor separation; bulk actions capped/previewed.

### Performance and resource budget

Queue first page p95 ≤1.5s and ≤22 queries; task mutation ≤1.8s; rank computed from indexed projection rather than large runtime union.

### Testing required

Two-user claim race, reminder restart, recurrence DST/month-end, stale approval, delegation expiry, private activity leakage, queue reconciliation and bulk mixed failures.

### What success looks like

Every active object can create one visible work item; queue counts reconcile to source records; two users cannot claim the same work; browser closure/restart never loses reminders.

### Required deliverables

Work models/services/UI; recurrence/reminder jobs; approval framework; queue projector; ranking policy; notification and calendar tests.


---

## S19 — Build lead intake, assignment, SLA, qualification and conversion

**Phase:** Phase 3 — Commercial lifecycle

**Objective:** Turn every accepted enquiry into one accountable, deduplicated, policy-compliant sales process.

**Why this step exists:** The earliest customer experience and revenue protection depend on fast response and immediate stop when the prospect replies or opts out.

**Prerequisites:** S14 customer identity; S15 communication guard; S18 work queue; S13 state machine.

### What to build in the frontend

Build public/internal lead forms, lead queue, lead workspace, source/assignment evidence, SLA timer, qualification panel, score explanation, sequence status and conversion preview.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/sales/leads` | Lead queue | Prioritize accepted leads by SLA, source, score reasons, owner and next action. | 1400 ms | ≤22 | ≤850 KB |
| Staff | `/sales/leads/new` | Create lead | Create manual/referral lead through the same validated intake path. | 1500 ms | ≤18 | ≤600 KB |
| Staff | `/sales/leads/{id}` | Lead workspace | Qualify, respond and convert while preserving source, SLA and sequence state. | 1500 ms | ≤28 | ≤900 KB |

### How to build the frontend


#### `/sales/leads` — Lead queue

- **Purpose:** Prioritize accepted leads by SLA, source, score reasons, owner and next action.
- **Components:** LeadFilters; SLAColumn; ReasonBadges; LeadTable; BulkBoundedActions
- **API/data:** GET/POST/PATCH /leads; transition, assign, qualification, disqualify, convert
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/assign/transition/disqualify
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Sales scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤22 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤22, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/sales/leads/new` — Create lead

- **Purpose:** Create manual/referral lead through the same validated intake path.
- **Components:** LeadIntakeForm; CustomerMatchPanel; ConsentEvidence
- **API/data:** GET/POST/PATCH /leads; transition, assign, qualification, disqualify, convert
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create lead
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** create_lead capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤18 SQL, ≤600 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤18, compressed transfer ≤600 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/sales/leads/{id}` — Lead workspace

- **Purpose:** Qualify, respond and convert while preserving source, SLA and sequence state.
- **Components:** LeadHeader; QualificationPanel; Timeline; ScoreExplanation; NextAction; SequenceStatus
- **API/data:** GET/POST/PATCH /leads; transition, assign, qualification, disqualify, convert
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Assign, qualify, transition, disqualify, convert, draft message
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Lead object scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤28 SQL, ≤900 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤28, compressed transfer ≤900 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement shared intake adapters, abuse/quarantine, duplicate/existing-customer check, assignment engine, first-response SLA, acknowledgement intent, qualification snapshots, transition/invariant, source attribution, stale escalation, rules score and atomic conversion.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| sales | `LeadIntakeService` | Validate every source adapter through one intake path, dedupe, assign, start SLA and emit one accepted event. | leads, lead_source_events, contact_points, domain_events |
| sales | `AssignmentEngine` | Evaluate versioned deterministic/capacity round-robin rules and skip unavailable staff. | assignment_rule_versions, users, queue_memberships, leads |
| sales | `LeadSlaService` | Calculate source/priority first-response deadlines and stop only on meaningful human response. | leads, business_calendars, sla_policies, activities, email_messages |
| sales | `QualificationService` | Create structured need/fit/stakeholder/budget/timing snapshots and enforce transition evidence. | qualification_snapshots, leads |
| sales | `LeadTransitionService` | Apply allowed lead state machine, owner/action invariant and exit behavior. | leads, domain_events, timeline_events |
| sales | `LeadConversionService` | Atomically link/create organization, contact and opportunity while preserving lead/source history. | leads, organizations, contacts, contact_organizations, opportunities |
| sales | `LeadScoringService` | Produce rules-first fit/completeness/freshness/engagement score with reasons and abstention. | leads, predictions, prediction_reasons |

### How to build the backend services


#### `LeadIntakeService`

- **Responsibility:** Validate every source adapter through one intake path, dedupe, assign, start SLA and emit one accepted event.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** leads, lead_source_events, contact_points, domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `AssignmentEngine`

- **Responsibility:** Evaluate versioned deterministic/capacity round-robin rules and skip unavailable staff.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** assignment_rule_versions, users, queue_memberships, leads
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `LeadSlaService`

- **Responsibility:** Calculate source/priority first-response deadlines and stop only on meaningful human response.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** leads, business_calendars, sla_policies, activities, email_messages
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `QualificationService`

- **Responsibility:** Create structured need/fit/stakeholder/budget/timing snapshots and enforce transition evidence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** qualification_snapshots, leads
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `LeadTransitionService`

- **Responsibility:** Apply allowed lead state machine, owner/action invariant and exit behavior.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** leads, domain_events, timeline_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `LeadConversionService`

- **Responsibility:** Atomically link/create organization, contact and opportunity while preserving lead/source history.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** leads, organizations, contacts, contact_organizations, opportunities
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `LeadScoringService`

- **Responsibility:** Produce rules-first fit/completeness/freshness/engagement score with reasons and abstention.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** leads, predictions, prediction_reasons
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create leads, lead_source_events, qualification_snapshots and assignment rule references; indexes on state/owner/SLA/due/source/normalized contact.

### Ordered implementation procedure

1. Define intake DTO.
2. implement manual/public/email/import adapters.
3. dedupe before assignment.
4. assign deterministically.
5. start SLA and task.
6. queue permitted acknowledgement.
7. qualify/transition.
8. stop on meaningful reply.
9. convert atomically.
10. aggregate outcomes.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/leads` | List leads | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/leads` | Create a lead | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/leads/{id}` | Soft-delete or cancel one lead | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/leads/{id}` | Get one lead | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/leads/{id}` | Patch one lead | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/leads/{id}/assign` | Assign or override lead ownership with rule evidence | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/leads/{id}/convert` | Atomically link/create canonical contact, organization, and opportunity | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/leads/{id}/disqualify` | Disqualify lead with structured reason and optional review date | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/leads/{id}/qualification` | Create a structured qualification snapshot | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/leads/{id}/source-events` | List append-only lead source attribution events | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/leads/{id}/transition` | Apply an allowed lead state transition | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/leads?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN`

**Purpose:** List leads

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "lead",
      "id": "01K2LEAD000000000000000000",
      "version": 7,
      "attributes": {
        "state": "NEW",
        "source_code": "WEB_INQUIRY",
        "priority": "NORMAL",
        "owner_id": "01K2OWNER000000000000000001",
        "first_response_due_at": "2026-07-14T11:00:00Z",
        "next_action_at": "2026-07-14T10:30:00Z"
      }
    }
  ],
  "links": {
    "self": "/api/v1/leads?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN",
    "next": "/api/v1/leads?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM leads WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, owner_id, next_action_at, public_id); INDEX(first_response_due_at, state, public_id); INDEX(source_code, created_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/leads/{id}/transition`

**Purpose:** Apply an allowed lead state transition

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "target_state": "ENGAGED",
      "evidence": {
        "meaningful_reply_message_id": "01K2MESSAGE0000000000000001"
      },
      "next_action_at": "2026-07-15T09:00:00Z"
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "lead",
    "id": "01K2LEAD000000000000000000",
    "version": 8,
    "attributes": {
      "state": "ENGAGED",
      "source_code": "WEB_INQUIRY",
      "priority": "NORMAL",
      "owner_id": "01K2OWNER000000000000000001",
      "first_response_due_at": "2026-07-14T11:00:00Z",
      "next_action_at": "2026-07-15T09:00:00Z",
      "prior_state": "CONTACTING"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM leads with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); INDEX(state, owner_id, next_action_at, public_id); INDEX(first_response_due_at, state, public_id); INDEX(source_code, created_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Public rate limits/honeypot/timing; no automation from quarantined import/form; consent guard; owner/action invariant; low score never blocks review; no arbitrary bulk recipients.

### Performance and resource budget

Public form p95 ≤1.8s; staff list/detail ≤1.5s; create/transition ≤1.8s; response warning jobs within one Cron interval; indexed list ≤22 queries.

### Testing required

Equivalent source payloads, duplicate event/replay, assignment absence/capacity, business calendar, auto-ack not human response, reply race, disqualify/nurture/convert rollback, score abstention.

### What success looks like

Each accepted lead has one owner, SLA, future action and source evidence within the request/first Cron interval; duplicate intake never starts a second sequence; conversion creates one linked opportunity.

### Required deliverables

Lead frontend/backend/API; public form; assignment/SLA/qualification/conversion; rules score; reports and UAT-02/03/04 evidence.


---

## S20 — Build opportunities, pipelines, catalogue, stakeholders and risk

**Phase:** Phase 3 — Commercial lifecycle

**Objective:** Manage evidence-based commercial progression with accurate values, forecast source and next actions.

**Why this step exists:** Generic stage boards without enforced evidence create misleading forecasts and stalled deals.

**Prerequisites:** S19 leads; S12 configuration; S13 transitions; S18 tasks.

### What to build in the frontend

Build opportunity list/board/detail, keyboard stage movement dialog, pipeline/catalgoue administration, stakeholder and product-line editors, risk reasons and forecast categories.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/sales/opportunities` | Opportunity list | Manage open commercial pursuits, forecast source, stage age, value, risk and next action. | 1500 ms | ≤22 | ≤850 KB |
| Staff | `/sales/pipeline` | Pipeline board | Visualize stage columns without relying on drag-only interaction. | 1700 ms | ≤24 | ≤1000 KB |
| Staff | `/sales/opportunities/{id}` | Opportunity workspace | Manage stakeholders, products, risks, quotes, approvals, stage evidence and next action. | 1600 ms | ≤32 | ≤1050 KB |
| Staff | `/sales/catalog` | Product and service catalogue | Govern active dates, codes, pricing guidance and onboarding mappings. | 1400 ms | ≤20 | ≤750 KB |
| Staff | `/sales/pipelines` | Pipeline configuration | Define versioned stages, required evidence, SLA and allowed transitions. | 1600 ms | ≤26 | ≤1000 KB |

### How to build the frontend


#### `/sales/opportunities` — Opportunity list

- **Purpose:** Manage open commercial pursuits, forecast source, stage age, value, risk and next action.
- **Components:** OpportunityFilters; Table; ForecastBadges; RiskReasons; SavedViews
- **API/data:** GET/POST/PATCH /opportunities; transitions, stakeholders, lines, forecast report
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/update/pause/transition
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Sales scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/sales/pipeline` — Pipeline board

- **Purpose:** Visualize stage columns without relying on drag-only interaction.
- **Components:** StageColumns; OpportunityCards; KeyboardMoveDialog; StageTotals
- **API/data:** GET/POST/PATCH /opportunities; transitions, stakeholders, lines, forecast report
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Transition through explicit dialog/evidence
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Sales scope; stage permission
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1700 ms, ≤24 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1700 ms, SQL count ≤24, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/sales/opportunities/{id}` — Opportunity workspace

- **Purpose:** Manage stakeholders, products, risks, quotes, approvals, stage evidence and next action.
- **Components:** OpportunityHeader; StageStepper; StakeholderPanel; LineItems; RiskPanel; QuoteList; Timeline
- **API/data:** GET/POST/PATCH /opportunities; transitions, stakeholders, lines, forecast report
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Update, transition, pause, mark lost/won through commands
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Opportunity scope + financial field policy
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤32 SQL, ≤1050 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤32, compressed transfer ≤1050 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/sales/catalog` — Product and service catalogue

- **Purpose:** Govern active dates, codes, pricing guidance and onboarding mappings.
- **Components:** CatalogueTable; VersionForm; MappingPanel
- **API/data:** GET/POST/PATCH /products; GET/POST /exchange-rates
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/update/retire catalogue item
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** catalog_admin capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤750 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤750 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/sales/pipelines` — Pipeline configuration

- **Purpose:** Define versioned stages, required evidence, SLA and allowed transitions.
- **Components:** PipelineList; StageEditor; TransitionMatrix; DependencyPanel
- **API/data:** GET/POST/PATCH /opportunities; transitions, stakeholders, lines, forecast report
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create draft version; validate/activate
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** pipeline_admin + approval
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤26 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤26, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement pipeline versions/stages, opportunity creation/update, stage transition/history, stakeholders, product catalogue/effective version, line items, stored exchange rates, forecast category, probability source, stall/risk calculation and pause/wake-up.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| sales | `PipelineService` | Manage immutable pipeline versions, stages, transition matrix, exit evidence and SLA. | pipelines, pipeline_versions, pipeline_stages |
| sales | `OpportunityService` | Create/update value, currency, close date, forecast source, owner/action, stakeholders and lines. | opportunities, opportunity_contacts, opportunity_lines |
| sales | `OpportunityTransitionService` | Validate stage evidence and append effective history including backward-move reason. | opportunities, opportunity_stage_events, domain_events |
| sales | `OpportunityRiskService` | Calculate deterministic risk from staleness, stakeholders, dates, quote, objections and service signals. | opportunities, quotes, tickets, feedback_responses, predictions |
| sales | `ProductCatalogueService` | Govern effective-dated products, codes, pricing guidance and onboarding mappings. | product_services |
| sales | `ExchangeRateService` | Store authorized deterministic rates and sources; never call live external rate API. | exchange_rates |

### How to build the backend services


#### `PipelineService`

- **Responsibility:** Manage immutable pipeline versions, stages, transition matrix, exit evidence and SLA.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** pipelines, pipeline_versions, pipeline_stages
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OpportunityService`

- **Responsibility:** Create/update value, currency, close date, forecast source, owner/action, stakeholders and lines.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** opportunities, opportunity_contacts, opportunity_lines
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OpportunityTransitionService`

- **Responsibility:** Validate stage evidence and append effective history including backward-move reason.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** opportunities, opportunity_stage_events, domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OpportunityRiskService`

- **Responsibility:** Calculate deterministic risk from staleness, stakeholders, dates, quote, objections and service signals.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** opportunities, quotes, tickets, feedback_responses, predictions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ProductCatalogueService`

- **Responsibility:** Govern effective-dated products, codes, pricing guidance and onboarding mappings.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** product_services
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ExchangeRateService`

- **Responsibility:** Store authorized deterministic rates and sources; never call live external rate API.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** exchange_rates
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create pipelines/versions/stages, product_services, exchange_rates, opportunities, opportunity_contacts/lines and stage events with stage/owner/close-date/action indexes.

### Ordered implementation procedure

1. Approve pipelines.
2. implement versioned configuration.
3. create opportunity service.
4. add stakeholders/lines.
5. implement stage evidence.
6. append timing history.
7. implement risk reasons.
8. handle close-date slips and pause.
9. build board/list/detail.
10. profile forecast queries.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/exchange-rates` | List stored exchange rate records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/exchange-rates` | Create one stored exchange rate | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/exchange-rates/{id}` | Retire or soft-delete one stored exchange rate | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/exchange-rates/{id}` | Get one stored exchange rate | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/exchange-rates/{id}` | Update one stored exchange rate | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/opportunities` | List opportunities | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/opportunities` | Create a opportunity | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/opportunities/{id}` | Soft-delete or cancel one opportunity | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/opportunities/{id}` | Get one opportunity | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/opportunities/{id}` | Patch one opportunity | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/opportunities/{id}/lines` | List selected product/service lines | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/opportunities/{id}/lines` | Add a governed product/service line | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/opportunities/{id}/pause` | Pause opportunity with review date and communication plan | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/opportunities/{id}/stakeholders` | List opportunity stakeholder roles and influence | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/opportunities/{id}/stakeholders` | Add or update an opportunity stakeholder | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/opportunities/{id}/transition` | Apply an evidence-gated opportunity stage transition | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/pipeline-versions` | List pipeline version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/pipeline-versions` | Create one pipeline version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/pipeline-versions/{id}` | Retire or soft-delete one pipeline version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/pipeline-versions/{id}` | Get one pipeline version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/pipeline-versions/{id}` | Update one pipeline version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/pipeline-versions/{id}/activate` | Activate a reviewed pipeline version | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/pipelines` | List pipeline records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/pipelines` | Create one pipeline | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/pipelines/{id}` | Retire or soft-delete one pipeline | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/pipelines/{id}` | Get one pipeline | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/pipelines/{id}` | Update one pipeline | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/products` | List product/service records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/products` | Create one product/service | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/products/{id}` | Retire or soft-delete one product/service | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/products/{id}` | Get one product/service | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/products/{id}` | Update one product/service | staff | 200 | 1800 ms | ≤22 | If-Match |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/exchange-rates?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN`

**Purpose:** List stored exchange rate records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "exchange-rate",
      "id": "01K2EXCHANGE00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Exchange Rate"
      }
    }
  ],
  "links": {
    "self": "/api/v1/exchange-rates?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN",
    "next": "/api/v1/exchange-rates?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM exchange_rates WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/opportunities/{id}/transition`

**Purpose:** Apply an evidence-gated opportunity stage transition

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "target_stage_code": "SOLUTION",
      "exit_evidence": {
        "need_confirmed": true,
        "decision_date": "2026-09-15",
        "stakeholder_ids": [
          "01K2CONTACT0000000000000000"
        ]
      },
      "next_action_at": "2026-07-18T08:00:00Z"
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "opportunity",
    "id": "01K2OPPORTUN00000000000000",
    "version": 8,
    "attributes": {
      "name": "Managed hosting migration",
      "stage_code": "SOLUTION",
      "forecast_category": "PIPELINE",
      "value": "12500.00",
      "currency": "USD",
      "expected_close_date": "2026-09-30",
      "owner_id": "01K2OWNER000000000000000001",
      "next_action_at": "2026-07-18T08:00:00Z",
      "prior_stage_code": "DISCOVERY"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM opportunities with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); INDEX(stage_id, owner_id, next_action_at, public_id); INDEX(expected_close_date, forecast_category, public_id); INDEX(organization_id, state, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Financial field restrictions; no stage drag bypass; override probability/forecast reason; retired catalogue cannot be newly selected; direct API cannot alter stage without command.

### Performance and resource budget

List/board/detail p95 ≤1.7s; detail ≤32 queries; stage transition ≤1.8s; forecast/drilldown ≤2.0s; indexes avoid stage-column N+1.

### Testing required

Every edge/evidence; concurrent transition; missing stakeholder risk; currency/rounding; retired product; close-date slip; pause expiry; board keyboard/accessibility; report reconciliation.

### What success looks like

Every active opportunity has owner, value/currency, stage, close date and next action; stage history reconstructs velocity; risk reasons are visible and deterministic; board totals reconcile.

### Required deliverables

Opportunity/pipeline/catalogue frontend/backend/API; risk service; forecast projections; stage and financial tests.


---

## S21 — Build quotes, approvals, issue/delivery and atomic won/lost handoff

**Phase:** Phase 3 — Commercial lifecycle

**Objective:** Produce reproducible commercial documents and convert outcomes into the downstream customer lifecycle exactly once.

**Why this step exists:** A quote is commercial evidence; mutable issued documents or partial won handoffs create financial and delivery disputes.

**Prerequisites:** S20 opportunities/catalogue; S18 approval; S11 files; S15 policy.

### What to build in the frontend

Build quote list/editor/version switcher, line totals, approval snapshot/diff, signed delivery evidence, expiry warnings, won/lost dialogs and handoff completeness review.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/sales/quotes` | Quotes | List draft/approval/issued/expired quote versions and delivery state. | 1400 ms | ≤20 | ≤800 KB |
| Staff | `/sales/quotes/{id}` | Quote editor and evidence | Build versioned line items, freeze issued snapshot and reproduce delivery evidence. | 1700 ms | ≤30 | ≤1100 KB |

### How to build the frontend


#### `/sales/quotes` — Quotes

- **Purpose:** List draft/approval/issued/expired quote versions and delivery state.
- **Components:** QuoteFilters; QuoteTable; ApprovalState; ExpiryBadges
- **API/data:** GET/POST/PATCH /quotes and /quote-versions; approval, issue, deliver, expiry
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create draft, request approval, issue/deliver
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Quote and financial capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/sales/quotes/{id}` — Quote editor and evidence

- **Purpose:** Build versioned line items, freeze issued snapshot and reproduce delivery evidence.
- **Components:** QuoteHeader; VersionSwitcher; LineEditor; Totals; ApprovalPanel; DeliveryEvidence
- **API/data:** GET/POST/PATCH /quotes and /quote-versions; approval, issue, deliver, expiry
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Edit draft; request approval; issue; deliver; supersede
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Quote scope + four-eyes thresholds
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1700 ms, ≤30 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1700 ms, SQL count ≤30, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement quote family/version/line services, decimal rounding, approval thresholds/four-eyes, issue freeze/checksum/document generation, signed link/delivery intent, expiry actions, idempotent won handoff and structured lost/no-decision outcome.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| sales | `QuoteService` | Create versioned drafts and immutable issued snapshots with exact totals, terms and checksum. | quotes, quote_versions, quote_lines |
| sales | `QuoteApprovalService` | Route threshold/exception approvals and prohibit self-approval where four-eyes applies. | approval_requests, approval_decisions, quote_versions |
| sales | `QuoteIssueService` | Freeze approved version, generate private document, create guarded delivery draft and record delivery evidence. | quote_versions, file_assets, outbox_messages |
| sales | `WonHandoffService` | Atomically freeze won facts and create exactly one onboarding, success profile and renewal chain. | opportunities, onboarding_cases, customer_success_profiles, renewals, domain_events |
| sales | `OpportunityOutcomeService` | Record lost/no-decision evidence, stop incompatible workflows and preserve learning labels. | opportunities, opportunity_stage_events, outcome_labels |

### How to build the backend services


#### `QuoteService`

- **Responsibility:** Create versioned drafts and immutable issued snapshots with exact totals, terms and checksum.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** quotes, quote_versions, quote_lines
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `QuoteApprovalService`

- **Responsibility:** Route threshold/exception approvals and prohibit self-approval where four-eyes applies.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** approval_requests, approval_decisions, quote_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `QuoteIssueService`

- **Responsibility:** Freeze approved version, generate private document, create guarded delivery draft and record delivery evidence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** quote_versions, file_assets, outbox_messages
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `WonHandoffService`

- **Responsibility:** Atomically freeze won facts and create exactly one onboarding, success profile and renewal chain.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** opportunities, onboarding_cases, customer_success_profiles, renewals, domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OpportunityOutcomeService`

- **Responsibility:** Record lost/no-decision evidence, stop incompatible workflows and preserve learning labels.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** opportunities, opportunity_stage_events, outcome_labels
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create quotes, quote_versions, quote_lines, approval links and won-handoff uniqueness; index opportunity/state/expiry/version.

### Ordered implementation procedure

1. Define commercial calculation rules.
2. create drafts/versions.
3. validate totals/terms.
4. request approval on immutable snapshot hash.
5. freeze issue.
6. generate private document.
7. deliver via guarded outbox.
8. handle expiry/replacement.
9. validate handoff.
10. mark won atomically or record lost evidence.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `POST` | `/opportunities/{id}/mark-lost` | Close opportunity as lost/no-decision with structured evidence | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/opportunities/{id}/mark-won` | Execute idempotent won handoff and create onboarding/success/renewal records | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/quote-versions` | List quote version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/quote-versions` | Create one quote version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/quote-versions/{id}` | Retire or soft-delete one quote version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/quote-versions/{id}` | Get one quote version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/quote-versions/{id}` | Update one quote version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/quote-versions/{id}/deliver` | Create guarded signed-link or attachment delivery intent | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/quote-versions/{id}/request-approval` | Request approval for an immutable quote snapshot | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/quote-versions/{id}/supersede` | Supersede an issued quote using a new draft version | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/quotes` | List quotes | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/quotes` | Create a quote | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/quotes/{id}` | Soft-delete or cancel one quote | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/quotes/{id}` | Get one quote | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/quotes/{id}` | Patch one quote | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/quotes/{id}/issue` | Freeze and issue an approved quote version | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/quote-versions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN`

**Purpose:** List quote version records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "quote-version",
      "id": "01K2QUOTEVER00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Quote Version"
      }
    }
  ],
  "links": {
    "self": "/api/v1/quote-versions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN",
    "next": "/api/v1/quote-versions?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM quote_versions WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/opportunities/{id}/mark-won`

**Purpose:** Execute idempotent won handoff and create onboarding/success/renewal records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "won-command",
    "attributes": {
      "effective_date": "2026-07-14",
      "value": "12500.00",
      "currency": "USD",
      "purchased_items": [
        {
          "product_version_id": "01K2PRODUCT0000000000000000",
          "quantity": "1.00",
          "unit_price": "12500.00"
        }
      ],
      "handoff": {
        "delivery_owner_id": "01K2USER0000000000000000003",
        "success_owner_id": "01K2USER0000000000000000005",
        "target_onboarding_completion": "2026-08-15",
        "promised_outcomes": [
          "Zero-downtime migration"
        ],
        "open_risks": [
          "DNS cutover window"
        ]
      }
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "won-handoff",
    "id": "01K2WONHANDO000000000000000",
    "version": 8,
    "attributes": {
      "opportunity_id": "01K2OPPORTUN00000000000000",
      "opportunity_stage": "WON",
      "won_at": "2026-07-14T08:00:00Z",
      "onboarding_case_id": "01K2ONBOARDI00000000000000",
      "customer_success_profile_id": "01K2SUCCESS0000000000000000",
      "renewal_id": "01K2RENEWAL000000000000000",
      "welcome_draft_id": "01K2DRAFT000000000000000000",
      "idempotent_replay": false
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM opportunities with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); INDEX(stage_id, owner_id, next_action_at, public_id); INDEX(expected_close_date, forecast_category, public_id); INDEX(organization_id, state, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Financial/discount permissions; approver separation; signed links scoped/expiring; issued version immutable; file revalidation at send; lost/won require evidence and step-up if configured.

### Performance and resource budget

Quote editor/detail p95 ≤1.7s; issue command ≤1.8s excluding queued document/mail; won transaction ≤2.5s and short locks; document generation queued if expensive.

### Testing required

Rounding/tax/discount boundaries, stale approval after edit, self-approval, issue replay, signed token tamper/expiry, delivery failure, won duplicate event/crash, incomplete handoff, lost reasons.

### What success looks like

An issued quote can be reproduced byte-for-byte from version/checksum; repeated won calls create one onboarding/success/renewal chain and one event; no outcome closes without required evidence.

### Required deliverables

Quote frontend/backend/API; calculation and document generation; approvals; signed delivery; won/lost handoff; UAT-04/05 evidence.


---

## S22 — Build mailboxes, templates, blocks and controlled drafts

**Phase:** Phase 3 — Communications

**Objective:** Create safe, reviewed customer communication content and mailbox configuration before sending automation.

**Why this step exists:** Free-form generative text and arbitrary senders are outside scope; reproducibility requires exact template/version/block evidence.

**Prerequisites:** S11 files; S12 configuration; S15 purposes; S18 approvals.

### What to build in the frontend

Build mailbox administration/test, template and block library, versioned editor, allowlisted variable dictionary, plain-text/HTML preview, draft queue and controlled composer.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/messaging/drafts` | Draft queue | List drafts awaiting edit, approval or send eligibility. | 1300 ms | ≤18 | ≤700 KB |
| Staff | `/messaging/drafts/{id}` | Controlled email draft | Assemble approved blocks, show policy result, lock approval snapshot and send intent. | 1500 ms | ≤26 | ≤900 KB |
| Staff | `/messaging/templates` | Templates | Manage versioned purpose-classified templates and block library. | 1400 ms | ≤20 | ≤750 KB |
| Staff | `/messaging/templates/{id}` | Template editor | Edit allowlisted variables, plain-text/HTML, preview, review and activate. | 1600 ms | ≤24 | ≤950 KB |
| Admin | `/messaging/mailboxes` | Mailbox administration | Configure approved SMTP/IMAP mailboxes and test connection without exposing secrets. | 1400 ms | ≤18 | ≤650 KB |

### How to build the frontend


#### `/messaging/drafts` — Draft queue

- **Purpose:** List drafts awaiting edit, approval or send eligibility.
- **Components:** DraftFilters; DraftTable; PurposeBadges; ApprovalState
- **API/data:** GET/POST/PATCH /email-drafts; request approval; send
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/open draft
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Messaging scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1300 ms, ≤18 SQL, ≤700 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1300 ms, SQL count ≤18, compressed transfer ≤700 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/messaging/drafts/{id}` — Controlled email draft

- **Purpose:** Assemble approved blocks, show policy result, lock approval snapshot and send intent.
- **Components:** RecipientPanel; BlockComposer; PlainHtmlPreview; PolicyChecklist; ApprovalPanel
- **API/data:** GET/POST/PATCH /email-drafts; request approval; send
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Edit; request approval; send
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Message purpose + recipient scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤26 SQL, ≤900 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤26, compressed transfer ≤900 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/messaging/templates` — Templates

- **Purpose:** Manage versioned purpose-classified templates and block library.
- **Components:** TemplateTable; PurposeFilter; VersionBadges
- **API/data:** GET/POST/PATCH /templates, template versions and blocks; preview/activate
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/open/retire
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** template_admin capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤750 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤750 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/messaging/templates/{id}` — Template editor

- **Purpose:** Edit allowlisted variables, plain-text/HTML, preview, review and activate.
- **Components:** TemplateEditor; VariableDictionary; PreviewContexts; Diff; Approval
- **API/data:** GET/POST/PATCH /templates, template versions and blocks; preview/activate
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create version; validate; activate
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** template_admin + reviewer
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/messaging/mailboxes` — Mailbox administration

- **Purpose:** Configure approved SMTP/IMAP mailboxes and test connection without exposing secrets.
- **Components:** MailboxTable; SecretReferenceForm; TestPanel; HealthBadges
- **API/data:** GET/POST/PATCH /email-accounts; test and health
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/update/test/disable
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** mail_admin + step-up
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤18 SQL, ≤650 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤18, compressed transfer ≤650 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement email account metadata/secret references, template/version lifecycle, safe variable resolver, HTML sanitation, plain-text alternative, approved block assembly, draft rendering hash and material-edit approval invalidation.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| messaging | `EmailAccountService` | Manage approved SMTP/IMAP mailbox metadata, secret references, purpose and health tests. | email_accounts, system_metrics |
| messaging | `TemplateService` | Manage purpose-classified template families and immutable reviewed versions with typed variable allowlist. | templates, template_versions |
| messaging | `MessageBlockService` | Manage approved greeting/context/answer/next-step/signature blocks for controlled assembly. | message_blocks |
| messaging | `DraftService` | Assemble and edit drafts, preserve source blocks, render plain/HTML and invalidate stale approvals. | email_messages, templates, template_versions, message_blocks, approval_requests |

### How to build the backend services


#### `EmailAccountService`

- **Responsibility:** Manage approved SMTP/IMAP mailbox metadata, secret references, purpose and health tests.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** email_accounts, system_metrics
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `TemplateService`

- **Responsibility:** Manage purpose-classified template families and immutable reviewed versions with typed variable allowlist.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** templates, template_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `MessageBlockService`

- **Responsibility:** Manage approved greeting/context/answer/next-step/signature blocks for controlled assembly.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** message_blocks
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `DraftService`

- **Responsibility:** Assemble and edit drafts, preserve source blocks, render plain/HTML and invalidate stale approvals.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** email_messages, templates, template_versions, message_blocks, approval_requests
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create email_accounts, templates, template_versions, message_blocks and draft/message metadata structures; index code/purpose/state/effective dates.

### Ordered implementation procedure

1. Create dedicated mailboxes.
2. define sender/purpose mappings.
3. implement template schema.
4. implement allowlisted variables/fallback.
5. implement sanitizer/plain text.
6. create block assembly.
7. persist draft/render hash.
8. add previews/test contexts.
9. add review/activation.
10. test mail clients.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/email-accounts` | List email account records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/email-accounts` | Create one email account | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/email-accounts/{id}` | Retire or soft-delete one email account | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/email-accounts/{id}` | Get one email account | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/email-accounts/{id}` | Update one email account | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/email-accounts/{id}/test` | Test SMTP/IMAP connection without sending to customers | staff | 200 | 1800 ms | ≤22 | standard |
| `POST` | `/email-drafts` | Create a policy-scoped email draft | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/email-drafts/{id}` | Get one rendered draft, source blocks, policy and approval state | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/email-drafts/{id}` | Edit draft and invalidate material approval when required | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/email-drafts/{id}/request-approval` | Lock rendered snapshot and request approval | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/message-blocks` | List approved message block records | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/message-blocks` | Create one approved message block | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/message-blocks/{id}` | Retire or soft-delete one approved message block | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/message-blocks/{id}` | Get one approved message block | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/message-blocks/{id}` | Update one approved message block | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/template-versions` | List template version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/template-versions` | Create one template version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/template-versions/{id}` | Retire or soft-delete one template version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/template-versions/{id}` | Get one template version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/template-versions/{id}` | Update one template version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/template-versions/{id}/activate` | Activate a reviewed template version | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/templates` | List templates | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/templates` | Create a template | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/templates/{id}` | Soft-delete or cancel one template | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/templates/{id}` | Get one template | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/templates/{id}` | Patch one template | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/templates/{id}/preview` | Preview a template with allowlisted test context | staff | 200 | 1800 ms | ≤22 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/email-accounts?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List email account records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "email-account",
      "id": "01K2EMAILACC00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Email Account"
      }
    }
  ],
  "links": {
    "self": "/api/v1/email-accounts?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/email-accounts?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM email_accounts WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/template-versions/{id}/activate`

**Purpose:** Activate a reviewed template version

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "activate",
    "id": "01K2ACTIVATE00000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Activate",
      "last_action": "ACTIVATE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM activates with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Credentials only environment/secret reference; no arbitrary From/Reply-To; no template code/expression; CR/LF rejection; no external fonts/scripts/tracking; attachments only authorized files.

### Performance and resource budget

Template/draft screens p95 ≤1.6s; rendering <150ms typical; request ≤1MB; preview bounded; static assets local.

### Testing required

Missing variable, unauthorized attribute, injection, unsafe HTML, CR/LF, sender override, attachment scope, material edit invalidation, plain-text parity, staging interception.

### What success looks like

Every customer message can identify exact sender, purpose, template version, source blocks, rendered hash and approval state; no configuration can execute code or choose arbitrary sender.

### Required deliverables

Mailbox/template/block/draft frontend/backend/API; content standards; approved baseline templates; sanitizer and rendering tests.


---

## S23 — Build transactional outbox, final policy guard and SMTP delivery state

**Phase:** Phase 3 — Communications

**Objective:** Ensure customer messages are low-volume, policy-compliant, auditable and recoverable across retries and ambiguous SMTP outcomes.

**Why this step exists:** Sending inline or blindly retrying after network failure creates duplicates and violates consent/hosting limits.

**Prerequisites:** S15 policy engine; S22 drafts/templates/mailboxes; S10 audit.

### What to build in the frontend

Build outbox list/detail, priority/state filters, policy evidence, attempt timeline, cancellation/retry controls and explicit delivery-unknown reconciliation UI.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Operations | `/messaging/outbox` | Outbox | Monitor ready, sending, sent, failed and delivery-unknown intents by priority. | 1400 ms | ≤20 | ≤800 KB |
| Operations | `/messaging/outbox/{id}` | Outbox evidence | Reconstruct rendered content hash, policy, approvals, attempts and delivery evidence. | 1400 ms | ≤24 | ≤900 KB |

### How to build the frontend


#### `/messaging/outbox` — Outbox

- **Purpose:** Monitor ready, sending, sent, failed and delivery-unknown intents by priority.
- **Components:** OutboxFilters; StateTable; PolicyResult; AttemptCount
- **API/data:** GET /outbox; cancel/retry/reconcile ambiguous
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Cancel/retry/reconcile allowed states
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Messaging operations capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/messaging/outbox/{id}` — Outbox evidence

- **Purpose:** Reconstruct rendered content hash, policy, approvals, attempts and delivery evidence.
- **Components:** OutboxHeader; RecipientList; PolicyEvidence; AttemptTimeline; AmbiguityPanel
- **API/data:** GET /outbox; cancel/retry/reconcile ambiguous
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Cancel/retry/reconcile ambiguous
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Restricted messaging operations
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤24 SQL, ≤900 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤24, compressed transfer ≤900 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement send-intent creation in business transaction, deterministic Message-ID/idempotency key, priority lanes, global/mailbox/contact caps, claim/final guard, SMTP MIME handoff, delivery events, transient/permanent/ambiguous classification and Sent/archive reconciliation.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| messaging | `CommunicationPolicyEngine` | Evaluate legal/security, DNC, bounce, unsubscribe, recovery, reply, severity, quiet hours, caps, duplicate objective and approval in fixed precedence. | consent_preferences, suppression_entries, communication_ledger, tickets, recovery_cases |
| messaging | `OutboxService` | Create immutable send intent in business transaction, claim by priority, final-guard at send time and preserve idempotency. | outbox_messages, delivery_events, communication_ledger |
| messaging | `SmtpTransportService` | Render MIME safely, validate headers/sender/attachments, hand off once and classify confirmed/transient/permanent/ambiguous outcomes. | outbox_messages, delivery_events, email_messages |
| messaging | `BounceService` | Classify DSN/bounce/complaint, suppress hard failures, bound soft retries and create review for ambiguity. | delivery_events, suppression_entries, contact_points |

### How to build the backend services


#### `CommunicationPolicyEngine`

- **Responsibility:** Evaluate legal/security, DNC, bounce, unsubscribe, recovery, reply, severity, quiet hours, caps, duplicate objective and approval in fixed precedence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** consent_preferences, suppression_entries, communication_ledger, tickets, recovery_cases
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OutboxService`

- **Responsibility:** Create immutable send intent in business transaction, claim by priority, final-guard at send time and preserve idempotency.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** outbox_messages, delivery_events, communication_ledger
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SmtpTransportService`

- **Responsibility:** Render MIME safely, validate headers/sender/attachments, hand off once and classify confirmed/transient/permanent/ambiguous outcomes.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** outbox_messages, delivery_events, email_messages
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `BounceService`

- **Responsibility:** Classify DSN/bounce/complaint, suppress hard failures, bound soft retries and create review for ambiguity.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** delivery_events, suppression_entries, contact_points
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create outbox_messages, delivery_events and communication_ledger with unique idempotency/message identity and state/priority/scheduled indexes.

### Ordered implementation procedure

1. Define state machine READY/CLAIMED/SENDING/SENT/FAILED/DELIVERY_UNKNOWN.
2. create intent transactionally.
3. claim bounded batch.
4. re-check policy.
5. write attempt before handoff.
6. send.
7. classify response.
8. never blind-retry unknown.
9. reconcile evidence.
10. enforce 60/hour and 10/5 minutes.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `POST` | `/email-drafts/{id}/send` | Create transactional outbox send intent after final policy check | staff | 202 | 1200 ms | ≤12 | If-Match, Idempotency-Key |
| `GET` | `/outbox` | List outbox, including ambiguous and failed sends | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/outbox/{id}` | Get one outbox intent and delivery evidence | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/outbox/{id}/cancel` | Cancel a not-yet-transmitted send intent | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/outbox/{id}/reconcile-ambiguous` | Resolve an SMTP ambiguous handoff; never automatic retry | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/outbox/{id}/retry` | Retry a confirmed safe transient failure after final policy guard | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/suppressions` | Create a channel/purpose/global suppression entry | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/suppressions/{id}` | End a suppression with authority and reason | staff | 204 | 1800 ms | ≤22 | If-Match, Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/outbox?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List outbox, including ambiguous and failed sends

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "outbox",
      "id": "01K2OUTBOX0000000000000000",
      "version": 7,
      "attributes": {
        "state": "READY",
        "priority": "SERVICE",
        "recipient_count": 1,
        "scheduled_at": "2026-07-14T08:05:00Z",
        "message_id": "<crm.01K2@example.org>"
      }
    }
  ],
  "links": {
    "self": "/api/v1/outbox?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/outbox?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM outbox_messages WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); UNIQUE(idempotency_key); UNIQUE(message_id); INDEX(state, priority, scheduled_at, public_id); INDEX(recipient_normalized, purpose, created_at)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/email-drafts/{id}/send`

**Purpose:** Create transactional outbox send intent after final policy check

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "approval_id": "01K2APPROVAL000000000000000",
      "send_at": "2026-07-14T08:05:00Z"
    }
  }
}
```

**Success:** `HTTP 202`

**Response body**

```json
{
  "data": {
    "type": "outbox-intent",
    "id": "01K2JOB000000000000000001",
    "attributes": {
      "state": "QUEUED",
      "submitted_at": "2026-07-14T08:00:00Z",
      "status_url": "/api/v1/jobs/01K2JOB000000000000000001"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001"
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1200 ms**; p99 ≤ **2500 ms** under the representative mixed workload.

- Maximum **12 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM outbox_messages with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); UNIQUE(idempotency_key); UNIQUE(message_id); INDEX(state, priority, scheduled_at, public_id); INDEX(recipient_normalized, purpose, created_at)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1200 ms and p99 ≤2500 ms on the representative mixed workload, uses ≤12 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Same guard for manual/automation; no mass recipient upload; sender allowlist; header injection prevention; BCC/archive privacy; secrets redacted; step-up for ambiguity resolution if needed.

### Performance and resource budget

Send command ≤10 messages/35s, internal cap 60/hour; web send intent p95 ≤1.8s; outbox list ≤20 queries; no request performs SMTP.

### Testing required

Crash before/after attempt/handoff, duplicate Cron, policy change after schedule, rate cap, hard/soft failure, connection timeout ambiguity, Sent reconciliation, attachment deleted, emergency stop.

### What success looks like

No confirmed duplicate customer message occurs in forced-failure tests; every ambiguous handoff becomes visible and is not retried automatically; service mail outranks relationship mail without exceeding caps.

### Required deliverables

Outbox/SMTP services; state machine; Cron command; operations UI; failure-injection suite; delivery runbook.


---

## S24 — Build IMAP ingestion, threading, inbound safety and reply-aware stopping

**Phase:** Phase 3 — Communications

**Objective:** Bring customer replies into the canonical timeline and immediately adapt automation.

**Why this step exists:** Closed-loop follow-up fails if replies are duplicated, misthreaded, unsafe or processed too late.

**Prerequisites:** S22 mailboxes; S23 messaging records; S16 timeline; S26 runtime may be scaffolded.

### What to build in the frontend

Build CRM inbox, thread detail, sanitized message viewer, attachment validation state, customer context, ambiguous match review, classify/rethread controls and reply work item.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/messaging/inbox` | CRM inbox | Show matched and ambiguous inbound conversations requiring action. | 1500 ms | ≤22 | ≤850 KB |
| Staff | `/messaging/threads/{id}` | Email thread | Read sanitized conversation, customer context, reply state and attachments. | 1500 ms | ≤30 | ≤1000 KB |

### How to build the frontend


#### `/messaging/inbox` — CRM inbox

- **Purpose:** Show matched and ambiguous inbound conversations requiring action.
- **Components:** MailboxFilter; ThreadList; UnreadAge; MatchConfidence; CustomerContext
- **API/data:** GET /email-threads; GET /email-messages; classify/rethread; draft reply
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open thread; assign; acknowledge
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Mailbox + record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/messaging/threads/{id}` — Email thread

- **Purpose:** Read sanitized conversation, customer context, reply state and attachments.
- **Components:** ThreadHeader; MessageStream; SafeHtmlViewer; AttachmentList; ReplyComposer; MatchReview
- **API/data:** GET /email-threads; GET /email-messages; classify/rethread; draft reply
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/edit draft; rethread/classify
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Thread + customer scope; visibility filter
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤30 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤30, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement bounded UID polling, mailbox cursor, MIME parser, UID/Message-ID dedupe, safe body storage/preview, threading hierarchy, reply-token/fallback confidence, intent classification hook, customer/ticket/lead matching, domain events and future-job/outbox cancellation.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| messaging | `ImapIngestionService` | Poll bounded UIDs, parse untrusted MIME defensively, dedupe and create committed inbound message events. | email_accounts, email_messages, message_recipients, message_attachments, domain_events |
| messaging | `ThreadingService` | Match by Message-ID/In-Reply-To/References/reply token, bounded fallback confidence and human review. | email_threads, email_messages |
| messaging | `ReplyStopService` | Cancel or exit future generic actions immediately after a matched meaningful reply. | domain_events, workflow_runs, scheduled_jobs, outbox_messages |
| messaging | `InboundAttachmentService` | Quarantine logically, validate type/signature/size, store privately and block inline active content. | message_attachments, file_assets |
| messaging | `MailboxHealthService` | Record connect/poll/send/UID latency/failure freshness and create incident when stale. | email_accounts, system_metrics, system_incidents |
| messaging | `MessageArchiveService` | Move large/raw bodies to checksummed compressed private storage while retaining searchable metadata. | email_messages, archive_manifests, archive_items |

### How to build the backend services


#### `ImapIngestionService`

- **Responsibility:** Poll bounded UIDs, parse untrusted MIME defensively, dedupe and create committed inbound message events.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** email_accounts, email_messages, message_recipients, message_attachments, domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ThreadingService`

- **Responsibility:** Match by Message-ID/In-Reply-To/References/reply token, bounded fallback confidence and human review.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** email_threads, email_messages
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ReplyStopService`

- **Responsibility:** Cancel or exit future generic actions immediately after a matched meaningful reply.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** domain_events, workflow_runs, scheduled_jobs, outbox_messages
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `InboundAttachmentService`

- **Responsibility:** Quarantine logically, validate type/signature/size, store privately and block inline active content.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** message_attachments, file_assets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `MailboxHealthService`

- **Responsibility:** Record connect/poll/send/UID latency/failure freshness and create incident when stale.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** email_accounts, system_metrics, system_incidents
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `MessageArchiveService`

- **Responsibility:** Move large/raw bodies to checksummed compressed private storage while retaining searchable metadata.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** email_messages, archive_manifests, archive_items
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create email_threads, email_messages, message_recipients, message_attachments and mailbox cursor/health fields; unique mailbox+UID and Message-ID indexes.

### Ordered implementation procedure

1. Poll unseen UID batch.
2. persist raw evidence safely.
3. parse headers/body/attachments defensively.
4. dedupe.
5. thread by standards.
6. match customer/context.
7. flag ambiguity.
8. commit inbound message+event.
9. create/refresh work item.
10. cancel generic future actions idempotently.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/email-accounts/{id}/health` | Get recent mailbox connect, poll, send and UID health evidence | staff | 200 | 1200 ms | ≤35 | standard |
| `GET` | `/email-messages` | List email message records | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/email-messages/{id}` | Get one email message | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/email-messages/{id}/classify` | Confirm or correct local message intent classification | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/email-messages/{id}/rethread` | Manually resolve an ambiguous inbound thread match | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/email-threads` | List email-threads | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/email-threads/{id}` | Get one email thread | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/email-threads/{id}` | Patch one email thread | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/operations/mail/poll-test` | Run bounded test mailbox poll and return diagnostic evidence | staff | 201 | 1800 ms | ≤15 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/email-accounts/{id}/health?fields[health]=id,state,owner_id,updated_at&include=owner`

**Purpose:** Get recent mailbox connect, poll, send and UID health evidence

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "health",
    "id": "01K2HEALTH0000000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Health"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1200 ms**; p99 ≤ **2800 ms** under the representative mixed workload.

- Maximum **35 SQL statements**, request **16 KB**, response **512 KB**.

- Query shape: SELECT the authorized health by public_id with actor scope in the same query; join current owner/state only; prefetch bounded child collections requested by include; return 404 before unrestricted data is materialized.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1200 ms and p99 ≤2800 ms on the representative mixed workload, uses ≤35 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/email-messages/{id}/classify`

**Purpose:** Confirm or correct local message intent classification

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "classify",
    "attributes": {
      "state": "ACTIVE",
      "name": "Classify"
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "classify",
    "id": "01K2CLASSIFY00000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Classify",
      "last_action": "CLASSIFY",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM classifys with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Inbound HTML untrusted; remote content disabled; spoofing indicators; attachment allowlist; no sender identity trust solely from From header; internal/portal visibility explicit.

### Performance and resource budget

≤25 messages/35s per poll; urgent reply visible within one five-minute interval; thread page p95 ≤1.5s; indexes prevent mailbox rescans.

### Testing required

Re-poll same UID, missing/duplicate Message-ID, References chain, fallback ambiguity, crafted MIME, oversized attachment, reply between schedule/claim, closed ticket reopen, misattributed sender.

### What success looks like

Each inbound message exists once, threads correctly or enters review, creates one actionable reply item and stops incompatible future messages within one polling/Cron interval.

### Required deliverables

IMAP/threading/inbox frontend/backend/API; safe MIME fixtures; reply-stop integration; mailbox health and recovery runbook.


---

## S25 — Build domain events, workflow definition/compiler and simulation

**Phase:** Phase 4 — Automation

**Objective:** Create a safe declarative automation language whose behavior is versioned, inspectable and side-effect free until activated.

**Why this step exists:** Hard-coded timers cannot support reliable exits, policy precedence, audit or company-managed evolution.

**Prerequisites:** S10 audit; S12 configuration; S13 states; domain services emitting committed events.

### What to build in the frontend

Build automation list/overview/builder/simulation screens with allowlisted trigger, typed condition tree, ordered steps/delays, exits, caps, approvals, conflict policy, dependencies and exact trace.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Admin | `/automation` | Automation definitions | List workflow families, current/draft versions, owners, dependencies and health. | 1400 ms | ≤20 | ≤850 KB |
| Admin | `/automation/new` | Create workflow definition | Create governed workflow identity before editing an immutable version. | 1300 ms | ≤16 | ≤550 KB |
| Admin | `/automation/{id}` | Automation overview | Review versions, metrics, dependencies, runs, approvals and rollback path. | 1600 ms | ≤26 | ≤950 KB |
| Admin | `/automation/{id}/builder` | Workflow builder | Build an acyclic allowlisted graph without executable code. | 1700 ms | ≤28 | ≤1100 KB |
| Admin | `/automation/{id}/simulate` | Workflow simulation | Evaluate draft against selected records/historical snapshots without side effects. | 1900 ms | ≤24 | ≤1200 KB |

### How to build the frontend


#### `/automation` — Automation definitions

- **Purpose:** List workflow families, current/draft versions, owners, dependencies and health.
- **Components:** WorkflowTable; StateBadges; OwnerFilter; DependencyWarnings
- **API/data:** GET/POST/PATCH /automation-definitions and versions; validate, dependencies, simulate, activate, rollback, emergency stop
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/open/retire definition
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** automation_admin capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/automation/new` — Create workflow definition

- **Purpose:** Create governed workflow identity before editing an immutable version.
- **Components:** WorkflowMetadataForm; PurposeClassification; OwnerPicker
- **API/data:** GET/POST/PATCH /automation-definitions and versions; validate, dependencies, simulate, activate, rollback, emergency stop
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create definition/version
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** automation_admin
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1300 ms, ≤16 SQL, ≤550 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1300 ms, SQL count ≤16, compressed transfer ≤550 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/automation/{id}` — Automation overview

- **Purpose:** Review versions, metrics, dependencies, runs, approvals and rollback path.
- **Components:** WorkflowHeader; VersionList; DependencyGraph; Metrics; ChangeHistory
- **API/data:** GET/POST/PATCH /automation-definitions and versions; validate, dependencies, simulate, activate, rollback, emergency stop
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create version; validate; activate/rollback
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** automation_admin + reviewer
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤26 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤26, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/automation/{id}/builder` — Workflow builder

- **Purpose:** Build an acyclic allowlisted graph without executable code.
- **Components:** TriggerEditor; ConditionTree; StepList; DelayEditor; ExitEditor; ConflictPolicy; ValidationPanel
- **API/data:** GET/POST/PATCH /automation-definitions and versions; validate, dependencies, simulate, activate, rollback, emergency stop
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save draft steps/conditions/exits
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Field dictionary + action allowlist
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1700 ms, ≤28 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1700 ms, SQL count ≤28, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/automation/{id}/simulate` — Workflow simulation

- **Purpose:** Evaluate draft against selected records/historical snapshots without side effects.
- **Components:** RecordPicker; SnapshotSelector; SimulationTrace; GuardResults; DateTimeline
- **API/data:** GET/POST/PATCH /automation-definitions and versions; validate, dependencies, simulate, activate, rollback, emergency stop
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Run simulation
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Read permission on sample records; no mutation
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1900 ms, ≤24 SQL, ≤1200 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1900 ms, SQL count ≤24, compressed transfer ≤1200 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement domain event schemas/registry, consumption ledger, workflow families/versions, compiler validation, typed field dictionary/operators, action registry, graph cycle/depth/step checks, dependency analysis and side-effect-free simulation against records/snapshots.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| automations | `DomainEventService` | Persist typed committed business facts with schema version, correlation and actor in the same transaction. | domain_events |
| automations | `EventConsumerService` | Claim and consume events idempotently using unique consumer/event ledger. | event_consumptions, domain_events |
| automations | `WorkflowDefinitionService` | Manage immutable versions, ownership, purpose, re-entry policy, caps and approval state. | automation_definitions, automation_versions |
| automations | `WorkflowCompiler` | Validate trigger/condition/action schemas, acyclic graph, depth/step limits and dependencies; produce executable JSON plan. | automation_versions, custom_field_definitions, pipeline_stages, templates, work_queues |
| automations | `ConditionEvaluator` | Evaluate typed allowlisted fields/operators with bounded boolean depth and recorded facts. | automation_versions, workflow_run_events |
| automations | `AutomationActionRegistry` | Expose only reviewed idempotent actions with explicit authorization, result and compensation semantics. | automation_versions |
| automations | `WorkflowSimulator` | Evaluate draft against selected records/snapshots and return exact dates, guards, conflicts and exits without side effects. | automation_versions, source domain tables |

### How to build the backend services


#### `DomainEventService`

- **Responsibility:** Persist typed committed business facts with schema version, correlation and actor in the same transaction.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `EventConsumerService`

- **Responsibility:** Claim and consume events idempotently using unique consumer/event ledger.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** event_consumptions, domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `WorkflowDefinitionService`

- **Responsibility:** Manage immutable versions, ownership, purpose, re-entry policy, caps and approval state.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** automation_definitions, automation_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `WorkflowCompiler`

- **Responsibility:** Validate trigger/condition/action schemas, acyclic graph, depth/step limits and dependencies; produce executable JSON plan.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** automation_versions, custom_field_definitions, pipeline_stages, templates, work_queues
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ConditionEvaluator`

- **Responsibility:** Evaluate typed allowlisted fields/operators with bounded boolean depth and recorded facts.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** automation_versions, workflow_run_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `AutomationActionRegistry`

- **Responsibility:** Expose only reviewed idempotent actions with explicit authorization, result and compensation semantics.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** automation_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `WorkflowSimulator`

- **Responsibility:** Evaluate draft against selected records/snapshots and return exact dates, guards, conflicts and exits without side effects.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** automation_versions, source domain tables
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create domain_events, event_consumptions, automation_definitions/versions and normalized/JSON validated step plan; index type/time/correlation and code/version/state.

### Ordered implementation procedure

1. Register committed event contracts.
2. implement versioned definitions.
3. define trigger/condition/action schemas.
4. implement compiler.
5. reject arbitrary code/URLs.
6. compute dependencies/cycles.
7. implement simulation clock/guards/conflicts.
8. add reviewer/activation checks.
9. create contract fixtures.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/automation-definitions` | List automation-definitions | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/automation-definitions` | Create a automation definition | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/automation-definitions/{id}` | Soft-delete or cancel one automation definition | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/automation-definitions/{id}` | Get one automation definition | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/automation-definitions/{id}` | Patch one automation definition | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/automation-definitions/{id}/activate` | Validate and activate an approved workflow version | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/automation-definitions/{id}/rollback` | Restore prior version for new enrolments with explicit in-flight policy | staff | 202 | 1200 ms | ≤12 | If-Match, Idempotency-Key |
| `POST` | `/automation-definitions/{id}/simulate` | Evaluate a draft workflow against snapshots without side effects | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/automation-versions` | List automation version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/automation-versions` | Create one automation version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/automation-versions/{id}` | Retire or soft-delete one automation version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/automation-versions/{id}` | Get one automation version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/automation-versions/{id}` | Update one automation version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/automation-versions/{id}/dependencies` | Get referenced fields, stages, templates, queues and workflows | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/automation-versions/{id}/validate` | Validate graph, fields, dependencies, limits and permissions | staff | 200 | 1800 ms | ≤22 | standard |
| `GET` | `/domain-events` | List committed domain events for diagnostics | staff | 200 | 1500 ms | ≤18 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/automation-definitions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN`

**Purpose:** List automation-definitions

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "automation-definition",
      "id": "01K2AUTOMATI00000000000000",
      "version": 7,
      "attributes": {
        "code": "WF-03",
        "name": "Lead follow-up and reply stop",
        "state": "DRAFT",
        "active_version": null,
        "owner_id": "01K2USER0000000000000000002"
      }
    }
  ],
  "links": {
    "self": "/api/v1/automation-definitions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN",
    "next": "/api/v1/automation-definitions?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM automation_definitions WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); UNIQUE(code); INDEX(state, owner_id, updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/automation-definitions/{id}/activate`

**Purpose:** Validate and activate an approved workflow version

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "automation-definition",
    "id": "01K2AUTOMATI00000000000000",
    "version": 8,
    "attributes": {
      "code": "WF-03",
      "name": "Lead follow-up and reply stop",
      "state": "ACTIVE",
      "active_version": null,
      "owner_id": "01K2USER0000000000000000002",
      "last_action": "ACTIVATE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM automation_definitions with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); UNIQUE(code); INDEX(state, owner_id, updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

No Python/shell/SQL/eval/templates/HTTP callback; actor cannot configure action beyond approved scope; record samples permissioned; simulation never writes business/customer events.

### Performance and resource budget

Definition pages ≤1.6s; simulation request ≤1.9s for bounded sample and ≤24 queries; max 30 steps, boolean depth/size bound, max five nested enrolments.

### Testing required

Every trigger/operator/action; invalid field/type; direct/indirect cycle; excessive graph/depth; unauthorized action; rollback event absence; duplicate event; simulation zero side effect.

### What success looks like

A process owner can see exactly why a record would enroll, dates/actions/guards/exits/conflicts, and unsafe definitions cannot activate or execute arbitrary code.

### Required deliverables

Event registry/ledger; workflow compiler/simulator; builder UI/API; dependency report; contract/security tests.


---

## S26 — Build durable workflow runtime, jobs, retries, dead letters and emergency stop

**Phase:** Phase 4 — Automation

**Objective:** Execute delayed automation safely through bounded cPanel Cron without daemons.

**Why this step exists:** Server restarts, overlapping Cron and transient failures must not lose, duplicate or hide work.

**Prerequisites:** S25 compiled plans/events; S18 work queue; S23 outbox.

### What to build in the frontend

Build run/job/dead-letter trace screens, pause/resume/cancel, replay preview, command heartbeat, queue age and emergency-stop banner/control.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Operations | `/automation/runs` | Workflow runs | Monitor enrolled subjects, current step, outcomes, exits and failure state. | 1400 ms | ≤20 | ≤800 KB |
| Operations | `/automation/runs/{id}` | Workflow run trace | Reconstruct trigger, condition decisions, actions, jobs, guards and timeline. | 1500 ms | ≤26 | ≤1000 KB |
| Operations | `/automation/jobs` | Scheduled jobs | Inspect due/retry/claimed/dead jobs and command heartbeat. | 1400 ms | ≤20 | ≤800 KB |
| Operations | `/automation/dead-letters` | Dead letters | Investigate terminal failures, affected customers, owner, aging and replay safety. | 1500 ms | ≤22 | ≤850 KB |
| Admin | `/automation/emergency` | Automation emergency control | Stop new automated external effects and show exact scope/recovery state. | 1200 ms | ≤14 | ≤500 KB |

### How to build the frontend


#### `/automation/runs` — Workflow runs

- **Purpose:** Monitor enrolled subjects, current step, outcomes, exits and failure state.
- **Components:** RunFilters; RunTable; State/ExitBadges
- **API/data:** GET /workflow-runs; pause/resume/cancel
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Pause/resume/cancel
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Automation operations + subject scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/automation/runs/{id}` — Workflow run trace

- **Purpose:** Reconstruct trigger, condition decisions, actions, jobs, guards and timeline.
- **Components:** RunHeader; ExecutionTrace; SubjectLink; JobList; HumanReadableHistory
- **API/data:** GET /workflow-runs; pause/resume/cancel
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Pause/resume/cancel
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Automation operations + subject scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤26 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤26, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/automation/jobs` — Scheduled jobs

- **Purpose:** Inspect due/retry/claimed/dead jobs and command heartbeat.
- **Components:** JobFilters; JobTable; LeaseState; RetryTimeline
- **API/data:** GET /scheduled-jobs; cancel/replay; command runs
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Cancel safe job; open dead letter
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Automation operations
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/automation/dead-letters` — Dead letters

- **Purpose:** Investigate terminal failures, affected customers, owner, aging and replay safety.
- **Components:** DeadLetterTable; ErrorClass; PolicyRecheck; ReplayPreview
- **API/data:** GET /dead-letters; replay/resolve
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Replay/resolve with reason
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Automation operations + step-up for bulk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/automation/emergency` — Automation emergency control

- **Purpose:** Stop new automated external effects and show exact scope/recovery state.
- **Components:** KillSwitchBanner; ScopeSelector; ImpactSummary; ApprovalDialog
- **API/data:** GET/POST/PATCH /automation-definitions and versions; validate, dependencies, simulate, activate, rollback, emergency stop
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Enable/disable kill switch
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Privileged step-up + four-eyes where configured
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1200 ms, ≤14 SQL, ≤500 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1200 ms, SQL count ≤14, compressed transfer ≤500 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement enrollment uniqueness/re-entry policy, workflow run state, durable scheduled jobs, one-command DB lease, atomic job claim, attempt records, idempotent actions, retries/backoff/jitter, dead letters, nested depth/correlation, conflict resolver, global frequency ledger and kill switch.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| automations | `EnrolmentService` | Create one run per declared re-entry key and enforce correlation/depth guards. | workflow_runs, domain_events |
| automations | `WorkflowRuntime` | Advance run through actions/delays/exits and append human-readable trace. | workflow_runs, workflow_run_events, scheduled_jobs |
| automations | `SchedulerService` | Create durable delayed jobs instead of sleeping and compute timezone/business-calendar due time. | scheduled_jobs, business_calendars |
| operations | `CommandLeaseService` | Acquire one command lease, recover stale lease by policy and exit competing invocations. | command_leases, command_runs |
| automations | `JobClaimService` | Atomically claim bounded due jobs on the production MySQL/MariaDB semantics. | scheduled_jobs, job_attempts |
| automations | `RetryService` | Classify transient/permanent/policy/ambiguous failure and apply bounded exponential backoff with jitter. | scheduled_jobs, job_attempts |
| automations | `DeadLetterService` | Create owned severity-classified terminal investigation, current-policy replay and resolution evidence. | dead_letters, scheduled_jobs, job_attempts |
| automations | `ConflictResolver` | Apply deterministic security/recovery/service/relationship/promotional precedence and collapse duplicate objectives. | workflow_runs, outbox_messages, communication_ledger |
| automations | `EmergencyStopService` | Stop new automated external-effect claims within one cron interval and preserve recoverable state. | feature_flags, automation kill-switch configuration, command_runs |

### How to build the backend services


#### `EnrolmentService`

- **Responsibility:** Create one run per declared re-entry key and enforce correlation/depth guards.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** workflow_runs, domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `WorkflowRuntime`

- **Responsibility:** Advance run through actions/delays/exits and append human-readable trace.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** workflow_runs, workflow_run_events, scheduled_jobs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SchedulerService`

- **Responsibility:** Create durable delayed jobs instead of sleeping and compute timezone/business-calendar due time.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** scheduled_jobs, business_calendars
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `CommandLeaseService`

- **Responsibility:** Acquire one command lease, recover stale lease by policy and exit competing invocations.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** command_leases, command_runs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `JobClaimService`

- **Responsibility:** Atomically claim bounded due jobs on the production MySQL/MariaDB semantics.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** scheduled_jobs, job_attempts
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RetryService`

- **Responsibility:** Classify transient/permanent/policy/ambiguous failure and apply bounded exponential backoff with jitter.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** scheduled_jobs, job_attempts
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `DeadLetterService`

- **Responsibility:** Create owned severity-classified terminal investigation, current-policy replay and resolution evidence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** dead_letters, scheduled_jobs, job_attempts
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ConflictResolver`

- **Responsibility:** Apply deterministic security/recovery/service/relationship/promotional precedence and collapse duplicate objectives.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** workflow_runs, outbox_messages, communication_ledger
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `EmergencyStopService`

- **Responsibility:** Stop new automated external-effect claims within one cron interval and preserve recoverable state.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** feature_flags, automation kill-switch configuration, command_runs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create workflow_runs/events, scheduled_jobs, job_attempts, dead_letters, command_leases/runs; indexes on state/due/retry/lease/idempotency/correlation.

### Ordered implementation procedure

1. Enroll from event idempotently.
2. create first job.
3. acquire command lease.
4. claim short batch.
5. re-evaluate exits/policy.
6. execute action.
7. append result/next job.
8. classify/retry/dead-letter.
9. checkpoint/time out.
10. implement pause/cancel/emergency/replay.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `DELETE` | `/automation/emergency-stop` | Clear emergency stop after step-up and approval | staff | 204 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/automation/emergency-stop` | Stop new automated external effects within one cron interval | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/command-runs` | List durable scheduled-command execution records | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/dead-letters` | List dead-letter record records | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/dead-letters/{id}` | Get one dead-letter record | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/dead-letters/{id}/replay` | Replay terminal work after current policy, permission and idempotency checks | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/dead-letters/{id}/resolve` | Resolve dead letter without replay and record repair evidence | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/scheduled-jobs` | List scheduled-jobs | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/scheduled-jobs/{id}` | Get one scheduled job | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/scheduled-jobs/{id}/cancel` | Cancel a pending or retry-wait job | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/scheduled-jobs/{id}/replay` | Replay dead-lettered work after current policy guard | staff | 202 | 1200 ms | ≤12 | If-Match, Idempotency-Key |
| `GET` | `/workflow-runs` | List workflow-runs | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/workflow-runs` | Create a workflow run | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/workflow-runs/{id}` | Get one workflow run | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/workflow-runs/{id}/cancel` | Cancel a workflow run and future jobs according to policy | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/workflow-runs/{id}/pause` | Pause one workflow run | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/workflow-runs/{id}/resume` | Resume one workflow run after re-evaluating exits and policy | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/command-runs?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN`

**Purpose:** List durable scheduled-command execution records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "command-run",
      "id": "01K2COMMANDR00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Command Run"
      }
    }
  ],
  "links": {
    "self": "/api/v1/command-runs?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN",
    "next": "/api/v1/command-runs?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM command_runs WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/dead-letters/{id}/resolve`

**Purpose:** Resolve dead letter without replay and record repair evidence

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "resolve",
    "id": "01K2RESOLVE000000000000000",
    "version": 8,
    "attributes": {
      "state": "RESOLVED",
      "name": "Resolve",
      "last_action": "RESOLVE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM resolves with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Runtime uses system policy but cannot exceed action allowlist/record scope; replay requires current authorization/policy and reason; emergency stop privileged/audited; errors redact customer/secrets.

### Performance and resource budget

≤50 jobs or 40s per command; due-job p95 begins within one Cron interval +2 min; locks short; process memory ≤512MB; command overlaps produce one executor.

### Testing required

Concurrent runners, stale lease, crash after claim/action/commit, event redelivery, retry schedule, permanent/policy error, nested loop guard, reply/opt-out final exit, kill switch latency.

### What success looks like

Restart/duplicate Cron cannot lose or logically duplicate actions; every failure has owner/severity/replay path; emergency stop blocks new external effects within one interval while state remains recoverable.

### Required deliverables

Runtime/job/lease/retry/dead-letter services; Cron commands; operations screens; failure-injection/soak tests; runbooks.


---

## S27 — Configure and verify all 28 production workflows

**Phase:** Phase 4 — Automation

**Objective:** Translate the approved operating model into reviewed draft workflows and activate only after complete evidence.

**Why this step exists:** The engine alone provides no customer outcome; every production workflow needs company policy, templates, stops, ownership and tests.

**Prerequisites:** S19-S26 modules; approved workflow owners/templates/SLAs.

### What to build in the frontend

Build workflow-specific overview/help text and simulation fixtures. No new framework component unless a workflow exposes a missing generic need.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Install WF-01 through WF-28 as versioned drafts; bind triggers, conditions, tasks/messages, owners, delays, exits, caps, conflicts, metrics and rollback/in-flight policy. Implement any missing typed action through the registry, never one-off code inside a workflow.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| automations | `DefaultWorkflowInstaller` | Install WF-01 through WF-28 as reviewed drafts with owner, template, stops, caps and simulation fixtures. | automation_definitions, automation_versions |

### How to build the backend services


#### `DefaultWorkflowInstaller`

- **Responsibility:** Install WF-01 through WF-28 as reviewed drafts with owner, template, stops, caps and simulation fixtures.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** automation_definitions, automation_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Persist 28 definition/version records and test fixtures; no customer run is created merely by deployment.

### Ordered implementation procedure

1. name owner/escalation.
2. bind trigger schema.
3. define eligibility.
4. bind templates/purpose.
5. define actions/delays.
6. define reply/opt-out/complaint/completion/stage/manual exits.
7. simulate positive/negative/duplicate/conflict cases.
8. test retry/dead-letter/auth.
9. approve.
10. activate progressively.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

High-impact workflows require four-eyes; imported/quarantined/test records excluded; no mass mail; security/recovery/service precedence; no auto-merge/churn/high-impact AI action.

### Performance and resource budget

Each workflow respects engine batch/mail caps; simulation stays bounded; metrics aggregate incrementally. Activation volume is staged.

### Testing required

Five mandatory categories per workflow: positive, stop/exit, duplicate event, retry/dead letter, permission. Add race tests for message/reply and one-time handoffs.

### What success looks like

All 28 workflow packs have named owner, exact simulation output, approved templates/policy, rollback and test evidence. Activation is controlled and no workflow can contact an ineligible customer.

### Required deliverables

Workflow configuration bundle; simulation snapshots; test pack; approval register; activation/rollback plan; staff guidance.


---

## S28 — Build onboarding templates, cases, milestones, requests and blockers

**Phase:** Phase 5 — Full lifecycle

**Objective:** Turn each won promise into an accountable delivery plan and measurable time-to-value.

**Why this step exists:** A won deal is not value until handoff, customer inputs, milestones and blockers are managed and closed.

**Prerequisites:** S21 won handoff; S18 tasks; S23 messaging; S26 automation; S32 portal scaffold as needed.

### What to build in the frontend

Build onboarding queue/detail/template editor, dependency-aware checklist, weighted progress, customer request cards, secure uploads, blocker panel, completion/cancel dialogs and customer-visible wording preview.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/onboarding` | Onboarding queue | Prioritize active cases by phase, due next action, blockers and progress. | 1400 ms | ≤20 | ≤800 KB |
| Staff | `/onboarding/{id}` | Onboarding workspace | Deliver won promises using instantiated milestones, requests, blockers and customer communication. | 1600 ms | ≤30 | ≤1000 KB |
| Admin | `/onboarding/templates` | Onboarding templates | Govern product-to-template mapping, milestones, owners, inputs, SLA and completion rules. | 1400 ms | ≤20 | ≤800 KB |
| Admin | `/onboarding/templates/{id}` | Onboarding template editor | Edit acyclic dependency graph and instantiate a test snapshot. | 1700 ms | ≤28 | ≤1050 KB |

### How to build the frontend


#### `/onboarding` — Onboarding queue

- **Purpose:** Prioritize active cases by phase, due next action, blockers and progress.
- **Components:** CaseFilters; CaseTable; ProgressBar; BlockerBadges
- **API/data:** GET/POST/PATCH /onboarding-cases; milestones, blockers, customer requests, completion/cancel
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open/assign/pause
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Onboarding scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/onboarding/{id}` — Onboarding workspace

- **Purpose:** Deliver won promises using instantiated milestones, requests, blockers and customer communication.
- **Components:** CaseHeader; MilestoneChecklist; DependencyView; CustomerRequests; Blockers; Timeline
- **API/data:** GET/POST/PATCH /onboarding-cases; milestones, blockers, customer requests, completion/cancel
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Complete/waive milestone; request input; resolve blocker; complete/cancel case
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Case scope + field visibility
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤30 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤30, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/onboarding/templates` — Onboarding templates

- **Purpose:** Govern product-to-template mapping, milestones, owners, inputs, SLA and completion rules.
- **Components:** TemplateTable; ProductMapping; VersionBadges
- **API/data:** GET/POST/PATCH /onboarding-templates and versions
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/open/retire
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** onboarding_admin
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/onboarding/templates/{id}` — Onboarding template editor

- **Purpose:** Edit acyclic dependency graph and instantiate a test snapshot.
- **Components:** MilestoneEditor; DependencyGraph; RoleMapping; InputSchema; Simulation
- **API/data:** GET/POST/PATCH /onboarding-templates and versions
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create version; validate/activate
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** onboarding_admin + reviewer
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1700 ms, ≤28 SQL, ≤1050 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1700 ms, SQL count ≤28, compressed transfer ≤1050 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement template/version snapshot, one-case-per-handoff, role-based assignment, handoff completeness, milestone/dependency/waiver, customer request tokens/portal, reminders/exits, blocker escalation/health effect, progress calculation and completion feedback/success handoff.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| onboarding | `OnboardingTemplateService` | Manage versioned milestone, dependency, role, input, SLA and completion blueprints. | onboarding_templates, onboarding_template_versions |
| onboarding | `OnboardingCaseService` | Instantiate exactly one case from won handoff snapshot and maintain owner/phase/action invariant. | onboarding_cases, onboarding_milestones, onboarding_dependencies |
| onboarding | `MilestoneService` | Validate dependency order, complete/waive with evidence and recompute weighted progress. | onboarding_milestones, onboarding_dependencies |
| onboarding | `CustomerRequestService` | Create signed/portal requests, validate submissions/files, reminders, expiry and acceptance. | customer_requests, file_assets, scheduled_jobs |
| onboarding | `BlockerService` | Create/resolve blocker with impact, owner, escalation and health/communication effects. | onboarding_blockers, tasks, health_reasons |
| onboarding | `OnboardingCompletionService` | Validate mandatory outcomes, create success baseline and one eligible feedback request. | onboarding_cases, health_snapshots, feedback_requests |

### How to build the backend services


#### `OnboardingTemplateService`

- **Responsibility:** Manage versioned milestone, dependency, role, input, SLA and completion blueprints.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** onboarding_templates, onboarding_template_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OnboardingCaseService`

- **Responsibility:** Instantiate exactly one case from won handoff snapshot and maintain owner/phase/action invariant.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** onboarding_cases, onboarding_milestones, onboarding_dependencies
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `MilestoneService`

- **Responsibility:** Validate dependency order, complete/waive with evidence and recompute weighted progress.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** onboarding_milestones, onboarding_dependencies
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `CustomerRequestService`

- **Responsibility:** Create signed/portal requests, validate submissions/files, reminders, expiry and acceptance.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** customer_requests, file_assets, scheduled_jobs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `BlockerService`

- **Responsibility:** Create/resolve blocker with impact, owner, escalation and health/communication effects.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** onboarding_blockers, tasks, health_reasons
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OnboardingCompletionService`

- **Responsibility:** Validate mandatory outcomes, create success baseline and one eligible feedback request.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** onboarding_cases, health_snapshots, feedback_requests
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create onboarding_templates/versions, cases, milestones, dependencies, customer_requests and blockers with case/state/owner/due indexes and handoff uniqueness.

### Ordered implementation procedure

1. Map products to templates.
2. instantiate snapshot at won.
3. validate handoff.
4. assign owner/tasks.
5. start approved welcome.
6. request inputs.
7. manage dependencies/blockers.
8. compute progress.
9. complete mandatory outcomes.
10. schedule one feedback/success review.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `POST` | `/customer-requests/{id}/complete` | Accept customer submission and complete request | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/customer-requests/{id}/resend` | Resend customer input request after current eligibility check | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/onboarding-blockers/{id}/resolve` | Resolve blocker with outcome and follow-up plan | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/onboarding-cases` | List onboarding-cases | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/onboarding-cases` | Create a onboarding case | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/onboarding-cases/{id}` | Soft-delete or cancel one onboarding case | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/onboarding-cases/{id}` | Get one onboarding case | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/onboarding-cases/{id}` | Patch one onboarding case | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/onboarding-cases/{id}/blockers` | Create a blocker with impact, owner and escalation date | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/onboarding-cases/{id}/cancel` | Cancel case with commercial impact and follow-up decision | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/onboarding-cases/{id}/complete` | Complete case after mandatory outcomes and success handoff | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/onboarding-cases/{id}/customer-requests` | Create portal/signed-link customer input request | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/onboarding-cases/{id}/milestones` | List instantiated onboarding milestones and dependencies | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/onboarding-cases/{id}/transition` | Apply onboarding case transition with milestone evidence | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/onboarding-milestones/{id}/complete` | Complete milestone with required evidence | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/onboarding-milestones/{id}/waive` | Waive milestone under configured approval policy | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/onboarding-template-versions` | List onboarding template version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/onboarding-template-versions` | Create one onboarding template version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/onboarding-template-versions/{id}` | Retire or soft-delete one onboarding template version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/onboarding-template-versions/{id}` | Get one onboarding template version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/onboarding-template-versions/{id}` | Update one onboarding template version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/onboarding-templates` | List onboarding template records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/onboarding-templates` | Create one onboarding template | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/onboarding-templates/{id}` | Retire or soft-delete one onboarding template | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/onboarding-templates/{id}` | Get one onboarding template | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/onboarding-templates/{id}` | Update one onboarding template | staff | 200 | 1800 ms | ≤22 | If-Match |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/onboarding-cases?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List onboarding-cases

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "onboarding-case",
      "id": "01K2ONBOARDI00000000000000",
      "version": 7,
      "attributes": {
        "state": "IN_PROGRESS",
        "phase": "TECHNICAL_SETUP",
        "progress_percent": 35,
        "owner_id": "01K2USER0000000000000000003",
        "target_completion_date": "2026-08-15",
        "next_action_at": "2026-07-15T08:00:00Z"
      }
    }
  ],
  "links": {
    "self": "/api/v1/onboarding-cases?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/onboarding-cases?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM onboarding_cases WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); UNIQUE(source_won_handoff_id); INDEX(state, owner_id, next_action_at, public_id); INDEX(target_completion_date, state, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/customer-requests/{id}/complete`

**Purpose:** Accept customer submission and complete request

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "complete",
    "id": "01K2COMPLETE00000000000000",
    "version": 8,
    "attributes": {
      "state": "COMPLETED",
      "name": "Complete",
      "last_action": "COMPLETE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM completes with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Portal/signed request scope; file controls; customer-visible vs internal separation; waiver approval; reminders stop on reply/submission/hold/completion; incomplete handoff can return to sales.

### Performance and resource budget

Queue/detail ≤1.6s; progress deterministic; reminders within one interval; one case per handoff enforced; milestone updates ≤1.8s.

### Testing required

Template edit does not alter active case, dependency cycle, duplicate won event, token tamper, upload scope, reminder race, blocker escalation, waiver permission, completion missing item/cancel outcome.

### What success looks like

Every won opportunity produces exactly one complete owned case; the customer knows what is needed; progress reconciles to milestones; blockers age visibly; completion establishes success baseline and feedback.

### Required deliverables

Onboarding frontend/backend/API/templates; portal request integration; workflows WF-12–15; reports and UAT-05/06 evidence.


---

## S29 — Build support desk, SLA clocks, incidents and knowledge

**Phase:** Phase 5 — Full lifecycle

**Objective:** Provide reliable multi-source support with meaningful response metrics, safe conversations and recoverable poor outcomes.

**Why this step exists:** Auto-acknowledgements must not hide slow human response; waiting, reopen and internal notes require exact semantics.

**Prerequisites:** S24 email ingestion; S18 queues; S12 SLA; S26 workflows; S11 files.

### What to build in the frontend

Build ticket queue/detail, SLA clocks, triage forms, customer/internal conversation composer, assignment/claim, root-cause/resolution, reopen/merge, incident command center, knowledge library/editor and SLA administration.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Support | `/support/tickets` | Support ticket queue | Prioritize tickets by first-response/resolution risk, priority, state and customer context. | 1400 ms | ≤22 | ≤850 KB |
| Support | `/support/tickets/{id}` | Ticket workspace | Manage triage, SLA clocks, customer-visible conversation, internal notes, diagnosis, root cause and resolution. | 1600 ms | ≤32 | ≤1100 KB |
| Manager | `/support/queues` | Support queue health | Show backlog, aging, SLA warning/breach and assignment capacity. | 1600 ms | ≤24 | ≤950 KB |
| Support | `/support/incidents` | Customer service incidents | Track broad-impact incidents, affected customers, update cadence and resolution. | 1500 ms | ≤22 | ≤900 KB |
| Support | `/support/incidents/{id}` | Incident command center | Coordinate impact, internal/customer updates, missed cadence and post-incident evidence. | 1600 ms | ≤28 | ≤1050 KB |
| Support | `/support/knowledge` | Knowledge library | Search approved internal/portal articles with version and usage evidence. | 1400 ms | ≤20 | ≤750 KB |
| Support | `/support/knowledge/{id}` | Knowledge article editor | Draft, review and publish immutable internal/portal article version. | 1500 ms | ≤22 | ≤850 KB |
| Admin | `/support/sla` | SLA policy administration | Configure business-calendar response/update/resolution targets and pause rules. | 1500 ms | ≤22 | ≤850 KB |

### How to build the frontend


#### `/support/tickets` — Support ticket queue

- **Purpose:** Prioritize tickets by first-response/resolution risk, priority, state and customer context.
- **Components:** TicketFilters; SLAColumns; PriorityBadges; QueueClaim
- **API/data:** GET/POST/PATCH /tickets; messages, transition, resolve, reopen, merge
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/claim/assign/open
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Support team/queue scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤22 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤22, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/support/tickets/{id}` — Ticket workspace

- **Purpose:** Manage triage, SLA clocks, customer-visible conversation, internal notes, diagnosis, root cause and resolution.
- **Components:** TicketHeader; SLAClock; Conversation; InternalNotes; DiagnosisForm; KnowledgeSuggestions; Timeline
- **API/data:** GET/POST/PATCH /tickets; messages, transition, resolve, reopen, merge
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Triage, transition, message, resolve, reopen, merge
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Ticket scope + visibility partition
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤32 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤32, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/support/queues` — Support queue health

- **Purpose:** Show backlog, aging, SLA warning/breach and assignment capacity.
- **Components:** QueueCards; AgingChart; ExceptionTable; AssignmentActions
- **API/data:** GET/POST/PATCH /tickets; messages, transition, resolve, reopen, merge
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Assign/escalate
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Support manager scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/support/incidents` — Customer service incidents

- **Purpose:** Track broad-impact incidents, affected customers, update cadence and resolution.
- **Components:** IncidentTable; ImpactSummary; UpdateCadence; AffectedCustomers
- **API/data:** GET/POST/PATCH /support-incidents; incident updates
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/update/resolve incident
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Incident capability + customer scopes
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤900 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤900 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/support/incidents/{id}` — Incident command center

- **Purpose:** Coordinate impact, internal/customer updates, missed cadence and post-incident evidence.
- **Components:** IncidentHeader; Timeline; UpdateComposer; CustomerList; Actions
- **API/data:** GET/POST/PATCH /support-incidents; incident updates
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Add update; change state; resolve
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Incident capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤28 SQL, ≤1050 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤28, compressed transfer ≤1050 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/support/knowledge` — Knowledge library

- **Purpose:** Search approved internal/portal articles with version and usage evidence.
- **Components:** KnowledgeSearch; ArticleTable; VisibilityBadges
- **API/data:** GET/POST/PATCH /knowledge-articles and versions; publish
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/open/retire
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Knowledge scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤750 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤750 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/support/knowledge/{id}` — Knowledge article editor

- **Purpose:** Draft, review and publish immutable internal/portal article version.
- **Components:** ArticleEditor; Visibility; VersionDiff; Approval
- **API/data:** GET/POST/PATCH /knowledge-articles and versions; publish
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create version; publish
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** knowledge_admin + reviewer
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/support/sla` — SLA policy administration

- **Purpose:** Configure business-calendar response/update/resolution targets and pause rules.
- **Components:** PolicyTable; CalendarPreview; PriorityMatrix; BoundaryTestPanel
- **API/data:** GET/POST/PATCH /sla-policies and versions; activate
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create version; validate/activate
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** sla_admin + reviewer
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement common intake/dedupe, human-readable reference + opaque ID, triage/priority matrix, business-calendar SLA intervals, meaningful first response, waiting dependencies/wake-up, conversation visibility, assignment, ticket links/merge, incident cadence, diagnosis/root cause, knowledge versions, resolution/reopen and CSAT trigger.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| support | `TicketIntakeService` | Accept mailbox/form/portal/staff intake through one deduped source-evidenced path. | tickets, ticket_events, email_messages, domain_events |
| support | `TriageService` | Capture/suggest category, impact, urgency, priority, service, owner and SLA with human confirmation. | tickets, ticket_categories, sla_policies |
| support | `PriorityService` | Calculate versioned impact/urgency matrix and controlled override reason. | tickets, configuration_versions |
| support | `SlaClockService` | Open/pause/resume first-response/update/resolution intervals and calculate business/customer/internal/total time. | sla_clock_intervals, sla_policies, business_calendars |
| support | `TicketTransitionService` | Apply support state machine, waiting dependency/wake-up, terminal evidence and reopen interval. | tickets, ticket_events, sla_clock_intervals |
| support | `TicketConversationService` | Add customer-visible/portal/internal events with persistent visibility and safe attachments. | ticket_events, email_messages, file_assets |
| support | `SupportAssignmentService` | Route queues/skills/services, atomic claim, absence exclusion and escalation. | tickets, work_queues, queue_memberships, delegations |
| support | `SupportIncidentService` | Track broad impact, affected customers, update cadence, owner, resolution and post-incident evidence. | support_incidents, incident updates, tickets |
| support | `KnowledgeService` | Manage approved immutable internal/portal articles and link usage to tickets. | knowledge_articles, knowledge_article_versions, ticket_knowledge_usage |
| support | `TicketResolutionService` | Require customer summary, diagnosis/root cause/category, resolve interval and schedule eligible CSAT. | tickets, ticket_events, feedback_requests |

### How to build the backend services


#### `TicketIntakeService`

- **Responsibility:** Accept mailbox/form/portal/staff intake through one deduped source-evidenced path.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tickets, ticket_events, email_messages, domain_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `TriageService`

- **Responsibility:** Capture/suggest category, impact, urgency, priority, service, owner and SLA with human confirmation.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tickets, ticket_categories, sla_policies
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `PriorityService`

- **Responsibility:** Calculate versioned impact/urgency matrix and controlled override reason.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tickets, configuration_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SlaClockService`

- **Responsibility:** Open/pause/resume first-response/update/resolution intervals and calculate business/customer/internal/total time.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** sla_clock_intervals, sla_policies, business_calendars
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `TicketTransitionService`

- **Responsibility:** Apply support state machine, waiting dependency/wake-up, terminal evidence and reopen interval.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tickets, ticket_events, sla_clock_intervals
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `TicketConversationService`

- **Responsibility:** Add customer-visible/portal/internal events with persistent visibility and safe attachments.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** ticket_events, email_messages, file_assets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SupportAssignmentService`

- **Responsibility:** Route queues/skills/services, atomic claim, absence exclusion and escalation.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tickets, work_queues, queue_memberships, delegations
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SupportIncidentService`

- **Responsibility:** Track broad impact, affected customers, update cadence, owner, resolution and post-incident evidence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** support_incidents, incident updates, tickets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `KnowledgeService`

- **Responsibility:** Manage approved immutable internal/portal articles and link usage to tickets.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** knowledge_articles, knowledge_article_versions, ticket_knowledge_usage
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `TicketResolutionService`

- **Responsibility:** Require customer summary, diagnosis/root cause/category, resolve interval and schedule eligible CSAT.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tickets, ticket_events, feedback_requests
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create ticket_categories, tickets/events, sla_clock_intervals, ticket_links, support incidents, knowledge_articles/versions/usage; indexes on state/owner/priority/next SLA/customer/reference.

### Ordered implementation procedure

1. Define categories/priority/SLA.
2. implement all intake adapters.
3. assign/triage.
4. start clocks.
5. manage visible conversation.
6. transition waiting/in-progress.
7. warn/breach immutably.
8. resolve with evidence.
9. reopen on unresolved reply.
10. schedule one CSAT interval.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/knowledge-article-versions` | List knowledge article version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/knowledge-article-versions` | Create one knowledge article version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/knowledge-article-versions/{id}` | Retire or soft-delete one knowledge article version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/knowledge-article-versions/{id}` | Get one knowledge article version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/knowledge-article-versions/{id}` | Update one knowledge article version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/knowledge-article-versions/{id}/publish` | Publish an approved internal or portal article version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/knowledge-articles` | List knowledge-articles | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/knowledge-articles` | Create a knowledge article | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/knowledge-articles/{id}` | Soft-delete or cancel one knowledge article | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/knowledge-articles/{id}` | Get one knowledge article | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/knowledge-articles/{id}` | Patch one knowledge article | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/sla-policy-versions` | List SLA policy version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/sla-policy-versions` | Create one SLA policy version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/sla-policy-versions/{id}` | Retire or soft-delete one SLA policy version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/sla-policy-versions/{id}` | Get one SLA policy version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/sla-policy-versions/{id}` | Update one SLA policy version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/sla-policy-versions/{id}/activate` | Activate an approved SLA policy version | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/support-incidents` | List support incident records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/support-incidents` | Create one support incident | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/support-incidents/{id}` | Retire or soft-delete one support incident | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/support-incidents/{id}` | Get one support incident | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/support-incidents/{id}` | Update one support incident | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/support-incidents/{id}/updates` | Add a customer/internal incident update and enforce cadence | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/tickets` | List tickets | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/tickets` | Create a ticket | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/tickets/{id}` | Soft-delete or cancel one ticket | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/tickets/{id}` | Get one ticket | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/tickets/{id}` | Patch one ticket | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/tickets/{id}/merge` | Merge a duplicate ticket while preserving conversation provenance | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/tickets/{id}/messages` | Add customer-visible or internal ticket event | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/tickets/{id}/reopen` | Reopen a resolved/closed ticket and create a new SLA interval | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/tickets/{id}/resolve` | Resolve ticket with required root-cause and customer summary | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/tickets/{id}/transition` | Apply ticket transition and SLA clock rules | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/knowledge-article-versions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN`

**Purpose:** List knowledge article version records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "knowledge-article-version",
      "id": "01K2KNOWLEDG00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Knowledge Article Version"
      }
    }
  ],
  "links": {
    "self": "/api/v1/knowledge-article-versions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN",
    "next": "/api/v1/knowledge-article-versions?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM knowledge_article_versions WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/sla-policy-versions/{id}/activate`

**Purpose:** Activate an approved SLA policy version

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "activate",
    "id": "01K2ACTIVATE00000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Activate",
      "last_action": "ACTIVATE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM activates with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Portal never sees internal notes/metadata; email untrusted; ticket reference not authorization; SLA corrections append events; critical incident updates restricted; file controls.

### Performance and resource budget

Ticket list/detail ≤1.6s/32 queries; clock calculation bounded/indexed; urgent intake/reply within one poll interval; dashboards ≤2s.

### Testing required

Mailbox/form/portal dedupe, priority matrix, holiday/DST, auto-ack exclusion, wait pause rules, atomic claim, internal note leakage, merge provenance, missed incident cadence, resolve/reopen/CSAT uniqueness.

### What success looks like

Every ticket has visible owner/priority/SLA/next action; meaningful first response is honest; waiting clocks reconcile; portal sees only customer content; low CSAT flows to recovery.

### Required deliverables

Support frontend/backend/API; SLA engine; incidents/knowledge; workflows WF-16–19; reports and UAT-07 evidence.


---

## S30 — Build surveys, feedback validation and low-score recovery

**Phase:** Phase 5 — Full lifecycle

**Objective:** Make customer feedback operational input that immediately changes follow-up and customer treatment.

**Why this step exists:** A feedback dashboard without owned recovery repeats dissatisfaction and can trigger inappropriate promotion.

**Prerequisites:** S23 messaging; S26 workflow; S29 support; S15 holds.

### What to build in the frontend

Build survey/version editor, request/status list, signed and portal survey pages, response detail/theme evidence, recovery queue/detail, hold visibility and accessible mobile forms.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/feedback/surveys` | Survey definitions | Govern purpose, questions, scale, eligibility, fatigue, anonymity and recovery thresholds. | 1400 ms | ≤20 | ≤800 KB |
| Staff | `/feedback/surveys/{id}` | Survey editor | Edit versioned questions and preview accessible signed/portal experience. | 1600 ms | ≤26 | ≤1000 KB |
| Staff | `/feedback/requests` | Feedback requests | Monitor eligible, queued, delivered, expired, bounced and responded survey requests. | 1400 ms | ≤20 | ≤800 KB |
| Staff | `/feedback/responses` | Feedback responses | Review valid responses, score distribution, comments, themes and recovery requirement. | 1500 ms | ≤22 | ≤850 KB |
| Staff | `/feedback/responses/{id}` | Feedback response detail | Inspect exact survey version, answer evidence and recovery linkage. | 1400 ms | ≤24 | ≤850 KB |
| Manager | `/feedback/recovery` | Recovery queue | Guarantee every low score or severe complaint has owner, due action and communication hold. | 1400 ms | ≤20 | ≤800 KB |
| Staff | `/feedback/recovery/{id}` | Recovery workspace | Record contact attempts, root cause, action, outcome and hold release. | 1500 ms | ≤24 | ≤900 KB |

### How to build the frontend


#### `/feedback/surveys` — Survey definitions

- **Purpose:** Govern purpose, questions, scale, eligibility, fatigue, anonymity and recovery thresholds.
- **Components:** SurveyTable; PurposeBadges; VersionStatus
- **API/data:** GET/POST/PATCH /survey-definitions and versions; activate
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/open/retire
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** feedback_admin
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/feedback/surveys/{id}` — Survey editor

- **Purpose:** Edit versioned questions and preview accessible signed/portal experience.
- **Components:** QuestionEditor; ScaleEditor; EligibilityRules; FatigueConfig; Preview
- **API/data:** GET/POST/PATCH /survey-definitions and versions; activate
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create version; validate/activate
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** feedback_admin + reviewer
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤26 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤26, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/feedback/requests` — Feedback requests

- **Purpose:** Monitor eligible, queued, delivered, expired, bounced and responded survey requests.
- **Components:** RequestFilters; DeliveryState; FatigueReason
- **API/data:** GET /feedback-requests; create, cancel, resend
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/cancel/resend
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Feedback scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/feedback/responses` — Feedback responses

- **Purpose:** Review valid responses, score distribution, comments, themes and recovery requirement.
- **Components:** ResponseFilters; ScoreBadges; ThemeEvidence; PrivacySuppression
- **API/data:** GET /feedback-responses; amend, validate
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open/validate/amend
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Feedback scope + anonymous constraints
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/feedback/responses/{id}` — Feedback response detail

- **Purpose:** Inspect exact survey version, answer evidence and recovery linkage.
- **Components:** ResponseHeader; QuestionAnswers; ThemeReasons; RecoveryPanel
- **API/data:** GET /feedback-responses; amend, validate
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Validate/exclude/amend; create recovery
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Feedback scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤24 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤24, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/feedback/recovery` — Recovery queue

- **Purpose:** Guarantee every low score or severe complaint has owner, due action and communication hold.
- **Components:** RecoveryTable; Severity; HoldState; Aging
- **API/data:** GET/POST/PATCH /recovery-cases; close
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Assign/open/close recovery
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Recovery scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/feedback/recovery/{id}` — Recovery workspace

- **Purpose:** Record contact attempts, root cause, action, outcome and hold release.
- **Components:** RecoveryHeader; Evidence; ActionLog; OutcomeForm; HoldPanel
- **API/data:** GET/POST/PATCH /recovery-cases; close
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Add event; close with outcome
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Recovery scope + sensitive fields
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤900 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤900 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement survey purpose/version/scale, eligibility/fatigue at schedule/send, signed token, one-click rating + comment/amendment, anonymous mode, validation/exclusion, local theme/severe phrase classification, recovery case/hold, root cause/action/outcome and privacy-aware reporting.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| feedback | `SurveyService` | Manage versioned purpose/question/scale/eligibility/fatigue/anonymity/recovery rules. | survey_definitions, survey_versions |
| feedback | `FeedbackEligibilityService` | Evaluate contact preference, fatigue, trigger, delay, expiry and duplicate interval at schedule and send time. | feedback_requests, consent_preferences, communication_ledger |
| feedback | `SignedSurveyService` | Issue purpose-bound expiring token hashes and prevent enumeration/cross-purpose replay. | feedback_requests |
| feedback | `FeedbackResponseService` | Capture exact version/answers, amendment history, anonymous policy and validation state. | feedback_responses, feedback_answers |
| feedback | `FeedbackClassifier` | Run local keyword/Naive Bayes categories with confidence, reasons and human-review abstention. | feedback_responses, predictions, prediction_reasons |
| feedback | `RecoveryService` | Open one accountable case for low score/severe complaint, apply communication hold and require outcome evidence. | recovery_cases, recovery_events, suppression_entries, tasks |

### How to build the backend services


#### `SurveyService`

- **Responsibility:** Manage versioned purpose/question/scale/eligibility/fatigue/anonymity/recovery rules.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** survey_definitions, survey_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `FeedbackEligibilityService`

- **Responsibility:** Evaluate contact preference, fatigue, trigger, delay, expiry and duplicate interval at schedule and send time.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** feedback_requests, consent_preferences, communication_ledger
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SignedSurveyService`

- **Responsibility:** Issue purpose-bound expiring token hashes and prevent enumeration/cross-purpose replay.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** feedback_requests
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `FeedbackResponseService`

- **Responsibility:** Capture exact version/answers, amendment history, anonymous policy and validation state.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** feedback_responses, feedback_answers
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `FeedbackClassifier`

- **Responsibility:** Run local keyword/Naive Bayes categories with confidence, reasons and human-review abstention.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** feedback_responses, predictions, prediction_reasons
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RecoveryService`

- **Responsibility:** Open one accountable case for low score/severe complaint, apply communication hold and require outcome evidence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** recovery_cases, recovery_events, suppression_entries, tasks
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create survey_definitions/versions, feedback_requests/responses/answers, recovery_cases/events; indexes on purpose/state/contact/sent/responded/recovery.

### Ordered implementation procedure

1. Configure survey purposes.
2. implement accessible forms.
3. calculate eligibility/fatigue.
4. issue token.
5. capture exact version.
6. validate.
7. classify locally.
8. open one recovery for low/severe.
9. hold promotional/advocacy.
10. close only with outcome.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/feedback-requests` | List feedback request records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/feedback-requests` | Create an eligibility-checked survey request | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/feedback-requests/{id}` | Retire or soft-delete one feedback request | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/feedback-requests/{id}` | Get one feedback request | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/feedback-requests/{id}/cancel` | Cancel an unsent or open feedback request | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/feedback-requests/{id}/resend` | Resend after fatigue, preference and expiry checks | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/feedback-responses` | List feedback-responses | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/feedback-responses` | Create a feedback response | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/feedback-responses/{id}` | Get one feedback response | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/feedback-responses/{id}/amend` | Append an allowed response correction without deleting original | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/feedback-responses/{id}/validate` | Validate or exclude spam/test/duplicate feedback for health/model use | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/recovery-cases` | List recovery-cases | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/recovery-cases` | Create a recovery case | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/recovery-cases/{id}` | Soft-delete or cancel one recovery case | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/recovery-cases/{id}` | Get one recovery case | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/recovery-cases/{id}` | Patch one recovery case | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/recovery-cases/{id}/close` | Close recovery with root cause, action, and outcome evidence | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/survey-definitions` | List survey-definitions | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/survey-definitions` | Create a survey definition | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/survey-definitions/{id}` | Soft-delete or cancel one survey definition | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/survey-definitions/{id}` | Get one survey definition | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/survey-definitions/{id}` | Patch one survey definition | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/survey-versions` | List survey version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/survey-versions` | Create one survey version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/survey-versions/{id}` | Retire or soft-delete one survey version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/survey-versions/{id}` | Get one survey version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/survey-versions/{id}` | Update one survey version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/survey-versions/{id}/activate` | Activate a reviewed survey version | staff | 200 | 1800 ms | ≤22 | Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/feedback-requests?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List feedback request records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "feedback-request",
      "id": "01K2FEEDBACK00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Feedback Request"
      }
    }
  ],
  "links": {
    "self": "/api/v1/feedback-requests?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/feedback-requests?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM feedback_requests WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/feedback-requests/{id}/resend`

**Purpose:** Resend after fatigue, preference and expiry checks

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "resend",
    "attributes": {
      "state": "ACTIVE",
      "name": "Resend"
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "resend",
    "id": "01K2RESEND0000000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Resend",
      "last_action": "RESEND",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM resends with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Anonymous mode never re-identifies; token purpose-bound; raw text stays local; tiny cohorts suppressed; low-confidence classification human-reviewed; delivery failure not negative score.

### Performance and resource budget

Signed page ≤1.6s; low score creates recovery within one Cron interval; reporting ≤2s; classifier bounded and nonblocking.

### Testing required

Token tamper/expiry/replay, fatigue conflicts, amend history, anonymous linkage absence, severe phrase/low confidence, duplicate/test/spam exclusion, low-score hold race, recovery closure evidence.

### What success looks like

Every valid low score/severe complaint gets one owner/due action and immediate promotion hold; survey history preserves exact version; invalid/non-delivery data never pollutes health/models.

### Required deliverables

Feedback/recovery frontend/backend/API; survey defaults; workflows WF-19/20; classifier fixtures; reports and UAT-08 evidence.


---

## S31 — Build customer success, health, renewal, churn and advocacy

**Phase:** Phase 5 — Full lifecycle

**Objective:** Create proactive, explainable retention operations across service, feedback, onboarding and commercial evidence.

**Why this step exists:** Small companies need to see risk and renewal obligations before churn, without aggressive model-driven upsell.

**Prerequisites:** S28-S30 outcomes; S20 commercial values; S18 work queue; S35 AI may initially use rules.

### What to build in the frontend

Build portfolio, health history/reasons, success plans/actions, renewal list/detail, churn/win-back and advocacy suggestion screens. Always show computed vs override and evidence links.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Success | `/success` | Customer success portfolio | Prioritize actionable risk, renewal, missed review and opportunity across assigned customers. | 1600 ms | ≤26 | ≤950 KB |
| Success | `/success/health` | Health overview | Show current computed/override bands, reason dimensions and change over time. | 1600 ms | ≤24 | ≤900 KB |
| Success | `/success/plans` | Success plans | Manage active outcome and risk-recovery plans. | 1400 ms | ≤20 | ≤800 KB |
| Success | `/success/plans/{id}` | Success plan workspace | Track desired outcomes, actions, blockers, evidence, review cadence and result. | 1500 ms | ≤26 | ≤950 KB |
| Success | `/success/renewals` | Renewal portfolio | Prepare renewal cycles with health, issues, value, notice window and decisions. | 1500 ms | ≤22 | ≤900 KB |
| Success | `/success/renewals/{id}` | Renewal workspace | Compile open issues, onboarding gaps, health, commercial change and decision evidence. | 1500 ms | ≤26 | ≤950 KB |
| Success | `/success/churn` | Churn and win-back | Review churn reasons, cooling periods, obligations and eligible win-back. | 1500 ms | ≤22 | ≤850 KB |
| Success | `/success/advocacy` | Advocacy suggestions | Review evidence-backed referral/review suggestions; never auto-send. | 1300 ms | ≤18 | ≤700 KB |

### How to build the frontend


#### `/success` — Customer success portfolio

- **Purpose:** Prioritize actionable risk, renewal, missed review and opportunity across assigned customers.
- **Components:** PortfolioFilters; HealthChange; RenewalWindow; RiskReasons; DueActions
- **API/data:** GET /customer-success-profiles; portfolio reports and work queue
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open customer/plan/renewal
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Success portfolio scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤26 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤26, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/success/health` — Health overview

- **Purpose:** Show current computed/override bands, reason dimensions and change over time.
- **Components:** HealthDistribution; ChangeTable; ReasonFilters
- **API/data:** GET /organizations/{id}/health; health snapshots; refresh/override
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Refresh/override from customer context
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Success scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤24 SQL, ≤900 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤24, compressed transfer ≤900 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/success/plans` — Success plans

- **Purpose:** Manage active outcome and risk-recovery plans.
- **Components:** PlanTable; ReviewDate; OutcomeState
- **API/data:** GET/POST/PATCH /success-plans and actions; close
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/open/close
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Success scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/success/plans/{id}` — Success plan workspace

- **Purpose:** Track desired outcomes, actions, blockers, evidence, review cadence and result.
- **Components:** PlanHeader; OutcomeMilestones; Actions; Evidence; ReviewHistory
- **API/data:** GET/POST/PATCH /success-plans and actions; close
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Update plan/actions; close
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Plan/customer scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤26 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤26, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/success/renewals` — Renewal portfolio

- **Purpose:** Prepare renewal cycles with health, issues, value, notice window and decisions.
- **Components:** RenewalTable; MilestoneBadges; RiskBranch; ValueSummary
- **API/data:** GET/POST/PATCH /renewals; decision
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/update/decision
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Renewal + financial scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤900 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤900 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/success/renewals/{id}` — Renewal workspace

- **Purpose:** Compile open issues, onboarding gaps, health, commercial change and decision evidence.
- **Components:** RenewalHeader; EvidenceChecklist; Timeline; DecisionForm
- **API/data:** GET/POST/PATCH /renewals; decision
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Update/record decision
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Renewal + customer scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤26 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤26, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/success/churn` — Churn and win-back

- **Purpose:** Review churn reasons, cooling periods, obligations and eligible win-back.
- **Components:** ChurnTable; ReasonDistribution; EligibilityBadges
- **API/data:** GET /churn-events; POST churn/correct; win-back policy
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Record/correct churn; create controlled win-back task
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Restricted success capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/success/advocacy` — Advocacy suggestions

- **Purpose:** Review evidence-backed referral/review suggestions; never auto-send.
- **Components:** SuggestionTable; EvidenceReasons; FatigueState
- **API/data:** GET /advocacy-suggestions; decision
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Approve/reject/defer
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Success scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1300 ms, ≤18 SQL, ≤700 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1300 ms, SQL count ≤18, compressed transfer ≤700 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement success profile/owner/review invariant, versioned health rules, immutable snapshots/reasons, override expiry, at-risk plan, meaningful inactivity, outcome plans, renewal cycles/milestones/decision, churn/corrective event, win-back eligibility and recommendation-only advocacy.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| customer_success | `CustomerSuccessProfileService` | Maintain success owner, lifecycle, review date and integrity exceptions for active customers. | customer_success_profiles, organizations |
| customer_success | `HealthRuleService` | Manage effective-dated segment/service dimensions, weights, bands and thresholds. | health_rule_sets |
| customer_success | `HealthCalculationService` | Create immutable dimension-reasoned health snapshots without correlated double counting. | health_snapshots, health_reasons, tickets, feedback_responses, onboarding_cases, renewals |
| customer_success | `HealthOverrideService` | Apply authorized override without deleting computed score and expire into review task. | health_snapshots, tasks |
| customer_success | `SuccessPlanService` | Create/update/close outcome and risk plans with actions, blockers, evidence and cadence. | success_plans, success_plan_actions |
| customer_success | `InactivityService` | Detect service-specific meaningful-interaction gaps without treating automated sends as engagement. | timeline_events, communication_ledger, tasks |
| customer_success | `RenewalService` | Create one cycle, schedule milestones, compile risks/issues and record decision/value. | renewals, scheduled_jobs, health_snapshots |
| customer_success | `ChurnService` | Record explicit churn evidence, stop incompatible workflows and preserve corrective events. | churn_events, workflow_runs, scheduled_jobs |
| customer_success | `WinBackService` | Evaluate cooling period, permission, reason and owner for bounded low-frequency win-back. | churn_events, consent_preferences, workflow_runs |
| customer_success | `AdvocacyService` | Create recommendation only after validated positive evidence and no active risk/fatigue. | advocacy_suggestions, feedback_responses, health_snapshots, tickets |

### How to build the backend services


#### `CustomerSuccessProfileService`

- **Responsibility:** Maintain success owner, lifecycle, review date and integrity exceptions for active customers.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** customer_success_profiles, organizations
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `HealthRuleService`

- **Responsibility:** Manage effective-dated segment/service dimensions, weights, bands and thresholds.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** health_rule_sets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `HealthCalculationService`

- **Responsibility:** Create immutable dimension-reasoned health snapshots without correlated double counting.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** health_snapshots, health_reasons, tickets, feedback_responses, onboarding_cases, renewals
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `HealthOverrideService`

- **Responsibility:** Apply authorized override without deleting computed score and expire into review task.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** health_snapshots, tasks
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SuccessPlanService`

- **Responsibility:** Create/update/close outcome and risk plans with actions, blockers, evidence and cadence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** success_plans, success_plan_actions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `InactivityService`

- **Responsibility:** Detect service-specific meaningful-interaction gaps without treating automated sends as engagement.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** timeline_events, communication_ledger, tasks
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RenewalService`

- **Responsibility:** Create one cycle, schedule milestones, compile risks/issues and record decision/value.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** renewals, scheduled_jobs, health_snapshots
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ChurnService`

- **Responsibility:** Record explicit churn evidence, stop incompatible workflows and preserve corrective events.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** churn_events, workflow_runs, scheduled_jobs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `WinBackService`

- **Responsibility:** Evaluate cooling period, permission, reason and owner for bounded low-frequency win-back.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** churn_events, consent_preferences, workflow_runs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `AdvocacyService`

- **Responsibility:** Create recommendation only after validated positive evidence and no active risk/fatigue.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** advocacy_suggestions, feedback_responses, health_snapshots, tickets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create health_rule_sets/snapshots/reasons, success profiles/plans/actions, renewals, churn_events and advocacy_suggestions; indexes on state/owner/review/renewal/health band.

### Ordered implementation procedure

1. Define segments/dimensions/weights.
2. calculate rules snapshot.
3. create owner/review tasks.
4. open plan on risk.
5. detect inactivity.
6. create renewal cycle and 90/60/30 jobs.
7. compile open issues.
8. record decision/churn.
9. assess win-back.
10. suggest advocacy only after positive validated evidence.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/advocacy-suggestions` | List advocacy suggestion records | staff | 200 | 1500 ms | ≤18 | standard |
| `DELETE` | `/advocacy-suggestions/{id}` | Retire or soft-delete one advocacy suggestion | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/advocacy-suggestions/{id}` | Get one advocacy suggestion | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/advocacy-suggestions/{id}` | Update one advocacy suggestion | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/advocacy-suggestions/{id}/decision` | Approve, reject or defer an advocacy suggestion | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/churn-events` | List churn event records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/churn-events` | Create one churn event | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/churn-events/{id}` | Get one churn event | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/churn-events/{id}/correct` | Record a corrective churn event without rewriting history | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/customer-success-profiles` | List customer success profile records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/customer-success-profiles` | Create one customer success profile | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/customer-success-profiles/{id}` | Retire or soft-delete one customer success profile | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/customer-success-profiles/{id}` | Get one customer success profile | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/customer-success-profiles/{id}` | Update one customer success profile | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/health-snapshots` | List health snapshot records | staff | 200 | 1200 ms | ≤35 | standard |
| `GET` | `/health-snapshots/{id}` | Get one health snapshot | staff | 200 | 1200 ms | ≤35 | standard |
| `POST` | `/organizations/{id}/churn` | Record explicit churn event and terminate incompatible workflows | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/organizations/{id}/health` | Get current and historical health evidence | staff | 200 | 1200 ms | ≤35 | standard |
| `POST` | `/organizations/{id}/health/override` | Apply authorized health override with reason and expiry | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/organizations/{id}/health/refresh` | Queue bounded health recomputation | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `GET` | `/renewals` | List renewals | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/renewals` | Create a renewal | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/renewals/{id}` | Soft-delete or cancel one renewal | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/renewals/{id}` | Get one renewal | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/renewals/{id}` | Patch one renewal | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/renewals/{id}/decision` | Record renewal, contraction, loss, or pending decision | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/success-plan-actions` | List success plan action records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/success-plan-actions` | Create one success plan action | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/success-plan-actions/{id}` | Retire or soft-delete one success plan action | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/success-plan-actions/{id}` | Get one success plan action | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/success-plan-actions/{id}` | Update one success plan action | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/success-plans` | List success-plans | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/success-plans` | Create a success plan | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/success-plans/{id}` | Soft-delete or cancel one success plan | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/success-plans/{id}` | Get one success plan | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/success-plans/{id}` | Patch one success plan | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/success-plans/{id}/close` | Close success plan with verified outcome | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/advocacy-suggestions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List advocacy suggestion records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "advocacy-suggestion",
      "id": "01K2ADVOCACY00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Advocacy Suggestion"
      }
    }
  ],
  "links": {
    "self": "/api/v1/advocacy-suggestions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/advocacy-suggestions?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM advocacy_suggestions WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `DELETE /api/v1/advocacy-suggestions/{id}`

**Purpose:** Retire or soft-delete one advocacy suggestion

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
```

**Request body**

```json
{
  "reason_code": "ADMIN_RETIRE",
  "comment": "Reviewed and approved."
}
```

**Success:** `HTTP 204`

_No response body._

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **16 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM advocacy_suggestions with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

### Security controls

No model-only upsell/churn; consent/fatigue/active recovery guards; financial field policy; override reason/expiry; corrective events not history rewrite.

### Performance and resource budget

Portfolio/health/renewal pages ≤1.6s; health batch checkpointed nightly and yields to operational jobs; no full unindexed scan; one renewal workflow per cycle.

### Testing required

Health deterministic fixtures/double-counting, override expiry, active risk without plan, automated send not engagement, duplicate renewal sequence, churn correction, DNC win-back, advocacy suppression.

### What success looks like

Every active customer has success owner/review date; every at-risk customer has plan or approved exception; health is fully explainable; renewals and churn reconcile to value records; advocacy never auto-sends.

### Required deliverables

Success frontend/backend/API; health rules/defaults; renewal/churn workflows WF-21–25; portfolio reports; UAT-09 evidence.


---

## S32 — Build invitation-only customer portal and signed public flows

**Phase:** Phase 6 — Portal and public interaction

**Objective:** Provide focused self-service while preserving strict organization/contact isolation.

**Why this step exists:** A portal expands attack surface; every query and mutation must derive scope server-side and expose only deliberate customer wording.

**Prerequisites:** S07 portal identity/invitation; S09 portal policy; S11 files; onboarding/support/feedback modules.

### What to build in the frontend

Build separate portal shell, home, onboarding requests/progress, tickets/conversation, files, feedback, profile/preferences and public lead/support/feedback/preference/quote pages. Use plain language and mobile-first layouts.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Portal | `/portal` | Portal home | Show own organization onboarding requests, tickets, files and feedback actions. | 1400 ms | ≤18 | ≤700 KB |
| Portal | `/portal/onboarding` | Portal onboarding | List own organization onboarding cases and requested inputs. | 1400 ms | ≤18 | ≤700 KB |
| Portal | `/portal/onboarding/{id}` | Portal onboarding detail | Submit requested information/files and see approved progress/status wording. | 1500 ms | ≤20 | ≤800 KB |
| Portal | `/portal/tickets` | Portal tickets | List/create tickets for own organization. | 1400 ms | ≤18 | ≤700 KB |
| Portal | `/portal/tickets/{id}` | Portal ticket detail | Read customer-visible conversation and add messages/files. | 1500 ms | ≤22 | ≤800 KB |
| Portal | `/portal/files` | Portal files | List/download only portal-visible own-organization files. | 1300 ms | ≤16 | ≤650 KB |
| Portal | `/portal/feedback` | Portal feedback | Complete open authenticated surveys and review completion state. | 1400 ms | ≤18 | ≤700 KB |
| Portal | `/portal/preferences` | Portal preferences | Update allowed contact profile and communication preferences. | 1200 ms | ≤16 | ≤550 KB |
| Public | `/public/lead` | Public lead form | Accept a bounded, accessible sales enquiry without external CAPTCHA. | 1800 ms | ≤12 | ≤450 KB |
| Public | `/public/support` | Public support form | Accept bounded support intake with safe upload policy and neutral confirmation. | 1800 ms | ≤12 | ≤500 KB |
| Public | `/public/feedback/{token}` | Signed feedback | Show exact survey version and accept one scoped response. | 1600 ms | ≤12 | ≤450 KB |
| Public | `/public/preferences/{token}` | Signed preference center | Show/update only allowed purpose/channel preferences. | 1400 ms | ≤12 | ≤400 KB |
| Public | `/public/quote/{token}` | Signed quote view | View/download immutable issued quote and record intent for staff review. | 1500 ms | ≤12 | ≤750 KB |

### How to build the frontend


#### `/portal` — Portal home

- **Purpose:** Show own organization onboarding requests, tickets, files and feedback actions.
- **Components:** PortalShell; TaskCards; TicketSummary; PlainStatus
- **API/data:** GET /portal/me; GET portal onboarding/tickets/feedback
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open permitted object
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Server derives contact/organization from session
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤18 SQL, ≤700 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤18, compressed transfer ≤700 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/portal/onboarding` — Portal onboarding

- **Purpose:** List own organization onboarding cases and requested inputs.
- **Components:** CaseCards; Progress; RequestList
- **API/data:** GET portal onboarding; submit customer request; upload/download files
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open/submit request
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Portal organization scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤18 SQL, ≤700 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤18, compressed transfer ≤700 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/portal/onboarding/{id}` — Portal onboarding detail

- **Purpose:** Submit requested information/files and see approved progress/status wording.
- **Components:** Progress; RequestForms; SafeFileUpload; CustomerVisibleTimeline
- **API/data:** GET portal onboarding; submit customer request; upload/download files
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Submit/revise open request
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Portal organization scope; internal data absent
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/portal/tickets` — Portal tickets

- **Purpose:** List/create tickets for own organization.
- **Components:** TicketList; CreateTicketForm; StatusLabels
- **API/data:** GET/POST portal tickets; GET ticket; POST messages; files
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/open ticket
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Portal organization scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤18 SQL, ≤700 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤18, compressed transfer ≤700 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/portal/tickets/{id}` — Portal ticket detail

- **Purpose:** Read customer-visible conversation and add messages/files.
- **Components:** TicketHeader; CustomerConversation; ReplyForm; SafeFileUpload
- **API/data:** GET/POST portal tickets; GET ticket; POST messages; files
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Post message/file
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Portal organization and ticket scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/portal/files` — Portal files

- **Purpose:** List/download only portal-visible own-organization files.
- **Components:** FileList; ClassificationHelp; DownloadAction
- **API/data:** GET /portal/files/{id}; POST /portal/files
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Upload where request permits; download
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Portal file links derived server-side
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1300 ms, ≤16 SQL, ≤650 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1300 ms, SQL count ≤16, compressed transfer ≤650 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/portal/feedback` — Portal feedback

- **Purpose:** Complete open authenticated surveys and review completion state.
- **Components:** SurveyCards; AccessibleSurveyForm
- **API/data:** GET/POST portal feedback
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Submit response
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Portal contact/organization scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤18 SQL, ≤700 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤18, compressed transfer ≤700 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/portal/preferences` — Portal preferences

- **Purpose:** Update allowed contact profile and communication preferences.
- **Components:** ProfileForm; PreferenceMatrix; EvidenceNotice
- **API/data:** GET/PATCH /portal/me
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Update permitted fields
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Own portal identity only
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1200 ms, ≤16 SQL, ≤550 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1200 ms, SQL count ≤16, compressed transfer ≤550 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/public/lead` — Public lead form

- **Purpose:** Accept a bounded, accessible sales enquiry without external CAPTCHA.
- **Components:** LeadForm; Honeypot; TimingToken; PrivacyNotice; NeutralSuccess
- **API/data:** POST /public/leads
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Submit lead
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Public rate-limited and quarantinable
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤12 SQL, ≤450 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤12, compressed transfer ≤450 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/public/support` — Public support form

- **Purpose:** Accept bounded support intake with safe upload policy and neutral confirmation.
- **Components:** SupportForm; ImpactUrgency; SafeUpload; PrivacyNotice
- **API/data:** POST /public/support
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Submit ticket intent
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Public rate-limited
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤12 SQL, ≤500 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤12, compressed transfer ≤500 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/public/feedback/{token}` — Signed feedback

- **Purpose:** Show exact survey version and accept one scoped response.
- **Components:** TokenState; AccessibleSurvey; Confirmation
- **API/data:** GET/POST /public/feedback/{token}
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Submit response
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Signed purpose-bound token
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤12 SQL, ≤450 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤12, compressed transfer ≤450 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/public/preferences/{token}` — Signed preference center

- **Purpose:** Show/update only allowed purpose/channel preferences.
- **Components:** TokenState; PreferenceMatrix; Confirmation
- **API/data:** GET/PATCH /public/preferences/{token}
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Update preferences
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Signed purpose-bound token
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤12 SQL, ≤400 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤12, compressed transfer ≤400 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/public/quote/{token}` — Signed quote view

- **Purpose:** View/download immutable issued quote and record intent for staff review.
- **Components:** QuoteSnapshot; SafeDownload; Expiry; ResponseForm
- **API/data:** GET /public/quotes/{token}; POST response
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Accept/reject intent
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Signed quote-specific token
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤12 SQL, ≤750 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤12, compressed transfer ≤750 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement portal scope service, invite/recovery/session policy, object selectors that ignore client organization IDs, customer-visible status mapping, signed-link token hashes, public form abuse controls, portal file/message/upload services and maintenance-safe responses.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| portal | `PortalScopeService` | Derive contact/organization scope exclusively from authenticated session and apply to every selector/mutation. | users, portal_invitations, contact_organizations |
| portal | `PortalProfileService` | Expose/update only approved profile and preference fields. | contacts, contact_points, consent_preferences |
| portal | `PortalOnboardingService` | Expose approved case/request/progress wording and accept scoped submissions/files. | onboarding_cases, customer_requests, file_assets |
| portal | `PortalTicketService` | Create/list/read/reply to own-organization tickets without internal-note metadata. | tickets, ticket_events, file_assets |
| portal | `PortalFileService` | Authorize portal-visible file stream; never trust request organization ID or path. | file_assets, contact_organizations |
| portal | `PublicFormProtectionService` | Apply payload caps, IP/session/token throttles, honeypot, minimum fill time, duplicate and quarantine logic. | login_throttles, leads, tickets |
| portal | `SignedLinkService` | Issue/store token hash, bind purpose/object/action, enforce expiry/revocation/single use and neutral failure. | feedback_requests, quote_versions, consent_preferences, customer_requests |

### How to build the backend services


#### `PortalScopeService`

- **Responsibility:** Derive contact/organization scope exclusively from authenticated session and apply to every selector/mutation.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** users, portal_invitations, contact_organizations
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `PortalProfileService`

- **Responsibility:** Expose/update only approved profile and preference fields.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** contacts, contact_points, consent_preferences
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `PortalOnboardingService`

- **Responsibility:** Expose approved case/request/progress wording and accept scoped submissions/files.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** onboarding_cases, customer_requests, file_assets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `PortalTicketService`

- **Responsibility:** Create/list/read/reply to own-organization tickets without internal-note metadata.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** tickets, ticket_events, file_assets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `PortalFileService`

- **Responsibility:** Authorize portal-visible file stream; never trust request organization ID or path.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** file_assets, contact_organizations
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `PublicFormProtectionService`

- **Responsibility:** Apply payload caps, IP/session/token throttles, honeypot, minimum fill time, duplicate and quarantine logic.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** login_throttles, leads, tickets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SignedLinkService`

- **Responsibility:** Issue/store token hash, bind purpose/object/action, enforce expiry/revocation/single use and neutral failure.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** feedback_requests, quote_versions, consent_preferences, customer_requests
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Use users/portal invitations/contact relationships plus source records; no duplicate portal copy. Add token hash/expiry/revocation columns and portal access audit where needed.

### Ordered implementation procedure

1. Define every portal-visible field/status.
2. implement separate URL/templates/policies.
3. derive scope from session.
4. build invite/recovery.
5. expose onboarding/tickets/files/feedback.
6. implement signed forms.
7. add rate/honeypot/timing limits.
8. test every altered ID.
9. test 360px/keyboard.
10. prove maintenance failure.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `POST` | `/portal/customer-requests/{id}/submit` | Submit requested fields/files within portal scope | portal | 201 | 1800 ms | ≤20 | Idempotency-Key |
| `GET` | `/portal/feedback` | List open and completed authenticated feedback requests | portal | 200 | 1400 ms | ≤18 | standard |
| `POST` | `/portal/feedback/{id}` | Submit an authenticated portal feedback response | portal | 201 | 1800 ms | ≤20 | Idempotency-Key |
| `POST` | `/portal/files` | Upload and validate a portal-scoped private file | portal | 201 | 1800 ms | ≤20 | Idempotency-Key |
| `GET` | `/portal/files/{id}` | Authorize and stream one portal-visible private file | portal | 200 | 1400 ms | ≤18 | standard |
| `GET` | `/portal/me` | Get portal contact and organization scope | portal | 200 | 1400 ms | ≤18 | standard |
| `PATCH` | `/portal/me` | Update permitted portal profile and preferences | portal | 200 | 1800 ms | ≤20 | If-Match |
| `GET` | `/portal/onboarding` | List portal-visible onboarding cases and requests | portal | 200 | 1400 ms | ≤18 | standard |
| `GET` | `/portal/onboarding/{id}` | Get one organization-scoped onboarding case | portal | 200 | 1400 ms | ≤18 | standard |
| `GET` | `/portal/tickets` | List organization-scoped portal tickets | portal | 200 | 1400 ms | ≤18 | standard |
| `POST` | `/portal/tickets` | Create a ticket in the logged-in organization scope | portal | 201 | 1800 ms | ≤20 | Idempotency-Key |
| `GET` | `/portal/tickets/{id}` | Get one organization-scoped ticket and customer-visible conversation | portal | 200 | 1400 ms | ≤18 | standard |
| `POST` | `/portal/tickets/{id}/messages` | Add customer-visible message to owned organization ticket | portal | 201 | 1800 ms | ≤20 | Idempotency-Key |
| `GET` | `/public/feedback/{token}` | Get a signed, expiring feedback form without exposing customer IDs | signed | 200 | 1800 ms | ≤12 | standard |
| `POST` | `/public/feedback/{token}` | Submit signed feedback response | signed | 201 | 1800 ms | ≤12 | Idempotency-Key |
| `POST` | `/public/leads` | Submit a rate-limited public lead form | public | 202 | 1800 ms | ≤12 | Idempotency-Key |
| `GET` | `/public/preferences/{token}` | Get signed preference center | signed | 200 | 1800 ms | ≤12 | standard |
| `PATCH` | `/public/preferences/{token}` | Update allowed communication preferences and evidence | signed | 200 | 1800 ms | ≤12 | Idempotency-Key |
| `GET` | `/public/quotes/{token}` | View/download one signed expiring quote snapshot | signed | 200 | 1800 ms | ≤12 | standard |
| `POST` | `/public/quotes/{token}/respond` | Record signed quote acceptance/rejection intent for staff review | signed | 201 | 1800 ms | ≤12 | Idempotency-Key |
| `POST` | `/public/support` | Submit a rate-limited public support form | public | 202 | 1800 ms | ≤12 | Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/portal/feedback?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List open and completed authenticated feedback requests

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: portal_session=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "feedback",
      "id": "01K2FEEDBACK00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Feedback"
      }
    }
  ],
  "links": {
    "self": "/api/v1/portal/feedback?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/portal/feedback?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1400 ms**; p99 ≤ **3000 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM feedbacks WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1400 ms and p99 ≤3000 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/portal/customer-requests/{id}/submit`

**Purpose:** Submit requested fields/files within portal scope

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: portal_session=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "file",
    "attributes": {
      "original_name": "requirements.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 245678,
      "classification": "CONFIDENTIAL",
      "validation_state": "ACCEPTED",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb924..."
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "file",
    "id": "01K2FILE000000000000000000",
    "version": 8,
    "attributes": {
      "original_name": "requirements.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 245678,
      "classification": "CONFIDENTIAL",
      "validation_state": "ACCEPTED",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb924...",
      "last_action": "SUBMIT",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **20 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM file_assets with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); UNIQUE(sha256, size_bytes); INDEX(owner_type, owner_id, deleted_at, public_id); INDEX(validation_state, created_at)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤20 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Exhaustive IDOR; stricter session timeouts; no internal notes/risk/queue metadata; signed tokens purpose-bound/expiring/revocable; CSRF; upload limits; neutral errors; no public directory/API.

### Performance and resource budget

Portal/public p95 ≤2.5s mixed load, target ≤1.8s typical; ≤20 queries; payloads bounded; abuse controls preserve worker slots; no external scripts/CDN.

### Testing required

Cross-organization IDs for every resource/action, direct file path, token tamper/replay/cross-purpose, CSRF, session expiry, upload abuse, rate-limit accessibility, internal metadata leakage, maintenance.

### What success looks like

A portal user can complete core onboarding/support/feedback flows on mobile, but cannot infer or access another organization or internal artifact through URL, search, count, file or response metadata.

### Required deliverables

Portal/public frontend/backend/API; visibility mapping register; IDOR suite; signed-link service; portal UAT-11 evidence.


---

## S33 — Build reconciled dashboards, saved views and controlled exports

**Phase:** Phase 6 — Reporting and data operations

**Objective:** Make management information actionable, permission-safe and reproducible rather than a separate source of truth.

**Why this step exists:** Dashboard totals are dangerous when definitions, permissions or drilldowns do not reconcile.

**Prerequisites:** All source domains stable; S09 authorization; S18 saved work patterns.

### What to build in the frontend

Build role dashboards and report pages for sales, onboarding, support, feedback, success, automation, data quality and health; metric definition drawer, saved views, drilldowns and export status/download.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Manager | `/sales/forecast` | Forecast dashboard | Reconcile pipeline, upside, commit and closed values with source probabilities. | 1800 ms | ≤24 | ≤1000 KB |
| Staff | `/reports` | Reports home | Role-aware operational dashboards and saved views. | 1800 ms | ≤24 | ≤1100 KB |
| Staff | `/reports/sales` | Sales reporting | Lead source/SLA/conversion and pipeline/forecast/velocity/loss metrics. | 1800 ms | ≤24 | ≤1100 KB |
| Staff | `/reports/support` | Support reporting | Backlog, first response, resolution, SLA, waiting, reopen, cause and satisfaction. | 1800 ms | ≤24 | ≤1100 KB |
| Staff | `/reports/onboarding` | Onboarding reporting | Handoff quality, time-to-value, blockers, completion and feedback. | 1800 ms | ≤24 | ≤1100 KB |
| Staff | `/reports/success` | Success reporting | Health change, recovery, renewal, churn and retention. | 1800 ms | ≤24 | ≤1100 KB |
| Staff | `/reports/feedback` | Feedback reporting | Response, distribution, themes, recovery and privacy-suppressed cohorts. | 1800 ms | ≤24 | ≤1100 KB |
| Staff | `/reports/automation` | Automation reporting | Enrolment, exits, failures, replies, tasks, outcomes and version comparison. | 1800 ms | ≤24 | ≤1100 KB |
| Staff | `/reports/data-quality` | Data-quality reporting | Duplicate, missing, invalid, stale, orphan and retention exceptions. | 1800 ms | ≤24 | ≤1100 KB |
| Staff | `/reports/system-health` | System-health reporting | Queue, mailbox, DB, file, inode, error and backup health. | 1800 ms | ≤24 | ≤1100 KB |
| Staff | `/data/exports` | Export jobs | Create permissioned asynchronous exports and retrieve expiring artifacts. | 1400 ms | ≤18 | ≤800 KB |

### How to build the frontend


#### `/sales/forecast` — Forecast dashboard

- **Purpose:** Reconcile pipeline, upside, commit and closed values with source probabilities.
- **Components:** ForecastCards; CurrencyBasis; StageChart; ExceptionTable
- **API/data:** GET/POST/PATCH /opportunities; transitions, stakeholders, lines, forecast report
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Drill to records; bounded export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Manager scope + financial visibility
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/reports` — Reports home

- **Purpose:** Role-aware operational dashboards and saved views.
- **Components:** ReportFilters; MetricDefinitionLink; KPIBlocks; AccessibleChart; DrilldownTable; ExportButton
- **API/data:** GET /reports/{code}; GET/POST /saved-views; POST /exports
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save view; queue export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Report and source-record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/reports/sales` — Sales reporting

- **Purpose:** Lead source/SLA/conversion and pipeline/forecast/velocity/loss metrics.
- **Components:** ReportFilters; MetricDefinitionLink; KPIBlocks; AccessibleChart; DrilldownTable; ExportButton
- **API/data:** GET /reports/{code}; GET/POST /saved-views; POST /exports
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save view; queue export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Report and source-record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/reports/support` — Support reporting

- **Purpose:** Backlog, first response, resolution, SLA, waiting, reopen, cause and satisfaction.
- **Components:** ReportFilters; MetricDefinitionLink; KPIBlocks; AccessibleChart; DrilldownTable; ExportButton
- **API/data:** GET /reports/{code}; GET/POST /saved-views; POST /exports
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save view; queue export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Report and source-record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/reports/onboarding` — Onboarding reporting

- **Purpose:** Handoff quality, time-to-value, blockers, completion and feedback.
- **Components:** ReportFilters; MetricDefinitionLink; KPIBlocks; AccessibleChart; DrilldownTable; ExportButton
- **API/data:** GET /reports/{code}; GET/POST /saved-views; POST /exports
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save view; queue export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Report and source-record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/reports/success` — Success reporting

- **Purpose:** Health change, recovery, renewal, churn and retention.
- **Components:** ReportFilters; MetricDefinitionLink; KPIBlocks; AccessibleChart; DrilldownTable; ExportButton
- **API/data:** GET /reports/{code}; GET/POST /saved-views; POST /exports
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save view; queue export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Report and source-record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/reports/feedback` — Feedback reporting

- **Purpose:** Response, distribution, themes, recovery and privacy-suppressed cohorts.
- **Components:** ReportFilters; MetricDefinitionLink; KPIBlocks; AccessibleChart; DrilldownTable; ExportButton
- **API/data:** GET /reports/{code}; GET/POST /saved-views; POST /exports
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save view; queue export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Report and source-record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/reports/automation` — Automation reporting

- **Purpose:** Enrolment, exits, failures, replies, tasks, outcomes and version comparison.
- **Components:** ReportFilters; MetricDefinitionLink; KPIBlocks; AccessibleChart; DrilldownTable; ExportButton
- **API/data:** GET /reports/{code}; GET/POST /saved-views; POST /exports
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save view; queue export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Report and source-record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/reports/data-quality` — Data-quality reporting

- **Purpose:** Duplicate, missing, invalid, stale, orphan and retention exceptions.
- **Components:** ReportFilters; MetricDefinitionLink; KPIBlocks; AccessibleChart; DrilldownTable; ExportButton
- **API/data:** GET /reports/{code}; GET/POST /saved-views; POST /exports
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save view; queue export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Report and source-record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/reports/system-health` — System-health reporting

- **Purpose:** Queue, mailbox, DB, file, inode, error and backup health.
- **Components:** ReportFilters; MetricDefinitionLink; KPIBlocks; AccessibleChart; DrilldownTable; ExportButton
- **API/data:** GET /reports/{code}; GET/POST /saved-views; POST /exports
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Save view; queue export
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Report and source-record scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1800 ms, ≤24 SQL, ≤1100 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1800 ms, SQL count ≤24, compressed transfer ≤1100 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/data/exports` — Export jobs

- **Purpose:** Create permissioned asynchronous exports and retrieve expiring artifacts.
- **Components:** ExportTable; DatasetPicker; FieldPolicyPreview; StepUp; Progress
- **API/data:** GET/POST /exports; cancel/download
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/cancel/download
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** export capability + field policy + step-up
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤18 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤18, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement metric definitions/versioning, incremental aggregates, permission-aware selectors, saved allowlisted filter definitions, drilldown contracts, asynchronous exports, step-up/approval and CSV formula neutralization.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| reporting | `MetricDefinitionService` | Manage versioned KPI owner/source/time/filter/exclusion definitions. | metric_definitions |
| reporting | `AggregateService` | Incrementally compute reconciled bounded aggregates and retain definition version. | metric_aggregates, source event tables |
| reporting | `DashboardService` | Return role/scope-aware cards/charts/drilldowns from authorized selectors and aggregates. | metric_aggregates, saved_views |
| reporting | `SavedViewService` | Validate bounded allowlisted filters/columns/visibility without raw SQL. | saved_views |
| reporting | `ExportService` | Snapshot current authorization/fields/criteria, queue job, generate private expiring artifact and audit hash/count. | export_jobs, file_assets, audit_events |
| reporting | `CsvSafetyService` | Preserve types and neutralize spreadsheet formula injection. | export_jobs |

### How to build the backend services


#### `MetricDefinitionService`

- **Responsibility:** Manage versioned KPI owner/source/time/filter/exclusion definitions.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** metric_definitions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `AggregateService`

- **Responsibility:** Incrementally compute reconciled bounded aggregates and retain definition version.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** metric_aggregates, source event tables
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `DashboardService`

- **Responsibility:** Return role/scope-aware cards/charts/drilldowns from authorized selectors and aggregates.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** metric_aggregates, saved_views
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SavedViewService`

- **Responsibility:** Validate bounded allowlisted filters/columns/visibility without raw SQL.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** saved_views
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ExportService`

- **Responsibility:** Snapshot current authorization/fields/criteria, queue job, generate private expiring artifact and audit hash/count.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** export_jobs, file_assets, audit_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `CsvSafetyService`

- **Responsibility:** Preserve types and neutralize spreadsheet formula injection.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** export_jobs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create metric_definitions/aggregates, saved_views and export_jobs; index metric/version/period/scope and job owner/state/expiry.

### Ordered implementation procedure

1. Approve formulas/time basis.
2. create definitions.
3. build incremental aggregate jobs.
4. reconcile to source events.
5. implement authorized drilldown.
6. implement saved views.
7. create export snapshot/job.
8. generate safe file privately.
9. expire/audit.
10. add scheduled minimal digests.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/exports` | List exports | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/exports` | Create a export job | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `GET` | `/exports/{id}` | Get one export job | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/exports/{id}/cancel` | Cancel queued export and expire any artifact | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/exports/{id}/download` | Authorize and download a completed unexpired export artifact | staff | 200 | 1200 ms | ≤25 | standard |
| `GET` | `/metric-definitions` | List metric definition records | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/metric-definitions` | Create one metric definition | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/metric-definitions/{id}` | Retire or soft-delete one metric definition | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/metric-definitions/{id}` | Get one metric definition | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/metric-definitions/{id}` | Update one metric definition | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/reports/{code}` | Get a bounded, permission-aware report result | staff | 200 | 2000 ms | ≤20 | standard |
| `GET` | `/saved-views` | List saved-views | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/saved-views` | Create a saved view | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/saved-views/{id}` | Soft-delete or cancel one saved view | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/saved-views/{id}` | Get one saved view | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/saved-views/{id}` | Patch one saved view | staff | 200 | 1800 ms | ≤22 | If-Match |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/exports?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN`

**Purpose:** List exports

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "export",
      "id": "01K2EXPORT0000000000000000",
      "version": 7,
      "attributes": {
        "state": "QUEUED",
        "dataset": "CUSTOMERS",
        "row_count": null,
        "expires_at": null
      }
    }
  ],
  "links": {
    "self": "/api/v1/exports?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at&filter[state]=OPEN",
    "next": "/api/v1/exports?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM export_jobs WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, requested_by_id, created_at, public_id); INDEX(expires_at, state)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/exports`

**Purpose:** Create a export job

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "export",
    "attributes": {
      "state": "QUEUED",
      "dataset": "CUSTOMERS",
      "row_count": null,
      "expires_at": null
    }
  }
}
```

**Success:** `HTTP 202`

**Response body**

```json
{
  "data": {
    "type": "job",
    "id": "01K2JOB000000000000000001",
    "attributes": {
      "state": "QUEUED",
      "submitted_at": "2026-07-14T08:00:00Z",
      "status_url": "/api/v1/jobs/01K2JOB000000000000000001"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001"
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1200 ms**; p99 ≤ **2500 ms** under the representative mixed workload.

- Maximum **12 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM export_jobs with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); INDEX(state, requested_by_id, created_at, public_id); INDEX(expires_at, state)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1200 ms and p99 ≤2500 ms on the representative mixed workload, uses ≤12 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Counts filtered before aggregation/disclosure; tiny anonymous cohorts suppressed; no raw SQL; export fields/rows reauthorized at execution; CSV injection neutralized; sensitive details stay behind login.

### Performance and resource budget

Report first page p95 ≤2s; standard ≤24 queries; exports return 202 ≤1.2s and run bounded; aggregates incremental; artifact expires ≤7 days.

### Testing required

Metric formula/timezone/currency versions, aggregate-vs-drilldown, cross-role count leakage, stale permissions before export, formula injection, expiry/download, large job cancel/restart, scheduled digest reauth.

### What success looks like

Every displayed number links to the exact authorized record set and named definition/version; exports cannot include unauthorized rows/fields and never block HTTP; dashboards highlight action, not vanity totals.

### Required deliverables

Reporting frontend/backend/API; KPI definitions; aggregate jobs; saved views; export pipeline; reconciliation/security tests; UAT-14.


---

## S34 — Build imports, retention, archives, privacy cases and legal holds

**Phase:** Phase 6 — Reporting and data operations

**Objective:** Move legacy/ongoing data safely and control growth under the database/inode limits.

**Why this step exists:** Shared hosting has hard capacity ceilings; unsafe imports can message customers or duplicate identities, and retention/purge can destroy evidence.

**Prerequisites:** S17 identity quality; S33 exports; S10 audit; approved retention/legal policy.

### What to build in the frontend

Build import wizard/batch progress/mapping/preview/duplicates/errors/reconciliation/release/rollback; retention policy/run/preview; archive inventory/retrieval; privacy case and legal-hold screens.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Operations | `/data/imports` | Import batches | Stage, map, validate, preview, commit, reconcile, release and rollback bounded data imports. | 1600 ms | ≤24 | ≤950 KB |
| Admin | `/admin/privacy` | Privacy cases | Handle access, correction, restriction, deletion, objection and portability. | 1500 ms | ≤24 | ≤950 KB |
| Admin | `/admin/legal-holds` | Legal holds | Create/review/release retention overrides. | 1500 ms | ≤24 | ≤950 KB |
| Admin | `/admin/retention` | Retention and archives | Dry-run/execute retention, verify archives and retrieve records. | 1500 ms | ≤24 | ≤950 KB |

### How to build the frontend


#### `/data/imports` — Import batches

- **Purpose:** Stage, map, validate, preview, commit, reconcile, release and rollback bounded data imports.
- **Components:** ImportTable; Upload; MappingEditor; ValidationSummary; DuplicatePreview; Progress
- **API/data:** GET/POST /imports; upload, validate, preview, commit, release, rollback
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Create/upload/validate/commit/release/rollback
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** data_ops + source record capabilities
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/admin/privacy` — Privacy cases

- **Purpose:** Handle access, correction, restriction, deletion, objection and portability.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET/POST/PATCH /privacy-cases; complete
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/admin/legal-holds` — Legal holds

- **Purpose:** Create/review/release retention overrides.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET/POST/PATCH /legal-holds; release
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/admin/retention` — Retention and archives

- **Purpose:** Dry-run/execute retention, verify archives and retrieve records.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** retention policies/runs and archives endpoints
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement format detection, saved allowlisted mappings, row source keys, chunk commit/checkpoint, quarantine and release, rollback preview; policy-driven dry-run/archive/purge, hold projection, archive package/manifest/checksum/retrieval and privacy case workflow.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| governance | `PrivacyCaseService` | Coordinate access/correction/restriction/deletion/objection/portability evidence and approvals. | privacy_cases, export_jobs, retention_runs |
| governance | `LegalHoldService` | Create scoped retention override and force archive/purge jobs to skip held records. | legal_holds, retention_runs |
| data_ops | `ImportService` | Stage source, detect format, map allowlisted transformations, validate, preview, chunk commit and hold automation. | import_mappings, import_batches, import_rows |
| data_ops | `ImportReconciliationService` | Compare source/result counts, sums, status, ownership, files, rejects and release decision. | import_batches, import_rows |
| data_ops | `ImportRollbackService` | Preview/reverse safe batch-provenance changes while preserving subsequent human edits. | import_batches, import_rows, source tables |
| data_ops | `RetentionService` | Evaluate versioned record-class/state policy, legal holds, dry-run, archive and final purge evidence. | retention_policies, retention_runs, legal_holds |
| data_ops | `ArchiveService` | Package old bodies/logs/files into checksummed indexed compressed private archives and retrieve one record within target. | archive_manifests, archive_items, file_assets |

### How to build the backend services


#### `PrivacyCaseService`

- **Responsibility:** Coordinate access/correction/restriction/deletion/objection/portability evidence and approvals.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** privacy_cases, export_jobs, retention_runs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `LegalHoldService`

- **Responsibility:** Create scoped retention override and force archive/purge jobs to skip held records.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** legal_holds, retention_runs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ImportService`

- **Responsibility:** Stage source, detect format, map allowlisted transformations, validate, preview, chunk commit and hold automation.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** import_mappings, import_batches, import_rows
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ImportReconciliationService`

- **Responsibility:** Compare source/result counts, sums, status, ownership, files, rejects and release decision.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** import_batches, import_rows
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ImportRollbackService`

- **Responsibility:** Preview/reverse safe batch-provenance changes while preserving subsequent human edits.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** import_batches, import_rows, source tables
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RetentionService`

- **Responsibility:** Evaluate versioned record-class/state policy, legal holds, dry-run, archive and final purge evidence.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** retention_policies, retention_runs, legal_holds
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ArchiveService`

- **Responsibility:** Package old bodies/logs/files into checksummed indexed compressed private archives and retrieve one record within target.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** archive_manifests, archive_items, file_assets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create import_mappings/batches/rows, retention_policies/runs, archive_manifests/items, privacy_cases and legal_holds with source/state/time/hold indexes.

### Ordered implementation procedure

1. Stage source.
2. confirm encoding/delimiter/header.
3. map/validate.
4. preview candidates/errors.
5. commit bounded chunks with automation held.
6. reconcile.
7. release tasks only.
8. dry-run retention.
9. archive/verify before delete.
10. purge with signed destruction report/hold skips.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/legal-holds` | List legal hold records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/legal-holds` | Create one legal hold | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/legal-holds/{id}` | Retire or soft-delete one legal hold | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/legal-holds/{id}` | Get one legal hold | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/legal-holds/{id}` | Update one legal hold | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/legal-holds/{id}/release` | Release legal hold after authority and dependency review | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/privacy-cases` | List privacy case records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/privacy-cases` | Create one privacy case | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/privacy-cases/{id}` | Retire or soft-delete one privacy case | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/privacy-cases/{id}` | Get one privacy case | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/privacy-cases/{id}` | Update one privacy case | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/privacy-cases/{id}/complete` | Complete privacy case with evidence, approvals and report | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/retention-policies` | List retention policy records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/retention-policies` | Create one retention policy | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/retention-policies/{id}` | Retire or soft-delete one retention policy | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/retention-policies/{id}` | Get one retention policy | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/retention-policies/{id}` | Update one retention policy | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/archive/{type}/{id}` | Retrieve one authorized archived record within bounded time | staff | 200 | 1200 ms | ≤25 | standard |
| `GET` | `/archives` | List archive manifests and verification state | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/archives/{id}/verify` | Verify archive manifest and member checksums | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `GET` | `/imports` | List imports | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/imports` | Create a import batch | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/imports/{id}` | Get one import batch | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/imports/{id}/commit` | Commit approved rows in bounded chunks while automation remains held | staff | 202 | 1200 ms | ≤12 | If-Match, Idempotency-Key, 202 job |
| `GET` | `/imports/{id}/preview` | Get staged mapping, validation, duplicates and sample rows | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/imports/{id}/release` | Release reconciled imported records without bulk messaging | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/imports/{id}/rollback` | Queue safe import rollback preview or execution | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `POST` | `/imports/{id}/upload` | Attach and checksum a bounded import source file | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/imports/{id}/validate` | Validate staged import without business side effects | staff | 202 | 1200 ms | ≤12 | If-Match, Idempotency-Key, 202 job |
| `GET` | `/retention-runs` | List retention dry-run and execution records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/retention-runs` | Start retention dry-run or execution job | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `GET` | `/retention-runs/{id}` | Get retention result, held/skipped/error counts and manifest | staff | 200 | 1200 ms | ≤25 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/legal-holds?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List legal hold records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "legal-hold",
      "id": "01K2LEGALHOL00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Legal Hold"
      }
    }
  ],
  "links": {
    "self": "/api/v1/legal-holds?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/legal-holds?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM legal_holds WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/privacy-cases/{id}/complete`

**Purpose:** Complete privacy case with evidence, approvals and report

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
If-Match: "v7"
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "approval-request",
    "id": "01K2APPROVAL00000000000000",
    "version": 8,
    "attributes": {
      "kind": "QUOTE_ISSUE",
      "state": "COMPLETED",
      "requested_by": "01K2USER0000000000000000001",
      "reviewer_id": "01K2USER0000000000000000002",
      "due_at": "2026-07-15T12:00:00Z",
      "last_action": "COMPLETE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM approval_requests with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); INDEX(state, reviewer_id, due_at, public_id); INDEX(target_type, target_id, state)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 412 stale If-Match; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

No arbitrary script/formula; imports cannot trigger outbound mail before release; export/import files private; purge requires authority/step-up; legal hold always wins; production data prohibited in staging without approved anonymization.

### Performance and resource budget

HTTP upload/submit bounded; commit/archive/purge are jobs; chunk ≤safe measured rows/time; DB warning 250MB/high 300MB/critical 340MB/block 360–375MB; archive single-record retrieval <60s.

### Testing required

Encoding/malformed/oversize, idempotent re-import, interrupted chunk, duplicate resolution, rollback after human edit, no automation in quarantine, hold skip, archive corruption, purge dependency, privacy deadlines.

### What success looks like

Migration/import counts and samples reconcile; no imported record contacts a customer unexpectedly; archives verify before source detail deletion; held records never purge; capacity trend stays safely below block.

### Required deliverables

Import/retention/archive/privacy frontend/backend/API; migration mappings; archive format; capacity thresholds; UAT-10 and governance evidence.


---

## S35 — Build local explainable AI, feedback, evaluation and governance

**Phase:** Phase 7 — Decision intelligence

**Objective:** Add bounded intelligence that improves prioritization/classification while core operation remains independent.

**Why this step exists:** Small datasets and shared hosting make opaque or autonomous AI unsafe; rules-first observation and measurable outcomes are required.

**Prerequisites:** Stable source events/outcomes; S31 health; S30 text feedback; S24 inbound email; approved model cards.

### What to build in the frontend

Build recommendation list/detail/explanation/feedback, model registry/card/version/evaluation, training runs and drift dashboards. Show output, confidence/abstention, reasons, missing data, evidence, version, expiry, actions and non-automatic boundary.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Staff | `/intelligence/predictions` | Recommendations | Review current scores/classifications, confidence, reasons, expiry and feedback state. | 1500 ms | ≤22 | ≤900 KB |
| Staff | `/intelligence/predictions/{id}` | Prediction explanation | Explain output, evidence, missing information, version, action options and non-automatic boundary. | 1400 ms | ≤24 | ≤850 KB |
| Admin | `/intelligence/models` | Model registry | List model cards, versions, tier, owner, review date and incident state. | 1400 ms | ≤20 | ≤800 KB |
| Admin | `/intelligence/models/{id}` | Model card and versions | Review purpose, population, features, harms, metrics, artifacts, approvals and rollback. | 1600 ms | ≤26 | ≤1000 KB |
| Admin | `/intelligence/training` | Training runs | Monitor checkpointed candidate training/evaluation without auto-promotion. | 1400 ms | ≤20 | ≤850 KB |
| Admin | `/intelligence/drift` | Model monitoring | Review distribution, confidence, abstention, disagreement and delayed outcomes. | 1700 ms | ≤24 | ≤1000 KB |

### How to build the frontend


#### `/intelligence/predictions` — Recommendations

- **Purpose:** Review current scores/classifications, confidence, reasons, expiry and feedback state.
- **Components:** PredictionFilters; ExplanationCards; AbstainBadges
- **API/data:** GET /predictions; feedback; refresh
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Submit feedback; refresh
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Entity scope + use-case capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤22 SQL, ≤900 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤22, compressed transfer ≤900 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/intelligence/predictions/{id}` — Prediction explanation

- **Purpose:** Explain output, evidence, missing information, version, action options and non-automatic boundary.
- **Components:** PredictionHeader; ReasonList; EvidenceLinks; MissingFeatures; FeedbackForm
- **API/data:** GET /predictions; feedback; refresh
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Accept/reject/modify/refresh
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Entity scope
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤24 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤24, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/intelligence/models` — Model registry

- **Purpose:** List model cards, versions, tier, owner, review date and incident state.
- **Components:** ModelTable; TierBadges; ReviewWarnings
- **API/data:** GET /model-cards and model versions; evaluation, promote/demote/retire
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Open card/version
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** model_governance capability
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤800 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤800 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/intelligence/models/{id}` — Model card and versions

- **Purpose:** Review purpose, population, features, harms, metrics, artifacts, approvals and rollback.
- **Components:** ModelCard; VersionList; EvaluationCharts; ArtifactHash; PromotionPanel
- **API/data:** GET /model-cards and model versions; evaluation, promote/demote/retire
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Promote/demote/retire
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** model_governance + four-eyes
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1600 ms, ≤26 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1600 ms, SQL count ≤26, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/intelligence/training` — Training runs

- **Purpose:** Monitor checkpointed candidate training/evaluation without auto-promotion.
- **Components:** TrainingTable; DatasetWindow; Checkpoints; Metrics
- **API/data:** GET/POST /training-runs; cancel
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Start/cancel candidate run
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** model_governance
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1400 ms, ≤20 SQL, ≤850 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1400 ms, SQL count ≤20, compressed transfer ≤850 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/intelligence/drift` — Model monitoring

- **Purpose:** Review distribution, confidence, abstention, disagreement and delayed outcomes.
- **Components:** DriftCharts; Thresholds; SegmentTable; IncidentLinks
- **API/data:** GET /model-monitoring; model cards/versions
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Demote/disable through model command
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** model_governance
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1700 ms, ≤24 SQL, ≤1000 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1700 ms, SQL count ≤24, compressed transfer ≤1000 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement feature registry/time-safe extractor, rule engine, weighted scores, pure-Python multinomial Naive Bayes where justified, immutable predictions/reasons, staff feedback, verified outcomes, checkpointed training, chronological evaluation, artifact checksum, promotion/demotion/tier and drift incident.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| intelligence | `FeatureRegistryService` | Register semantic type, observation time, missing behavior, sensitivity/proxy review and extraction owner. | feature_definitions |
| intelligence | `FeatureExtractionService` | Materialize point-in-time allowlisted features without future leakage. | feature_definitions, source event tables |
| intelligence | `ModelCardService` | Register purpose, population, harms, output, metrics, thresholds, tier, owner and review date. | model_cards |
| intelligence | `RuleEngine` | Execute deterministic rules/weighted scores with reason codes and missing-data abstention. | model_versions, predictions, prediction_reasons |
| intelligence | `NaiveBayesClassifier` | Run bounded pure-Python multinomial classification with severe phrase override and confidence abstention. | model_versions, predictions, prediction_reasons |
| intelligence | `PredictionService` | Persist immutable output, feature snapshot/hash, confidence, reasons, expiry and evidence links. | predictions, prediction_reasons |
| intelligence | `RecommendationFeedbackService` | Record accepted/rejected/modified/wrong category/priority and link subsequent action. | recommendation_feedback |
| intelligence | `OutcomeLabelService` | Attach verified delayed outcome separately from staff preference feedback. | outcome_labels |
| intelligence | `TrainingService` | Build checkpointed chronological candidate dataset/model artifact within row/time/memory bounds. | training_runs, model_versions |
| intelligence | `EvaluationService` | Compare chronological holdout to rules/current baseline using class, calibration, coverage, severe-miss and operational-cost gates. | training_runs, model_monitoring_metrics |
| intelligence | `ModelArtifactService` | Checksum/sign immutable JSON artifact, verify load compatibility and support rollback. | model_versions, file_assets |
| intelligence | `DriftService` | Monitor distribution, confidence, abstention, disagreement and delayed outcomes; create incident/demote. | model_monitoring_metrics, system_incidents |
| intelligence | `ModelPromotionService` | Require named four-eyes approval and prohibit automatic promotion/high-impact actions. | model_versions, approval_requests, audit_events |

### How to build the backend services


#### `FeatureRegistryService`

- **Responsibility:** Register semantic type, observation time, missing behavior, sensitivity/proxy review and extraction owner.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** feature_definitions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `FeatureExtractionService`

- **Responsibility:** Materialize point-in-time allowlisted features without future leakage.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** feature_definitions, source event tables
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ModelCardService`

- **Responsibility:** Register purpose, population, harms, output, metrics, thresholds, tier, owner and review date.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** model_cards
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RuleEngine`

- **Responsibility:** Execute deterministic rules/weighted scores with reason codes and missing-data abstention.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** model_versions, predictions, prediction_reasons
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `NaiveBayesClassifier`

- **Responsibility:** Run bounded pure-Python multinomial classification with severe phrase override and confidence abstention.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** model_versions, predictions, prediction_reasons
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `PredictionService`

- **Responsibility:** Persist immutable output, feature snapshot/hash, confidence, reasons, expiry and evidence links.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** predictions, prediction_reasons
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RecommendationFeedbackService`

- **Responsibility:** Record accepted/rejected/modified/wrong category/priority and link subsequent action.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** recommendation_feedback
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `OutcomeLabelService`

- **Responsibility:** Attach verified delayed outcome separately from staff preference feedback.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** outcome_labels
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `TrainingService`

- **Responsibility:** Build checkpointed chronological candidate dataset/model artifact within row/time/memory bounds.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** training_runs, model_versions
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `EvaluationService`

- **Responsibility:** Compare chronological holdout to rules/current baseline using class, calibration, coverage, severe-miss and operational-cost gates.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** training_runs, model_monitoring_metrics
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ModelArtifactService`

- **Responsibility:** Checksum/sign immutable JSON artifact, verify load compatibility and support rollback.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** model_versions, file_assets
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `DriftService`

- **Responsibility:** Monitor distribution, confidence, abstention, disagreement and delayed outcomes; create incident/demote.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** model_monitoring_metrics, system_incidents
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `ModelPromotionService`

- **Responsibility:** Require named four-eyes approval and prohibit automatic promotion/high-impact actions.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** model_versions, approval_requests, audit_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create model_cards, feature_definitions, model_versions, predictions/reasons, recommendation_feedback, outcome_labels, training_runs and monitoring metrics; index entity/use-case/time/version/review/outcome.

### Ordered implementation procedure

1. Register use case/harms.
2. approve features/time semantics.
3. implement rules baseline.
4. record observation predictions.
5. collect staff feedback/outcomes.
6. reach data threshold.
7. train bounded candidate.
8. evaluate chronological holdout/baseline/severe misses.
9. four-eyes promote to recommendation.
10. monitor/demote.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/feature-definitions` | List feature definition records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/feature-definitions` | Create one feature definition | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/feature-definitions/{id}` | Retire or soft-delete one feature definition | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/feature-definitions/{id}` | Get one feature definition | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/feature-definitions/{id}` | Update one feature definition | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/model-cards` | List registered intelligence use cases and current tier | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/model-cards/{id}` | Get model card, active versions, metrics, and review status | staff | 200 | 1200 ms | ≤25 | standard |
| `GET` | `/model-monitoring` | List model monitoring metric records | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/model-monitoring/{id}` | Get one model monitoring metric | staff | 200 | 1200 ms | ≤25 | standard |
| `GET` | `/model-versions` | List model version records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/model-versions` | Create one model version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `DELETE` | `/model-versions/{id}` | Retire or soft-delete one model version | staff | 204 | 1800 ms | ≤22 | If-Match |
| `GET` | `/model-versions/{id}` | Get one model version | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/model-versions/{id}` | Update one model version | staff | 200 | 1800 ms | ≤22 | If-Match |
| `POST` | `/model-versions/{id}/demote` | Demote/disable model and fall back to rules/manual queue | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/model-versions/{id}/evaluation` | Get chronological holdout, baseline, severe-miss and operational metrics | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/model-versions/{id}/promote` | Promote an evaluated model version after four-eyes approval | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `POST` | `/model-versions/{id}/retire` | Retire a model version and preserve reproducibility | staff | 201 | 1800 ms | ≤22 | If-Match, Idempotency-Key |
| `GET` | `/outcome-labels` | List outcome label records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/outcome-labels` | Create one outcome label | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/outcome-labels/{id}` | Get one outcome label | staff | 200 | 1200 ms | ≤25 | standard |
| `GET` | `/predictions` | List predictions | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/predictions/{id}` | Get one prediction | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/predictions/{id}/feedback` | Submit accepted/rejected/modified recommendation feedback | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `POST` | `/predictions/{id}/refresh` | Create a new immutable prediction using current active version | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/training-runs` | List training run records | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/training-runs` | Create one training run | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `GET` | `/training-runs/{id}` | Get one training run | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/training-runs/{id}/cancel` | Cancel checkpointed candidate training safely | staff | 200 | 1800 ms | ≤22 | If-Match, Idempotency-Key |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/feature-definitions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List feature definition records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "feature-definition",
      "id": "01K2FEATURED00000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Feature Definition"
      }
    }
  ],
  "links": {
    "self": "/api/v1/feature-definitions?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/feature-definitions?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM feature_definitions WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/feature-definitions`

**Purpose:** Create one feature definition

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "feature-definition",
    "attributes": {
      "state": "ACTIVE",
      "name": "Feature Definition"
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "feature-definition",
    "id": "01K2FEATURED00000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Feature Definition",
      "last_action": "FEATURE_DEFINITIONS",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM feature_definitions with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

No external data/model call; no protected/unneeded features; no high-impact model-only action; no free-form generated message; no auto-promotion; artifacts fail closed on checksum mismatch; AI disable leaves core usable.

### Performance and resource budget

Interactive inference target <300ms and bounded memory; batch scoring/training checkpointed and yields; web pages ≤1.6s; default sample gate ≥200 eligible and ≥30/class; routing gates as approved.

### Testing required

Point-in-time leakage, missing values, abstention boundary, explanation completeness, model disabled fallback, artifact tamper, severe miss, class imbalance, chronological metrics, promotion authorization, drift demotion.

### What success looks like

100% of surfaced predictions have version/confidence/reasons/feedback; insufficient data stays rules/observation; disabling AI does not block CRM; candidates never promote automatically or perform prohibited actions.

### Required deliverables

Intelligence frontend/backend/API; feature/model registries; rule/classifier artifacts; evaluation reports; governance/incident runbook; UAT-13.


---

## S36 — Build monitoring, capacity controls and incident operations

**Phase:** Phase 8 — Production hardening

**Objective:** Detect stale jobs, mailbox failures, capacity pressure, security/data/model incidents and guide recovery from inside cPanel.

**Why this step exists:** No external monitoring is permitted; green must be based on recent evidence, not merely absence of errors.

**Prerequisites:** All commands/modules emit metrics; S03 health; S26 command runs.

### What to build in the frontend

Complete privileged health, capacity, commands, incidents and support-bundle screens with trend, threshold, owner, evidence and degradation state.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Admin | `/admin/health` | Operations health | Inspect dependency freshness, capacity, commands, mail and queues. | 1500 ms | ≤24 | ≤950 KB |
| Admin | `/admin/incidents` | System incidents | Manage operational, security, data, mail, automation and model incidents. | 1500 ms | ≤24 | ≤950 KB |

### How to build the frontend


#### `/admin/health` — Operations health

- **Purpose:** Inspect dependency freshness, capacity, commands, mail and queues.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET /organizations/{id}/health; health snapshots; refresh/override
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

#### `/admin/incidents` — System incidents

- **Purpose:** Manage operational, security, data, mail, automation and model incidents.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET/POST/PATCH incidents; support bundles
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement metric collection, freshness classification, threshold-to-incident, capacity projection, degradation order/feature disable, incident lifecycle/timeline, sanitized support bundle and internal management/security notifications.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| operations | `SystemMetricService` | Collect queue depth/age, mailbox, DB/file/inode, error, command, backup and release metrics. | system_metrics, command_runs |
| operations | `SystemHealthService` | Classify healthy/degraded/unavailable from fresh evidence and threshold trends. | system_metrics, system_incidents |
| operations | `IncidentService` | Declare, own, contain, communicate, resolve and review operational/security/model incidents. | system_incidents, incident_events |
| operations | `CapacityService` | Measure/project database tables/indexes, storage/inodes, queue and mail; disable nonessential work by order. | system_metrics, retention_runs, feature_flags |
| operations | `SupportBundleService` | Create sanitized release/health/queue/config/recent-error bundle without secrets/full customer content. | system_metrics, releases, command_runs |

### How to build the backend services


#### `SystemMetricService`

- **Responsibility:** Collect queue depth/age, mailbox, DB/file/inode, error, command, backup and release metrics.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** system_metrics, command_runs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SystemHealthService`

- **Responsibility:** Classify healthy/degraded/unavailable from fresh evidence and threshold trends.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** system_metrics, system_incidents
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `IncidentService`

- **Responsibility:** Declare, own, contain, communicate, resolve and review operational/security/model incidents.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** system_incidents, incident_events
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `CapacityService`

- **Responsibility:** Measure/project database tables/indexes, storage/inodes, queue and mail; disable nonessential work by order.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** system_metrics, retention_runs, feature_flags
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `SupportBundleService`

- **Responsibility:** Create sanitized release/health/queue/config/recent-error bundle without secrets/full customer content.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** system_metrics, releases, command_runs
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Finalize system_metrics, system_incidents/events and command_runs; indexes by metric/time, incident state/severity/owner.

### Ordered implementation procedure

1. Define health contracts/thresholds.
2. collect each Cron heartbeat.
3. measure queue/mail/DB/files/inodes/errors/backups/release.
4. classify stale/degraded/unavailable.
5. create/dedupe incidents.
6. apply degradation order.
7. provide repair links.
8. build support bundle.
9. run tabletop scenarios.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/incidents` | List incidents | staff | 200 | 1500 ms | ≤18 | standard |
| `POST` | `/incidents` | Create a system incident | staff | 201 | 1800 ms | ≤22 | Idempotency-Key |
| `GET` | `/incidents/{id}` | Get one system incident | staff | 200 | 1200 ms | ≤25 | standard |
| `PATCH` | `/incidents/{id}` | Patch one system incident | staff | 200 | 1800 ms | ≤22 | If-Match |
| `GET` | `/operations/capacity` | Get database, files, inodes, process and queue capacity projection | staff | 200 | 1200 ms | ≤15 | standard |
| `GET` | `/operations/commands` | List management-command heartbeats and results | staff | 200 | 1500 ms | ≤15 | standard |
| `GET` | `/operations/health` | Get privileged dependency, queue, capacity, mail, and backup health | staff | 200 | 1200 ms | ≤15 | standard |
| `POST` | `/operations/incidents` | Create/declare an operational or security incident | staff | 201 | 1800 ms | ≤15 | Idempotency-Key |
| `GET` | `/operations/metrics` | List bounded system health metrics | staff | 200 | 1200 ms | ≤15 | standard |
| `POST` | `/operations/support-bundles` | Queue a sanitized internal support bundle | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/incidents?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List incidents

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "incident",
      "id": "01K2INCIDENT00000000000000",
      "version": 7,
      "attributes": {
        "severity": "P1",
        "state": "OPEN",
        "category": "MAILBOX_OUTAGE",
        "owner_id": "01K2USER0000000000000000001",
        "started_at": "2026-07-14T08:00:00Z"
      }
    }
  ],
  "links": {
    "self": "/api/v1/incidents?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/incidents?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM system_incidents WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, severity, owner_id, started_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/incidents`

**Purpose:** Create a system incident

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "incident",
    "attributes": {
      "severity": "P1",
      "state": "OPEN",
      "category": "MAILBOX_OUTAGE",
      "owner_id": "01K2USER0000000000000000001",
      "started_at": "2026-07-14T08:00:00Z"
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "incident",
    "id": "01K2INCIDENT00000000000000",
    "version": 8,
    "attributes": {
      "severity": "P1",
      "state": "OPEN",
      "category": "MAILBOX_OUTAGE",
      "owner_id": "01K2USER0000000000000000001",
      "started_at": "2026-07-14T08:00:00Z",
      "last_action": "INCIDENTS",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **22 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM system_incidents with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id); INDEX(state, severity, owner_id, started_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤22 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Detailed diagnostics privileged/redacted; no secrets/full content in support bundle; incident access restricted; feature degradation never bypasses security/consent or silently drops service work.

### Performance and resource budget

Health page p95 ≤1.2s and ≤15 queries from recent metrics; synthetic critical incident visible within one monitoring interval; metric retention bounded.

### Testing required

Stale heartbeat, mailbox outage, dead-letter surge, database threshold, inode warning, duplicate-send suspicion, compromised account, model incident, missing backup, support bundle redaction.

### What success looks like

Operations can identify what is unhealthy, since when, impact, owner and next action without shell access. Nonessential jobs stop before hard limits while core records/service communication remain prioritized.

### Required deliverables

Operations dashboards/API; metric collectors; incident engine/runbooks; capacity/degradation controls; support bundle; exercises.


---

## S37 — Build verified backups and timed restore drills

**Phase:** Phase 8 — Production hardening

**Objective:** Create recoverable backup sets and prove restoration rather than assuming files exist.

**Why this step exists:** A backup that cannot be read, matched to code/config or restored is not a backup. Same-provider limitations must be explicit.

**Prerequisites:** S34 archive/manifest; S42 release manifest scaffold; actual cPanel backup capabilities.

### What to build in the frontend

Build backup inventory, compatibility/verification detail, restore drill creation/progress/result and recovery checklist. Do not expose artifacts directly to unprivileged users.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Admin | `/admin/backups` | Backups and restore drills | Verify backup inventory and execute timed restore drills. | 1500 ms | ≤24 | ≤950 KB |

### How to build the frontend


#### `/admin/backups` — Backups and restore drills

- **Purpose:** Verify backup inventory and execute timed restore drills.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET /backups; verify; restore drills
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Implement selected logical DB export method, config/private-file/model/template/workflow/release manifests, checksums, free-space guard, verified retention, restore orchestration/checklist and reconciliation of counts/checksums/invariants/permissions.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| operations | `BackupService` | Create bounded logical backup + configuration/file/model/release manifests, verify before pruning. | backup_records, archive_manifests, releases |
| operations | `RestoreService` | Restore compatible set, verify checksums/counts/invariants/files/permissions and record RPO/RTO. | restore_drills, backup_records |

### How to build the backend services


#### `BackupService`

- **Responsibility:** Create bounded logical backup + configuration/file/model/release manifests, verify before pruning.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** backup_records, archive_manifests, releases
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `RestoreService`

- **Responsibility:** Restore compatible set, verify checksums/counts/invariants/files/permissions and record RPO/RTO.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** restore_drills, backup_records
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create backup_records and restore_drills; link release/config/schema/key versions and artifact manifests.

### Ordered implementation procedure

1. Select/test provider and application methods.
2. create bounded backup.
3. checksum/read contents.
4. record compatible inventory.
5. retain 7 daily/4 weekly/6 monthly where capacity permits.
6. never prune last verified set.
7. restore to staging/recovery.
8. intercept mail.
9. reconcile.
10. record RPO/RTO.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `GET` | `/backups` | List backup record records | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/backups/{id}` | Get one backup record | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/backups/{id}/verify` | Verify backup readability, checksum and compatible inventory | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `POST` | `/operations/backups` | Queue a verified logical backup | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `POST` | `/operations/restore-drills` | Queue a controlled restore drill against selected backup | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |
| `GET` | `/restore-drills` | List restore drill records | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/restore-drills/{id}` | Get one restore drill | staff | 200 | 1200 ms | ≤25 | standard |
| `POST` | `/restore-drills/{id}/start` | Start a timed controlled restore drill | staff | 202 | 1200 ms | ≤12 | Idempotency-Key, 202 job |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/backups?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at`

**Purpose:** List backup record records

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": [
    {
      "type": "backup",
      "id": "01K2BACKUP0000000000000000",
      "version": 7,
      "attributes": {
        "state": "ACTIVE",
        "name": "Backup"
      }
    }
  ],
  "links": {
    "self": "/api/v1/backups?page[after]=01K2CURSOR0000000000000000&page[size]=25&sort=-updated_at",
    "next": "/api/v1/backups?page[after]=01K2NEXT00000000000000000&page[size]=25"
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "page_size": 25,
    "has_more": true
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1500 ms**; p99 ≤ **3200 ms** under the representative mixed workload.

- Maximum **18 SQL statements**, request **16 KB**, response **512 KB**, page size **100**.

- Query shape: SELECT allowlisted list columns FROM backups WHERE actor_scope_predicate AND active_predicate AND (updated_at, public_id) < (?, ?) ORDER BY updated_at DESC, public_id DESC LIMIT 26; batch-load only requested allowlisted relationships.

- Required indexes: UNIQUE(public_id); INDEX(state, updated_at, public_id); INDEX(updated_at, public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1500 ms and p99 ≤3200 ms on the representative mixed workload, uses ≤18 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/backups/{id}/verify`

**Purpose:** Verify backup readability, checksum and compatible inventory

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "command",
    "attributes": {
      "reason_code": "APPROVED_OPERATION",
      "comment": "Evidence reviewed.",
      "expected_version": 7
    }
  }
}
```

**Success:** `HTTP 202`

**Response body**

```json
{
  "data": {
    "type": "job",
    "id": "01K2JOB000000000000000001",
    "attributes": {
      "state": "QUEUED",
      "submitted_at": "2026-07-14T08:00:00Z",
      "status_url": "/api/v1/jobs/01K2JOB000000000000000001"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001"
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1200 ms**; p99 ≤ **2500 ms** under the representative mixed workload.

- Maximum **12 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM verifys with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1200 ms and p99 ≤2500 ms on the representative mixed workload, uses ≤12 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Artifacts restricted/checksummed; offline copy decision documented; secrets excluded or separately encrypted; keys backed up/versioned; suspected compromise rotates credentials after restore.

### Performance and resource budget

RPO ≤24h, targeted 6h critical delta after resource test; RTO ≤4 business hours after host/valid backup available; backup outside peak and aborts before space exhaustion.

### Testing required

Zero-byte/corrupt/tampered/incompatible set, missing file/key/config, interrupted backup, retention pruning, full restore, portal isolation, outbox interception/idempotency after restore.

### What success looks like

A selected set restores the application, customer history, files, permissions, jobs and configuration within measured target. Existence alone never shows verified status.

### Required deliverables

Backup/restore services/UI/API; Cron/runbooks; quarterly restore evidence; risk acceptance for correlated provider failure.


---

## S38 — Performance, capacity and soak hardening

**Phase:** Phase 8 — Production hardening

**Objective:** Prove the complete system meets response, query, memory, concurrency and Cron budgets at representative volume.

**Why this step exists:** Optimization by intuition misses N+1, unindexed filters, queue growth and shared-host contention.

**Prerequisites:** All features integrated; representative dataset generator; Truehost-compatible staging.

### What to build in the frontend

Instrument browser timings and page weight; simplify layouts/payloads, paginate, defer secondary fragments and ensure mobile performance. Do not add a heavy SPA/cache as a shortcut.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Add endpoint timers/query counts, EXPLAIN review, selector projections, indexes, aggregate refresh, bounded jobs, connection management and resource guards. Optimize only measured hot paths.

_No domain service is introduced in this step._

### How to build the backend services


### Database work

Load representative volumes from PRD, update statistics, verify table/index size and query plans. Add only justified composite indexes and archive old detail if needed.

### Ordered implementation procedure

1. Generate capacity data.
2. define mixed staff/portal/Cron workload.
3. baseline.
4. find slow/query-heavy endpoints.
5. fix N+1/select columns/indexes.
6. test 15 sessions.
7. stress 20.
8. run repeated Cron/mail/job soak.
9. measure memory/DB/inodes.
10. record safe failure/degradation.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

Performance changes cannot weaken authorization, CSRF, validation or audit. Test data synthetic; no production customer mail; rate limits remain enabled.

### Performance and resource budget

Routine list/detail p95 ≤2s/p99 ≤4s; mutation p95 ≤2.5s; portal/public p95 ≤2.5s; search ≤2s; 15 sessions <1% errors; memory ≤512MB; standard detail ≤25 queries, Customer 360 ≤35.

### Testing required

Endpoint percentiles/query count/page weight; mixed load with Cron; DB locks/slow queries; memory; 24h-equivalent soak; queue age; archive retrieval; safe 503/429/degradation.

### What success looks like

All budgets pass on production-equivalent engine/config; no unbounded trend, N+1 or resource-limit response at target; stress failure is controlled and recoverable.

### Required deliverables

Performance report by endpoint; query/index evidence; capacity projection; soak results; approved exceptions and regression tests.


---

## S39 — Security hardening and independent verification

**Phase:** Phase 8 — Production hardening

**Objective:** Verify the complete attack surface against the threat model and OWASP ASVS Level 2 baseline.

**Why this step exists:** Security cannot be inferred from framework choice or test coverage; authenticated and portal logic require adversarial review.

**Prerequisites:** Complete integrated application; threat model updated; test staging.

### What to build in the frontend

Review every public/staff/portal state, error, link, upload, download, export and administrative action for information leakage and safe recovery.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Harden HTTPS/host/cookies/CSRF/CSP/HSTS, authentication, authorization, token, upload, email, serialization, dependency, logging, encryption, audit, automation configuration and incident controls. Remove debug/test endpoints.

_No domain service is introduced in this step._

### How to build the backend services


### Database work

Review database privileges, sensitive field encryption where preflight supports, backup access and retention. Verify no secret/PII in logs or test data.

### Ordered implementation procedure

1. Update threat model.
2. map ASVS applicability.
3. run SAST/dependency/secret scans.
4. execute auth/session/IDOR/mass assignment/injection/XSS/CSRF/upload/export tests.
5. review automation/AI abuse.
6. independent authenticated penetration review.
7. remediate.
8. retest.
9. sign residual risk.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

No unresolved critical/high; medium requires owner/compensating control; break-glass and incident runbooks exercised; keys/secrets rotation documented.

### Performance and resource budget

Security controls remain enabled during load; rate-limit DB queries bounded; encryption/hash settings benchmarked to avoid self-DoS.

### Testing required

OWASP ASVS mapping; API Top 10 object/property/function/resource tests; CSP; token/redirect/SSRF absence; MIME; mail header; workflow code injection; model artifact; backup confidentiality.

### What success looks like

Independent reviewer cannot access another scope, execute injected content, bypass policy or extract secrets. Every finding has evidence and no critical/high remains.

### Required deliverables

Security verification report; ASVS matrix; penetration results/retest; threat model vFinal; incident exercises; go-live security sign-off.


---

## S40 — Accessibility, responsive and cross-browser acceptance

**Phase:** Phase 8 — Production hardening

**Objective:** Prove complete staff, portal and signed journeys meet WCAG 2.2 AA and supported browser behavior.

**Why this step exists:** Daily operational software fails when keyboard, zoom, mobile, errors or authentication exclude users.

**Prerequisites:** Complete frontend; production-like configuration/data.

### What to build in the frontend

Audit all critical journeys for semantics, landmarks, headings, labels, instructions, error summary, focus order/visibility/not-obscured, status messages, target size, no-color-only meaning, reflow and accessible authentication.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Ensure backend preserves user input, returns field and summary errors, provides stable focus targets and works without JavaScript for core operations. HTMX responses announce important updates appropriately.

_No domain service is introduced in this step._

### How to build the backend services


### Database work

No schema changes except accessibility preferences if approved.

### Ordered implementation procedure

1. Define journey matrix.
2. run automated scan.
3. keyboard-only.
4. 200% zoom/360px.
5. screen-reader spot checks.
6. Chrome/Edge/Firefox/Safari current/previous.
7. JS-off fallback.
8. fix.
9. repeat full processes.
10. document minor approved variances.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

Accessible authentication must not weaken MFA/security; error messages non-disclosing; timeouts warn/allow extension where safe.

### Performance and resource budget

Critical pages remain within page-weight/latency target at 360px and zoom; no performance-heavy accessibility overlay.

### Testing required

Login/MFA/reset, lead, Customer 360, task, quote approval, ticket, survey, portal upload, automation simulation, export, errors/conflicts.

### What success looks like

No unresolved critical/serious barrier; all critical tasks keyboard-operable; no lost function at 360px/200% zoom; supported browsers pass core journeys.

### Required deliverables

Accessibility report; browser/responsive matrix; component fixes; role guides; WCAG evidence for production acceptance.


---

## S41 — Execute data migration dry runs, reconciliation and cutover readiness

**Phase:** Phase 8 — Production hardening

**Objective:** Move all authoritative legacy data into canonical structures without guessing, duplication or unintended automation.

**Why this step exists:** The best code fails if spreadsheets/mail/files are incompletely or incorrectly migrated.

**Prerequisites:** S34 import tools; source inventory/mappings; full configuration; business owners.

### What to build in the frontend

Use import/reconciliation UI and customer/duplicate review. Add no one-off browser-only migration behavior.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Create versioned migration scripts/adapters using the same domain services or explicit migration services, with source keys, checkpoints, rejects, repair and rollback reports. Import mail/file evidence within storage policy.

_No domain service is introduced in this step._

### How to build the backend services


### Database work

Load copy-sized staging, preserve provenance and old IDs, resolve duplicates and map statuses/reasons/owners. Keep records quarantined and automation disabled until signed release.

### Ordered implementation procedure

1. Inventory sources.
2. freeze data dictionary.
3. normalize/flag ambiguity.
4. dry-run identity clusters.
5. load staging.
6. reconcile counts/sums/status/owners/files/timelines.
7. repeat idempotently.
8. rehearse freeze/delta/rollback.
9. sign mappings.
10. prepare production runbook.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

Synthetic/anonymized staging where possible; migration files private/short retention; no outbound customer effects; high-risk merges approved; privacy/retention applied.

### Performance and resource budget

Production migration fits maintenance window and DB/storage safety reserve; chunked/checkpointed; no long locks; projected final DB below critical/block threshold.

### Testing required

Repeat run, interrupt/resume, duplicate source key, malformed row, missing owner, ambiguous status, files/checksums, timeline samples, no outbox/workflow, rollback repair.

### What success looks like

Two dry runs reconcile within approved tolerance, all rejects have disposition, production duration/space is known, and business owners can sample complete customer histories.

### Required deliverables

Migration scripts/mappings; reconciliation reports; cutover timing; freeze/delta/rollback plan; data-owner sign-off.


---

## S42 — Deploy, migrate, cut over and activate production in controlled stages

**Phase:** Phase 8 — Production hardening

**Objective:** Move the reviewed release to Truehost with verified backup, rollback and customer-effect interception.

**Why this step exists:** A successful build can still fail through deployment order, incompatible migration, mail activation or resource spikes.

**Prerequisites:** All acceptance evidence; restore pass; no critical/high defects; signed go-live.

### What to build in the frontend

Enable maintenance/read-only states, verify local static assets, branded notices and build identifier. Use test records/mailboxes for smoke tests.

| Audience | Route | Screen | Primary outcome | p95 | SQL | Page budget |
|---|---|---|---|---:|---:|---:|
| Admin | `/admin/releases` | Releases and maintenance | Review build/config/migration compatibility and maintenance state. | 1500 ms | ≤24 | ≤950 KB |

### How to build the frontend


#### `/admin/releases` — Releases and maintenance

- **Purpose:** Review build/config/migration compatibility and maintenance state.
- **Components:** AdminHeader; FilterTable; VersionDiff; EvidenceDrawer; ApprovalDialog; AuditTrail
- **API/data:** GET /releases; GET current release; maintenance controls
- **Server query:** Use permission-scoped selector; select only visible fields; select_related current owner/state; prefetch only bounded visible child sets; cursor paginate unbounded lists.
- **Mutations:** Use exact administrative command endpoints
- **State handling:** Skeleton or progress indicator for HTMX fragments; explicit empty state with next permitted action; field-level and summary validation; branded non-disclosing error with correlation ID; 412 conflict view shows changed fields and safe refresh/reapply.
- **Authorization:** Explicit privileged capability; step-up/four-eyes for high risk
- **Accessibility:** Semantic landmarks/headings; keyboard-first; visible focus; status text plus icon; error summary; 200% zoom and 360px reflow; no drag-only interaction; live regions only for important async state.
- **Screen budget:** p95 ≤1500 ms, ≤24 SQL, ≤950 KB compressed.
- **Success:** Authorized user completes the primary journey without hidden data or mouse-only steps; unauthorized objects/counts never appear; server p95 ≤1500 ms, SQL count ≤24, compressed transfer ≤950 KB; empty, invalid, conflict and dependency-failure states are useful.

### What to build in the backend

Create immutable release artifact/manifest, install locked dependencies, run deploy checks, acquire deployment lock, run migrations once, collect static, import config, restart Passenger, smoke and resume Cron/automation by priority.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| operations | `ReleaseService` | Record immutable release ID/commit/dependencies/migrations/config, deploy under lock and verify build. | releases, command_leases |
| operations | `MaintenanceService` | Block incompatible writes/public intake and present safe notice during migration/recovery. | feature_flags, system_incidents |

### How to build the backend services


#### `ReleaseService`

- **Responsibility:** Record immutable release ID/commit/dependencies/migrations/config, deploy under lock and verify build.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** releases, command_leases
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

#### `MaintenanceService`

- **Responsibility:** Block incompatible writes/public intake and present safe notice during migration/recovery.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** feature_flags, system_incidents
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Create verified predeploy backup; measure/execute migrations; load production configuration and quarantined migration; reconcile before release.

### Ordered implementation procedure

1. T-7 freeze/config/training.
2. T-1 final plan/owners.
3. backup/verify.
4. pause nonessential Cron/automation.
5. maintenance.
6. deploy artifact/hash-lock.
7. checks/migrations/static/config.
8. restart/build verify.
9. smoke with intercepted effects.
10. read-only review.
11. enable writes/IMAP/service mail.
12. activate approved workflows in small batches.
13. monitor/hypercare.

### APIs and endpoints introduced in this step

| Method | Path | Purpose | Auth | Success | p95 | SQL budget | Concurrency / replay |
|---|---|---|---|---:|---:|---:|---|
| `POST` | `/operations/maintenance/disable` | Disable maintenance after compatibility and smoke checks | staff | 201 | 1800 ms | ≤15 | Idempotency-Key |
| `POST` | `/operations/maintenance/enable` | Enable governed maintenance mode and block incompatible writes | staff | 201 | 1800 ms | ≤15 | Idempotency-Key |
| `GET` | `/operations/releases/current` | Get build, migration, and configuration compatibility status | staff | 200 | 1200 ms | ≤15 | standard |
| `GET` | `/releases` | List release manifest records | staff | 200 | 1500 ms | ≤18 | standard |
| `GET` | `/releases/{id}` | Get one release manifest | staff | 200 | 1200 ms | ≤25 | standard |

### Exact representative API wire contracts

The following contracts demonstrate both a read/list and a mutation/command where available. Every endpoint—including its exact example, required headers, performance, SQL plan, indexes, cache policy and errors—is specified in `api_endpoint_implementation_matrix.csv` and `internal_crm_openapi_v2.yaml`.

#### `GET /api/v1/operations/releases/current`

**Purpose:** Get build, migration, and configuration compatibility status

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
```

**Success:** `HTTP 200`

**Response body**

```json
{
  "data": {
    "type": "current",
    "id": "01K2CURRENT000000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Current"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1200 ms**; p99 ≤ **2800 ms** under the representative mixed workload.

- Maximum **15 SQL statements**, request **16 KB**, response **512 KB**.

- Query shape: SELECT the authorized current by public_id with actor scope in the same query; join current owner/state only; prefetch bounded child collections requested by include; return 404 before unrestricted data is materialized.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1200 ms and p99 ≤2800 ms on the representative mixed workload, uses ≤15 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect.

#### `POST /api/v1/operations/maintenance/disable`

**Purpose:** Disable maintenance after compatibility and smoke checks

**Required headers**

```http
Accept: application/json
X-Correlation-ID: <ULID>
Cookie: sessionid=<opaque>
X-CSRFToken: <token>
Idempotency-Key: <UUID>
Content-Type: application/json
```

**Request body**

```json
{
  "data": {
    "type": "disable",
    "attributes": {
      "state": "ACTIVE",
      "name": "Disable"
    }
  }
}
```

**Success:** `HTTP 201`

**Response body**

```json
{
  "data": {
    "type": "disable",
    "id": "01K2DISABLE000000000000000",
    "version": 8,
    "attributes": {
      "state": "ACTIVE",
      "name": "Disable",
      "last_action": "DISABLE",
      "updated_at": "2026-07-14T08:00:01Z"
    }
  },
  "meta": {
    "request_id": "01K2REQ0000000000000000001",
    "correlation_id": "01K2CORR00000000000000001",
    "domain_event_ids": [
      "01K2EVENT00000000000000001"
    ]
  }
}
```

**Performance and data-access contract**

- p95 ≤ **1800 ms**; p99 ≤ **3500 ms** under the representative mixed workload.

- Maximum **15 SQL statements**, request **1024 KB**, response **512 KB**.

- Query shape: BEGIN; SELECT target rows FROM disables with actor scope and FOR UPDATE when concurrency matters; verify If-Match/idempotency/capability/state/policy; write current state, append-only history, audit and domain event/outbox intent; COMMIT before any external effect.

- Required indexes: UNIQUE(public_id)

- Cache: `private, no-store`.

- Expected errors: 400 malformed; 401 unauthenticated; 403 forbidden; 404 not visible/not found; 409 state/uniqueness/idempotency conflict; 413 payload/content too large; 422 validation/policy; 429 rate limit/resource guard; 503 dependency/resource degraded.

- Acceptance: Authorized request meets p95 ≤1800 ms and p99 ≤3500 ms on the representative mixed workload, uses ≤15 SQL statements, respects the request/response/page bounds, and preserves authorization before loading data. The stated domain transition/result is persisted with audit and correlation evidence; negative, stale, duplicate-event and resource-degradation cases fail safely without record/count leakage or uncontrolled customer effect. Reusing the same key and identical request returns the original logical result; key reuse with different content returns 409.

### Security controls

Exact hosts/HTTPS; staging mail interception; no production smoke customer effect; secret/config separation; rollback on authorization/data/duplicate-send/resource/mail defects.

### Performance and resource budget

Observe web percentiles, 500/503/508, process/entry/memory, DB growth, queue/mail age and error rate. No activation batch exceeds mail/job capacity.

### Testing required

Exact deployment and rollback rehearsal; migration/invariant; login/MFA; customer/search; portal isolation; file; task/job lease; intercepted mail; health/build; rollback triggers.

### What success looks like

Production shows expected build/config/schema; records reconcile; smoke passes; queues/mail/resource remain healthy; no real customer effect occurs until explicitly approved activation.

### Required deliverables

Release package/manifest; deployment log; smoke/reconciliation; go/no-go; rollback package; cutover communications; hypercare ownership.


---

## S43 — Operate, patch, improve and prove reliability continuously

**Phase:** Phase 9 — Production operations

**Objective:** Keep production secure, within capacity and aligned with company processes after launch.

**Why this step exists:** Production quality decays without ownership, drills, patching, metric review, feedback and controlled changes.

**Prerequisites:** Successful S42 cutover; trained administrators/process owners.

### What to build in the frontend

Maintain role-specific guides, contextual help, release notes and visible system health. UX changes follow the same accessibility/performance review.

_No end-user screen is delivered in this step._

### How to build the frontend


This step is architecture, infrastructure, test or operations work; it deliberately introduces no customer-facing screen. Any temporary diagnostic UI is removed before release.

### What to build in the backend

Run staggered commands, incident/backup/restore/security/model reviews, dependency patches, release/change control, housekeeping, archive, data quality and invariant repairs. Add features only through PRD/ADR/traceability.

| Domain | Service | Responsibility | Principal persistence |
|---|---|---|---|
| operations | `HousekeepingService` | Clean expired temp/exports/sessions/logs/staging packages under manifest/path safety. | file_assets, export_jobs, user_sessions, archive_manifests |

### How to build the backend services


#### `HousekeepingService`

- **Responsibility:** Clean expired temp/exports/sessions/logs/staging packages under manifest/path safety.
- **Inputs:** Validated command + actor context + expected version
- **Outputs:** Typed result + changed public ID/version + domain event IDs + correlation ID
- **Persistence:** file_assets, export_jobs, user_sessions, archive_manifests
- **Transaction:** Owns one short transaction for current state, append-only history, audit and durable event/outbox intent.
- **Events/jobs:** Emits typed domain events; schedules bounded jobs only after durable intent exists.
- **Authorization:** Calls central capability, record-scope, field and contextual policy before mutation or disclosure.
- **Failure behavior:** Raises typed validation/policy/conflict errors; rolls back atomically; classifies retryable external work; never hides partial results.
- **Tests:** Unit boundary/invalid cases; MySQL/MariaDB integration; authorization; concurrency/idempotency; failure injection.
- **Success:** One authoritative implementation path is shared by HTML, API, imports and jobs; invariants cannot be bypassed; evidence is reproducible.

### Database work

Monitor table/index growth, retention/archives, integrity, backup inventory and model/event history. Perform controlled schema evolution.

### Ordered implementation procedure

1. Daily: queues/mail/dead letters/capacity/action coverage. Weekly: KPI/data quality/workflows/security/model review. Monthly: capacity/archive/permissions/patches. Quarterly: restore/break-glass/incident/access review. Each release: backup, security, migration, smoke, rollback evidence.

### APIs and endpoints introduced in this step

_No new HTTP endpoint is introduced in this step; the step establishes infrastructure or validates the complete system._

### Security controls

MFA/access review, least privilege, patch SLA, key/secret rotation, incident exercises, audit verification and no unsupported dependencies.

### Performance and resource budget

Track p95/p99/query/memory/page weight/queue age/mail rate/DB/inodes against thresholds; re-test after material data/hosting/runtime change.

### Testing required

Production checks, incident tabletop, restore, security regression, workflow simulation, model drift, permission recertification, archived retrieval and trained-admin runbook rehearsal.

### What success looks like

No P0 job is unacknowledged >1 business day; action coverage ≥95%; backups/restores verified; security patches timely; capacity has reserve; changes remain traceable/reversible.

### Required deliverables

Operations calendar; daily/weekly/monthly/quarterly checklists; patch/release process; incident/postmortem; KPI/model reviews; continuous acceptance register.


---

# 10. Production deployment and operations baseline

## 10.1 Truehost account layout

```text
/home/<cpanel-user>/
├── apps/
│   ├── crm-production/current/
│   └── crm-staging/current/
├── private/
│   ├── production/
│   │   ├── attachments/
│   │   ├── email/
│   │   ├── generated/
│   │   ├── exports/
│   │   ├── archives/
│   │   ├── models/
│   │   ├── backups/
│   │   ├── logs/
│   │   └── temp/
│   └── staging/
└── public_html/
    └── crm-static/                 # collected fingerprinted assets only
```

## 10.2 Staggered production commands

```text
Every 5 minutes at offset :00  sync_inbound_email   ≤25 messages / 35 seconds
Every 5 minutes at offset :01  send_outbox          ≤10 messages / 35 seconds
Every 5 minutes at offset :02  run_due_jobs         ≤50 jobs / 40 seconds
Every 15 minutes at :04        check_sla_and_invariants
Hourly at :11                  refresh_operational_aggregates
Every 6 hours at :23           export_critical_delta, only after resource validation
Nightly 01:17                  create_verified_backup
Nightly 02:13                  refresh_health_and_scores
Nightly 03:29                  archive_and_housekeep
Weekly Sunday 04:37            evaluate_model_candidates, skip under warning
Weekly Monday 06:07            send_management_digest
Monthly day 2 05:19            verify_archives_and_capacity
```

Each command uses an absolute virtual-environment path, a database lease, a duration/item bound, a checkpoint and a durable command-run result. Cron output is redirected to controlled logs rather than generating frequent mailbox messages.

## 10.3 Capacity guardrails

| Resource | Green / warning / critical action |
|---|---|
| Enabled staff | Hard operational ceiling 11 |
| Active sessions | Test 15; stress 20 to prove safe degradation |
| Database | Warning 250 MB; high 300 MB; critical 340 MB; schema-heavy release block 360–375 MB after actual-engine measurement; provider hard maximum remains external |
| Process memory | Normal target ≤512 MB; provider ceiling is not a working target |
| Private storage | Keep at least 8 GB free; default upload 5 MB, exceptional 20 MB by policy |
| Inodes | Warn 180,000; critical 220,000; archive/cleanup before provider soft limit |
| Email | ≤60/hour and ≤10/five minutes; no arbitrary mass send |
| Workflow | ≤100 definitions, ≤50 active, ≤30 steps, acyclic, ≤5 nested enrolments |
| Cron | ≤50 due jobs/40 seconds; IMAP ≤25/35 seconds; outbox ≤10/35 seconds |

## 10.4 Release sequence

1. Approve release manifest, dependencies, migration/config diff, backup and rollback owner.
2. Deploy to dormant staging and execute the exact deployment and rollback rehearsal.
3. Verify a compatible production backup.
4. Pause nonessential Cron and workflow activation; enable maintenance where schema incompatibility requires it.
5. Transfer the reviewed release and install hash-locked dependencies.
6. Run production checks and acquire deployment lock.
7. Apply migrations once, collect static assets and import approved configuration.
8. Restart Passenger and verify build/config/schema identifiers.
9. Run login/MFA, customer, search, portal isolation, file, task/job, intercepted mail and health smoke tests.
10. Resume writes, IMAP, critical service mail and approved workflow batches in that order.
11. Observe error/resource/queue/mail/database metrics and close or roll back.

## 10.5 Immediate rollback triggers

- confirmed staff/portal authorization leakage;
- confirmed duplicate customer message or inability to reconcile ambiguous delivery safely;
- migration corruption or material unreconciled data loss;
- sustained 500/503/508 or account resource exhaustion caused by the release;
- duplicated/lost/materially misthreaded inbound mail;
- exposed secret or critical security defect;
- runaway queue/dead-letter growth affecting service obligations;
- backup incompatibility discovered before full activation.

---

# 11. Final production completion gates

The platform is complete only when all of the following are true:

1. The actual Truehost account passes the signed compatibility preflight.
2. Every mandatory PRD requirement maps to design, code/configuration, tests and release evidence.
3. All frontend routes and backend services in the companion matrices are implemented or explicitly replaced by an approved equivalent.
4. Every endpoint contract, authorization case, performance budget and error path passes.
5. All 28 workflows pass positive, stop, duplicate-event, retry/dead-letter and permission tests and have approved owners/templates/rollback.
6. SMTP ambiguous handoff, reply stop and no-silent-duplicate tests pass.
7. Portal IDOR tests pass for every object, file, message, count and mutation.
8. Migration is repeatable, reconciled and cannot trigger unapproved communication.
9. Performance, soak, capacity, accessibility and browser gates pass on production-equivalent configuration.
10. No critical/high security finding or release-blocking defect remains.
11. A compatible backup has been restored and reconciled within the measured target.
12. Staff roles, MFA, ownership, delegation, training, runbooks and incident coverage are complete.
13. Business, product, technical, security/privacy, data, quality and process owners sign the production acceptance record.

# 12. Boundary limitations that code cannot remove

- The application cannot remain available when the one Truehost account, provider, DNS or database is unavailable.
- A monitor inside the same account cannot independently detect a provider-wide outage.
- Backups in the same provider failure domain are correlated; an off-provider encrypted copy is the only way to materially reduce that risk, but it is outside the stated runtime boundary and needs a governance decision.
- No external malware scanner exists under the boundary; strict file-type prohibition and safe serving reduce but do not eliminate malicious-file risk.
- WhatsApp, SMS, telephone and social automation require external providers and therefore remain staff-assisted tasks/logs.
- ChatGPT-class generation is not dependable on this plan; controlled templates and local explainable models are the production-safe design.

The result can be exceptionally dependable for this company, but no honest architecture can promise that software never fails or that a single shared-host failure domain is infinitely scalable. The correct production standard is bounded failure, no silent data loss, no silent unauthorized disclosure, no uncontrolled automation, clear diagnosis and verified recovery.
