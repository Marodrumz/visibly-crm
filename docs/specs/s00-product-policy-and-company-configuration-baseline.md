# S00 Product, Policy, and Company Configuration Baseline

Date: 2026-07-15
Owner: Oghenemaro
Approval evidence: Oghenemaro approved the PRD implementation, assigned Oghenemaro to all S00 owner roles, and approved implementation effective 2026-07-15 in the active Codex conversation.

This document freezes the S00 governance baseline. It does not create runtime configuration, product code, database migrations, customer-facing UI, or customer effects.

## Source Precedence

When sources conflict, apply this order:

1. Approved PRD.
2. Implementation manual.
3. OpenAPI and DBML/data contracts.
4. Matrices and registers.
5. Accepted ADRs.
6. Code and migrations.

Conflicts that affect business policy, architecture, security, privacy, data, API, capacity, or customer communication must stop implementation until Oghenemaro records a decision.

## Owner Register

| Role | Named owner | Authority |
|---|---|---|
| Business owner / sponsor | Oghenemaro | Product policy, process ownership, budget, risk acceptance, go-live, legal entity, retention policy, communication policy, escalation owners. |
| Product owner | Oghenemaro | Requirements, defect priority, workflow acceptance, field dictionaries, KPI definitions, UAT acceptance. |
| Technical owner | Oghenemaro | Architecture, deployment, data integrity, dependency compatibility, release procedure, backup/restore, capacity thresholds. |
| Security owner | Oghenemaro | Security model, threat model, ASVS posture, incident severity, security acceptance, privileged-operation review. |
| Privacy / data protection owner | Oghenemaro | Lawful purpose, consent, access, retention, legal hold, exports, deletion/privacy cases. |
| Sales process owner | Oghenemaro | Lead, opportunity, quote, sales SLA, commercial handoff, sales templates. |
| Onboarding process owner | Oghenemaro | Onboarding templates, milestones, blockers, customer inputs, completion criteria. |
| Support process owner | Oghenemaro | Ticket categories, impact/urgency, SLA, escalation, closure/reopen, knowledge. |
| Customer success process owner | Oghenemaro | Health model, renewal, churn, win-back, advocacy, review cadence. |
| Operations owner | Oghenemaro | Cron, health, capacity, release, backup, restore, incident response, housekeeping. |
| Audit/compliance owner | Oghenemaro | Acceptance evidence, audit-chain review, release evidence retention, waiver records. |

## Configuration Decision Register

Decision status values:

- Approved: S00 freezes the decision.
- Deferred: the decision is owned and has a gate; no implementation may proceed past the gate without a value.
- Blocked: a conflict or missing approval prevents work.

| Decision area | S00 disposition | Owner | Gate/deadline |
|---|---|---|---|
| Company identity | Deferred: legal/display name, production domain, support contact, legal contact, and privacy notice owner are not present in repository evidence. | Oghenemaro | Before S03 environment configuration and S32 portal/public flows. |
| Time and money | Deferred: company timezone, business hours, holiday calendar, base currency, allowed currencies, and exchange-rate process are not present in repository evidence. UTC storage and IANA display timezone remain approved architecture semantics. | Oghenemaro | Before S12 configuration and any SLA/reporting implementation. |
| Staff model | Approved boundary: one company and at most 11 enabled staff. Deferred values: actual staff list, teams, queues, managers, delegation, absence rules, and break-glass owner. | Oghenemaro | Before S07 identity and S09 authorization. |
| Customer model | Approved boundary: organization/contact records are canonical and permission-filtered. Deferred values: segments, required fields, custom fields, and restricted fields. | Oghenemaro | Before S14 customer records and S17 data governance. |
| Commercial process | Deferred: lead sources, qualification, pipelines, stages, products/services, quote terms, approval thresholds, and outcome reasons. | Oghenemaro | Before S19-S21. |
| Service process | Deferred: support categories, impact/urgency matrix, SLA windows, waiting policy, closure policy, reopen policy, and escalation. | Oghenemaro | Before S29. |
| Onboarding | Deferred: product-to-template mapping, milestones, customer inputs, target time-to-value, and completion criteria. | Oghenemaro | Before S28. |
| Success/renewal | Deferred: health dimensions/weights, risk bands, review cadence, renewal timing, churn reasons, and win-back policy. | Oghenemaro | Before S31. |
| Communication | Approved boundary: Truehost SMTP/IMAP only, low-volume relationship/service mail, no mass mailing, no arbitrary recipient lists. Deferred values: mailboxes, send identities, purposes, consent basis, quiet hours, template owners, signatures. | Oghenemaro | Before S15 and S22-S24. |
| Feedback | Deferred: survey scales, thresholds, fatigue rules, anonymity policy, recovery owner, reporting cohorts. | Oghenemaro | Before S30. |
| Data governance | Approved boundary: no attachment BLOBs, private files outside public root, soft delete before purge, legal hold precedence. Deferred values: migration sources, retention durations, privacy deadlines, export approval thresholds, and offline backup procedure. | Oghenemaro | Before S11, S33, S34, S37, and S41. |
| AI governance | Approved boundary: local explainable AI only, disableable, no external AI/LLM/vector DB/free-form generated customer text. Deferred values: use-case owners, initial rules, thresholds, severe classes, review cadence. | Oghenemaro | Before S35. |
| Offline encrypted backup | Approved as a non-runtime governance exception recommended for correlated provider-failure risk. Operational method remains deferred. | Oghenemaro | Before S37 and go-live acceptance. |

No deferred row grants permission to implement unsafe defaults. Dependent build steps must block until their required values are recorded.

## Canonical Data Semantics

| Topic | S00 baseline |
|---|---|
| Internal keys | Database tables use internal `BigAutoField` style integer keys where specified by DBML. |
| Public identifiers | Externally addressable resources expose 26-character ULID-style public IDs, never internal numeric IDs. |
| Record versions | Mutable records use optimistic concurrency through a record/row version. |
| Time | Store UTC timezone-aware datetimes internally. Display with approved IANA business timezone once supplied. |
| Money | Use `Decimal`, explicit currency, deterministic rounding, and an approved exchange-rate source. Currency must not be hard-coded. |
| Files | Store files outside public web roots; database stores metadata, checksums, ownership, retention class, and validation state only. |
| Email bodies | Store large/raw message bodies outside the database; store message metadata, hashes, threading identifiers, and safe summaries in DB rows. |
| History | Material state histories, consent evidence, approvals, audit events, predictions, outcomes, and timeline events are append-only. |
| Current state | Current-state projections may exist for queues and fast reads but must reconcile to append-only history. |
| Configuration | Configuration is versioned, validated, dependency-checked, simulated, reviewed, effective-dated, and rollback-capable. |

## Record Classes

| Class | Examples | Required controls |
|---|---|---|
| Identity/security | Users, sessions, MFA devices, invitations, auth events | Invitation-only staff, MFA, revocation, throttling, step-up, audit. |
| Customer core | Organizations, contacts, relationships, consent | Object authorization before list/count/search/detail/export/file, field policy, data quality. |
| Operational lifecycle | Leads, opportunities, onboarding cases, tickets, renewal/recovery plans | Exactly one accountable owner plus next action or approved wake-up date while active. |
| Commercial | Catalogue, opportunities, quotes, approvals, issue/delivery evidence | Versioned prices/terms, approval thresholds, optimistic concurrency, handoff completeness. |
| Communication | Mailboxes, templates, drafts, outbox, inbound messages, suppressions | Policy guard before send, idempotency, reply-aware stopping, no customer effect in request. |
| Workflow/job | Domain events, workflow runs, scheduled jobs, outbox attempts, dead letters | Durable intent, leases, bounded batches, idempotency keys, classified failure. |
| Governance/configuration | Roles, capabilities, configuration versions, feature flags, policies | Versioned changes, dependency impact, simulation, review, audit, rollback. |
| Reporting/export | Saved views, reports, export jobs, manifests | Permission-filtered aggregates, step-up/four-eyes where required, formula neutralization. |
| Local intelligence | Use cases, model versions, predictions, feature snapshots, feedback | Optional/disableable AI, explainable reasons, abstention, human review, artifact checksums. |

## Retention Classes

Retention durations are deferred to Oghenemaro, but these class names are frozen as the policy vocabulary:

| Retention class | Applies to | Baseline behavior |
|---|---|---|
| `identity_security` | Users, sessions, auth events, MFA evidence | Retain enough to support audit, security investigation, and account history. |
| `customer_operational` | Organizations, contacts, leads, opportunities, tasks, cases | Soft delete first; purge only under approved dependency/legal-hold process. |
| `communication_evidence` | Outbound/inbound message metadata, send evidence, consent/suppression | Retain immutable evidence needed to prove policy compliance and stop conditions. |
| `private_file` | Attachments, generated quote files, imports, exports, archives | Private storage, checksum manifest, expiry/purge controlled by policy. |
| `audit_tamper_evident` | Audit events and manifests | Append-only with verification; corrections use amendment events. |
| `configuration_history` | Configuration versions, roles, workflow definitions, templates, policies | Retire rather than delete; history remains interpretable. |
| `intelligence_artifact` | Model artifacts, predictions, feature snapshots, evaluation results | Immutable/checksummed; rollback-capable; demotion/retirement audited. |
| `temporary_processing` | Upload temp, import staging, export staging, generated temp | Bounded lifetime, manifest cleanup, no unsafe path traversal. |

## Preliminary Capacity and Storage Budget

These are internal guardrails for later implementation. Actual Truehost values must be measured in S01.

| Resource | Green / warning / critical / block posture |
|---|---|
| Enabled staff | Hard ceiling: 11 enabled staff. |
| Active sessions | Test 15 active sessions; stress 20 for safe degradation. |
| Database | Warn at 250 MB, high at 300 MB, critical at 340 MB, schema-heavy release block in the 360-375 MB range after actual-engine tests. PRD hard-ceiling risk remains 500 MB; no design may depend on reaching it. |
| Private storage | Keep at least 8 GB free. |
| Inodes | Warn at 180,000; critical at 220,000. |
| Uploads | Default 5 MB; exceptional 20 MB only by approved policy. |
| Mail | <=60/hour and <=10/five minutes; no mass mailing. |
| Cron | Due jobs <=50/40s; IMAP <=25/35s; outbox <=10/35s. |
| Standard detail queries | <=25 SQL statements unless matrix says otherwise. |
| Customer 360 queries | <=35 SQL statements with approved query-count evidence. |
| Normal compressed page | <=1.5 MB. |
| Process/job memory | Target <=512 MB steady state. |

## Domain Glossary

| Term | Meaning |
|---|---|
| Customer 360 | Unified customer record, timeline, consent, commercial history, support, onboarding, success, renewal, files, and risk context. |
| Accountable owner | Staff user responsible for the next operational action on an active record. |
| Next action | Explicit dated work item or approved wake-up that prevents silent drift. |
| Governed state | Lifecycle state that may change only through a transition service. |
| Domain event | Committed fact emitted after a business transaction commits. |
| Outbox intent | Durable row authorizing later external effect processing outside the HTTP request. |
| Dead letter | Owned terminal failure requiring review or repair. |
| Portal scope | Customer-visible scope derived only from server-side session or signed single-purpose token. |
| Restricted field | Field hidden or read-only except for explicitly authorized roles/contexts. |
| Policy guard | Final allow/deny decision before a sensitive, external, customer, privacy, or destructive effect. |
| Observation mode | AI/model mode that records recommendations without automatically changing business outcomes. |

## Content Vocabulary and Status Labels

General status vocabulary:

- Use explicit labels, not color alone.
- Prefer active verbs for actions and stable nouns for states.
- Every destructive or privacy-affecting action must state the impact and required reason.
- Internal-only, customer-visible, and portal-visible content must be persistently labeled.

Approved label families:

| Family | Labels |
|---|---|
| Draft lifecycle | Draft, In review, Active, Retired, Replaced. |
| Operational work | Open, In progress, Waiting for customer, Waiting for internal dependency, Blocked, Resolved, Closed, Reopened. |
| Risk/health | Healthy, Watch, At risk, Critical, Unknown, Abstained. |
| Approval | Requested, Approved, Rejected, Changes requested, Expired, Invalidated. |
| Delivery | Ready, Sending, Sent confirmed, Failed transient, Failed permanent, Delivery unknown, Policy canceled. |
| Job | Queued, Claimed, Running, Succeeded, Retry scheduled, Failed, Dead letter, Canceled. |
| Visibility | Internal, Customer-visible, Portal-visible, Restricted. |

## Accessibility Content Rules

- Every page and component introduced later must have semantic heading order, labels, visible focus, keyboard operation, error summaries, and field-level errors.
- Status must combine text/icon meaning with color.
- Long words and labels must fit at 360 CSS pixels and 200 percent zoom.
- Destructive actions must include effect text that remains available to screen readers.
- Loading, empty, invalid, conflict, dependency-failure, permission-denied, success, and retry states must be represented where applicable.
- User-visible text must avoid relying on tooltips alone for essential meaning.
- WCAG 2.2 AA is the acceptance target for applicable staff, portal, and signed-link journeys.

## Information Architecture

No frontend route is implemented in S00. The approved information architecture for later steps is:

```text
Operational home
  Work queue
  Approvals
  Tasks and activities

Customer 360
  Organizations
  Contacts
  Relationships
  Timeline
  Files
  Consent and preferences

Sales
  Leads
  Opportunities
  Catalogue
  Quotes

Messaging
  Mailboxes
  Templates
  Drafts
  Outbox
  Inbound review

Automation
  Events
  Workflow definitions
  Simulations
  Runs
  Dead letters

Service delivery
  Onboarding
  Support
  Feedback
  Customer success
  Renewal and recovery

Governance
  Configuration
  Roles and capabilities
  Audit
  Privacy and retention
  Imports and exports
  Local intelligence
  Reporting
  Operations

Customer portal
  Invitations
  Profile/preferences
  Requests
  Files
  Tickets/cases
  Feedback/signed forms
```

## Role Journey Maps

| Role | Daily journey | Stop conditions |
|---|---|---|
| Business/product owner | Review metrics, accept workflows, approve policy exceptions, prioritize defects, sign release evidence. | Critical/high security issue, unresolved policy ambiguity, failed acceptance evidence. |
| Sales owner | Review leads, qualification, opportunity stage evidence, quote approvals, next actions, stalled work. | Missing owner/next action, stale quote approval, DNC/complaint/severe support hold. |
| Onboarding owner | Monitor cases, milestones, blockers, customer requests, delay communications, completion evidence. | Missing milestone owner, blocker without action, customer input unsafe/missing, severe support issue. |
| Support owner | Triage tickets, SLA clocks, first response, waiting states, closure/reopen, incident escalation. | SLA breach risk, complaint, unresolved dependency, unsafe closure, privacy/legal hold. |
| Customer success owner | Review health, at-risk plans, renewals, churn signals, recovery actions, advocacy eligibility. | Active recovery, unresolved support, low feedback, consent suppression, commercial hold. |
| Security/privacy owner | Review access, exports, legal hold, privacy cases, security events, threat model changes. | Authorization leakage, exposed secret, unsafe file, unmet step-up/four-eyes requirement. |
| Operations owner | Review health, queues, Cron, mail age, DB/storage/inodes, backups, incidents, release readiness. | Resource criticality, stale backup, dead-letter surge, delivery ambiguity, rollback trigger. |

## Capability Catalogue

Capability risk classes:

- Low: read-only internal metadata with no sensitive values.
- Standard: normal CRM read/write within actor scope.
- Sensitive: customer data, restricted fields, communication, export, privacy, support, or workflow effects.
- Privileged: roles, configuration activation, approvals, retention, purge, merge, model promotion, release/operations.
- Break-glass: emergency access with reason, step-up, audit, and review.

| Capability family | Risk class | Examples | S00 control |
|---|---|---|---|
| Identity and session | Privileged | Invite staff, revoke sessions, require MFA, disable user | Default deny; S07-S09 implementation only. |
| Customer records | Sensitive | View/edit organizations, contacts, timeline, files | Authorization before list/count/search/detail/export/file. |
| Sales | Sensitive | Qualify lead, advance opportunity, approve quote | Governed transitions and approvals. |
| Messaging | Sensitive | Create draft, approve send, process replies | Final policy guard and outbox; no request-time send. |
| Automation | Privileged | Activate workflow, emergency stop, replay/dead letter | Simulation, immutable active versions, bounded jobs. |
| Support/onboarding/success | Sensitive | SLA, cases, recovery, renewal | Owner and next-action invariant. |
| Reporting/export | Privileged | Saved views, aggregates, export files | Permission-filtered aggregates, step-up/four-eyes. |
| Configuration | Privileged | Activate roles, policies, templates, reference data | Versioned, reviewed, effective-dated, rollback-capable. |
| Intelligence | Privileged | Promote/demote model, score records | Optional, explainable, observation first, human-governed. |
| Operations | Break-glass | Maintenance, backup/restore, rollback, purge | Reason, step-up, audit, owner review. |

## State-Machine Catalogue

| State machine | Baseline states | Required invariants |
|---|---|---|
| Configuration/versioned reference data | Draft, In review, Active, Retired, Replaced | Active versions immutable; activation records reviewer, effective time, checksum, dependency validation. |
| Lead | New, Triage, Contacting, Qualified, Nurture, Disqualified, Converted | Active states require owner and next action or approved wake-up. |
| Opportunity | Open, Discovery, Proposal, Approval, Won, Lost, Closed no-decision | Stage changes require reason/evidence and append-only history. |
| Quote | Draft, Approval requested, Approved, Issued, Delivered, Accepted, Rejected, Expired, Withdrawn | Material edit invalidates approval; one issued event per version. |
| Task | Open, Claimed, In progress, Waiting, Completed, Canceled, Reopened | Owner/queue and due date required until terminal. |
| Onboarding case | Planned, Active, Waiting for customer, Blocked, Completed, Canceled, Reopened | Milestones and blockers remain attributable. |
| Support ticket | New, Triage, In progress, Waiting for customer, Waiting internal, Resolved, Closed, Reopened | SLA clocks distinguish company time, customer wait, and total elapsed time. |
| Feedback recovery | New, Review, Recovery active, Waiting, Resolved, Closed | Low-score recovery has owner and target outcome. |
| Customer health/recovery | Healthy, Watch, At risk, Critical, Recovery active, Resolved | Severe support/recovery outranks commercial automation. |
| Outbox message | Ready, Claimed, Sending, Sent confirmed, Failed transient, Failed permanent, Delivery unknown, Policy canceled | Delivery unknown is never blindly retried. |
| Workflow run/job | Queued, Claimed, Running, Waiting, Succeeded, Retry scheduled, Failed permanent, Dead letter, Canceled | Lease, checkpoint, idempotency, and bounded execution required. |
| AI use case/model | Registered, Feature review, Observation, Recommendation, Restricted routing, Demoted, Retired | No auto-promotion; low confidence abstains; core CRM works with AI disabled. |

## Event Catalogue

Event naming pattern:

```text
<domain>.<subject>.<fact>.<version>
```

Examples:

| Event family | Example event | Notes |
|---|---|---|
| Identity | `accounts.user_invited.v1`, `accounts.session_revoked.v1` | Security events must be audit-linked. |
| Governance | `governance.configuration_activated.v1`, `governance.role_version_activated.v1` | Active configuration remains immutable. |
| Customer | `crm.organization_created.v1`, `crm.contact_preference_changed.v1` | Consent evidence is append-only. |
| Sales | `sales.lead_transitioned.v1`, `sales.quote_issued.v1` | Stage history and audit commit atomically. |
| Work | `work.task_completed.v1`, `work.approval_decided.v1` | Approval snapshots are immutable. |
| Messaging | `messaging.send_intent_created.v1`, `messaging.inbound_message_threaded.v1` | SMTP/IMAP effects are idempotent. |
| Automation | `automation.workflow_run_started.v1`, `automation.dead_letter_created.v1` | Consumers record event IDs uniquely. |
| Onboarding | `onboarding.case_blocked.v1`, `onboarding.case_completed.v1` | Blockers require owner/action. |
| Support | `support.ticket_sla_breached.v1`, `support.ticket_reopened.v1` | Reopen creates a new active interval. |
| Feedback | `feedback.low_score_received.v1`, `feedback.recovery_closed.v1` | Recovery owner required. |
| Success | `success.customer_marked_at_risk.v1`, `success.renewal_review_started.v1` | Mandatory obligations outrank model ranking. |
| Intelligence | `intelligence.prediction_recorded.v1`, `intelligence.model_demoted.v1` | Prediction stores version, reasons, confidence/abstention. |
| Operations | `operations.backup_verified.v1`, `operations.maintenance_enabled.v1` | Operational evidence is retained with release. |

## Screen Inventory Baseline

S00 introduces no end-user screen. The route inventory remains the authoritative `docs/matrices/frontend_route_component_matrix.csv`.

S00 records these inventory rules:

- No screen may load unrestricted data and authorize later.
- Lists use bounded pagination and permission-filtered counts.
- Forms use allowlisted fields, CSRF, value preservation, error summary, field errors, and record version where applicable.
- HTMX is progressive enhancement only; full-page fallback remains required.
- Authenticated, portal, and signed-link content uses `Cache-Control: private, no-store`.
- All screens must map to requirement IDs, route matrix rows, API/data dependencies, tests, and acceptance evidence.

## API Inventory and Style Guide

S00 introduces no API operation. The API inventory remains the authoritative `docs/matrices/api_endpoint_implementation_matrix.csv` and `docs/contracts/internal_crm_openapi_v2.yaml`.

Style guide:

- Prefix private same-origin API under `/api/v1`.
- Use secure server-side sessions; no browser JWT, public API key, OAuth server, CORS, GraphQL, public webhooks, or arbitrary API integration.
- Unsafe browser requests require CSRF.
- Expose public ULIDs, never internal numeric IDs.
- Mutable resources return `ETag: "vN"` and require `If-Match` for commands/updates where specified.
- Effectful commands require `Idempotency-Key` where specified.
- Errors use RFC 9457 `application/problem+json` with correlation ID.
- Validation uses 422; stale writes use 412; idempotency/content conflict uses 409; resource guards use 429 with `Retry-After`; async work returns 202 and a status URL.
- Authorization applies before list, count, search, aggregate, drilldown, detail, mutation, export, file, and background paths.
- Endpoint performance, SQL budget, request/response size, query plan, indexes, and cache policy come from the endpoint matrix.

## Change-Control Process

| Change type | Required control |
|---|---|
| Product policy, owner, workflow, SLA, retention, communication, AI tier, production acceptance | PRD change record or ADR, Oghenemaro approval, traceability update. |
| Architecture, hosting, runtime, database engine, mail, dependency major version | ADR, official documentation review, Truehost evidence, rollback/removal plan. |
| API contract or data model | OpenAPI/DBML/matrix update, contract tests, migration/compatibility review, owner approval. |
| Role/capability/security policy | Threat model update, authorization matrix update, negative tests, step-up/four-eyes where required. |
| Configuration activation | Versioned bundle, dependency simulation, reviewer, effective date, rollback, audit event. |
| Destructive/privacy/export/merge/model promotion | Reason, step-up, four-eyes where required, audit, repair/rollback plan. |
| Emergency stop/rollback | Operations owner action, incident record, customer-effect containment, post-incident review. |

## Acceptance Evidence Register

| Evidence | Location |
|---|---|
| S00 plan | `docs/plans/s00-freeze-product-policy-and-company-configuration.md` |
| Compatibility freshness | `docs/compatibility/s00-freeze-product-policy-and-company-configuration.md` |
| ADR template | `docs/adr/ADR-TEMPLATE.md` |
| ADR set | `docs/adr/ADR-001-through-012-s00-architecture-baseline.md` |
| Threat model v1 | `docs/specs/s00-threat-model-v1.md` |
| Requirement traceability | `docs/matrices/s00_requirement_traceability_matrix.csv` |
| Review/test evidence | `docs/test-evidence/s00-freeze-product-policy-and-company-configuration/review-evidence.md` |
| Ledger | `docs/progress/BUILD_LEDGER.md` |
