# S00 Threat Model v1

Date: 2026-07-15
Owner: Oghenemaro
Build step: S00
Reference baseline: OWASP ASVS 5.0.0 Level 2, WCAG 2.2 AA for applicable journeys, NIST AI RMF 1.0 as voluntary governance reference.

This threat model is a planning artifact. It creates no runtime control and must be updated when later steps add identity, authorization, files, mail, workflows, portal, reporting, imports, retention, AI, or deployment behavior.

## System Boundary

Inside the production runtime boundary:

- Staff browser, customer portal, and signed public forms over HTTPS.
- cPanel web server and Passenger WSGI.
- Django 5.2 LTS modular monolith.
- One MySQL/MariaDB InnoDB `utf8mb4` database.
- Private filesystem outside `public_html`.
- cPanel Cron commands for jobs, outbox, IMAP, backups, and housekeeping.
- Truehost SMTP/IMAP mailboxes.
- Local explainable AI/rules only.

Outside the boundary:

- External AI/LLM/vector services.
- Public APIs/webhooks/OAuth server/CORS/JWT browser auth.
- Redis/Celery/RabbitMQ/Kafka/daemon workers.
- Docker/Kubernetes/VPS-only services.
- Runtime CDN, external analytics, external CAPTCHA, external monitoring.
- SMS, WhatsApp, voice, and social automation providers.

## Trust Boundaries

| Boundary | Risk |
|---|---|
| Browser to Django | Session theft, CSRF, XSS, request tampering, direct-object access, stale writes. |
| Staff/portal session to authorization policy | Role escalation, record-scope bypass, field leakage, count/search leakage. |
| Django to MySQL/MariaDB | Injection, transaction races, collation surprises, lock behavior mismatch, data corruption. |
| Django to private filesystem | Path traversal, unsafe file type, direct public exposure, inode/storage exhaustion. |
| Django/Cron to SMTP/IMAP | Duplicate send, ambiguous delivery, misthreaded inbound mail, hostile MIME/body/header. |
| Configuration to workflow/runtime | Unsafe automation, unexpected retroactive effect, code/template/SQL execution through configuration. |
| AI scoring to staff decisions | Hidden bias, leakage, overreliance, stale features, unsafe automatic action. |
| Truehost account boundary | Provider outage, shared-host throttling, correlated backups, limited independent monitoring. |

## Critical Assets

| Asset | Classification | Required protection |
|---|---|---|
| Staff identities, MFA secrets, sessions, recovery evidence | Restricted/security | MFA, hashing/encryption where applicable, revocation, throttling, audit. |
| Customer organizations, contacts, relationships, notes, timelines | Confidential/customer | Default-deny authorization, field policy, audit, retention policy. |
| Consent, suppression, privacy, legal hold records | Restricted/privacy | Append-only evidence, policy precedence, export/deletion approval. |
| Quotes, commercial terms, opportunities, renewals | Confidential/commercial | Role/record scope, approval, versioning, immutable issued evidence. |
| Email/message bodies and attachments | Restricted/customer | Sanitization, private storage, idempotency, threading, no unsafe active content. |
| Workflow definitions, templates, policies, roles | Restricted/governance | Versioning, review, simulation, effective dates, immutable active versions. |
| Audit events and manifests | Restricted/audit | Append-only, tamper-evident hashes, periodic verification. |
| Backups, exports, archives | Restricted/bulk data | Step-up/four-eyes where required, encryption, expiry, safe manifests, formula neutralization. |
| AI artifacts, predictions, feature snapshots | Confidential/intelligence | Checksums, explainability, abstention, human feedback, disablement. |
| Secrets and environment values | Secret | cPanel env or mode-0600 private files only; never committed or printed. |

## Actors

| Actor | Authorized intent | Threat concern |
|---|---|---|
| Staff user | Daily CRM work within role and record scope | Overbroad access, accidental disclosure, stale write, unsafe export. |
| Administrator | Configuration, roles, release, operations | Privilege abuse, unsafe activation, missing review, secret exposure. |
| Portal user | Access scoped customer data/tasks/preferences | IDOR, token tampering, cross-organization leakage. |
| Public/signed-link user | Single-purpose form/preference/feedback flow | Enumeration, abuse, replay, invalid token disclosure. |
| Cron process | Bounded jobs/mail/import/export/backup | Overlap, duplicate effect, runaway job, stale policy. |
| Attacker | Unauthorized access, data theft, spam, resource exhaustion | Injection, XSS, CSRF, brute force, upload abuse, path traversal. |
| Provider/operator outside app | Hosting infrastructure access/limits | Availability, backup correlation, resource throttling. |

## Data Classification

| Class | Examples | Baseline rules |
|---|---|---|
| Public | Public help copy, approved signed-form instructions | No sensitive values; rate-limited where form submission exists. |
| Internal | Non-sensitive operational metadata, release notes | Staff authenticated; no portal/customer exposure unless approved. |
| Confidential customer | Contact, organization, timeline, cases, tasks, quotes, support | Record/field authorization, audit, retention, no uncontrolled export. |
| Restricted privacy | Consent, suppression, legal hold, privacy cases, sensitive fields | Purpose-bound access, step-up/four-eyes for high-risk actions. |
| Restricted security | Auth events, sessions, MFA, roles, capability config | Least privilege, redaction, tamper-evident audit. |
| Secret | Credentials, signing/encryption keys, MFA seeds, SMTP/IMAP passwords | Outside source/public roots; never in logs/support bundles/test data. |

## Privacy Purpose Map

Purpose codes are frozen as vocabulary. Legal basis/details remain owner-approved configuration.

| Purpose code | Applies to | Baseline rule |
|---|---|---|
| `service_delivery` | Support, onboarding, customer requests, critical service notices | Allowed only for necessary service delivery and account obligations. |
| `sales_relationship` | Leads, opportunities, quotes, lawful commercial follow-up | Must respect consent, DNC, quiet hours, caps, replies, complaints, and severe support holds. |
| `customer_success` | Health, renewal, recovery, advocacy, relationship reviews | Active recovery/support obligations outrank promotional outreach. |
| `feedback_recovery` | Surveys, low-score recovery, issue resolution | Survey fatigue/anonymity thresholds must be configured before launch. |
| `security_operations` | Auth, incident response, audit, abuse prevention | Limited to security/audit need and retention policy. |
| `legal_compliance` | Legal hold, privacy cases, retention, export/deletion | Overrides normal purge and requires owner-reviewed evidence. |
| `product_intelligence` | Local explainable scoring and recommendations | Optional, explainable, no external AI, no free-form customer text, no high-impact automatic action. |

## Privilege Conflicts

| Conflict | Required control |
|---|---|
| User grants own privileged role | Four-eyes review and audit; actor separation. |
| Export requester approves own sensitive export | Step-up plus separate approver where configured. |
| Quote creator approves own high-risk quote | Approval actor separation based on threshold/policy. |
| Workflow author activates high-impact workflow | Review/simulation and separate activation approval. |
| Model trainer promotes model | Promotion requires named approval and evaluation evidence. |
| Privacy deletion conflicts with legal hold or active obligation | Legal hold/active dependency wins; skip with reason. |
| Support/commercial owner suppresses severe complaint visibility | Severe support/recovery state blocks promotional automation. |
| Administrator edits policy to bypass security/consent | Security/consent cannot be bypassed by feature flag or configuration. |

## Abuse Cases and Mitigations

| Abuse case | Impact | Required mitigation |
|---|---|---|
| Direct object ID manipulation in staff/portal URLs | Unauthorized disclosure or mutation | Server-side record scope before load; public ULIDs do not imply access; exhaustive IDOR tests. |
| Search/count leakage | Cross-scope data inference | Permission-filtered selectors before list/count/search/aggregate. |
| Mass assignment | Owner/role/status/visibility tampering | Explicit form/API field allowlists and field policy. |
| CSRF on state-changing request | Unauthorized action from browser session | CSRF on unsafe browser requests; signed-token alternative only with security review. |
| Stored/reflected XSS | Session/data compromise | Auto-escape templates, strict sanitizer for rich/customer HTML, CSP, XSS corpus tests. |
| SQL injection/raw SQL misuse | Data breach/corruption | ORM/parameterized queries; raw SQL isolated and reviewed. |
| Unsafe file upload | Malware/active content/path traversal/public exposure | Type/size/signature allowlists, safe filenames, private storage, no unsafe SVG/HTML/scripts/macros/nested archives. |
| Duplicate send after retry/crash | Customer trust/compliance harm | Outbox idempotency, deterministic Message-ID, delivery states, no blind retry of delivery unknown. |
| Inbound MIME/header abuse | XSS, misthreading, duplicate tickets | Treat all inbound content as untrusted; UID/Message-ID idempotency; controlled reply tokens. |
| Workflow configuration executes code/SQL/network | Remote execution/data exfiltration | Declarative allowlisted actions only; no code, SQL, shell, arbitrary templates, HTTP calls, or webhooks. |
| Long-running job exhausts host | Availability loss | Cron leases, item/time limits, checkpoints, resource guard, explicit exits. |
| Backup cannot restore | Data loss | Verified backup manifests, checksums, restore drills, compatibility evidence. |
| AI recommendation hides safety obligation | Unsafe/commercially harmful action | Obligations, SLA, recovery, consent, and severe support outrank prediction. Low confidence abstains. |
| Secret leaks through support bundle/log | Credential compromise | Structured redaction, no real `.env` values, no credentials/tokens/body dumps. |

## Residual and Accepted Boundary Risks

| Risk | Residual status | Required governance |
|---|---|---|
| Single Truehost/provider outage | Accepted high residual | Incident runbook and customer contact alternative; app cannot eliminate. |
| Independent outage monitoring inside same account | Accepted limitation | Do not claim provider-independent detection. |
| Correlated provider backups | Accepted unless offline copy procedure approved | Monthly encrypted offline copy is recommended governance exception. |
| No external malware scanner | Accepted residual | Strict file-type prohibition and safe serving reduce but do not eliminate risk. |
| No SMS/WhatsApp/voice/social automation | Accepted product boundary | Staff-assisted logging/tasks only. |
| No generative AI runtime | Accepted product boundary | Templates and local explainable scoring only. |

## Review and Update Triggers

Update this threat model before or during:

- S07-S11 identity, authorization, audit, and file implementation.
- S15 consent/preferences/suppression.
- S22-S24 mail and messaging.
- S25-S27 workflow compiler/runtime and 28 workflows.
- S32 portal and signed public flows.
- S33-S34 reporting, export, retention, archive, privacy cases.
- S35 local intelligence.
- S39 security hardening and independent verification.
- Any change to hosting, runtime, database, mail, AI, retention, or external dependency posture.

## S00 Review Status

| Review | Status | Evidence |
|---|---|---|
| Threat model v1 drafted | Complete | This document. |
| Owner assignment | Complete | Oghenemaro assigned all S00 owner roles on 2026-07-15. |
| Formal independent security review | Not applicable to S00 documentation only | Required later by SEC-037 and S39. |
| Runtime control verification | Not applicable to S00 | No code/runtime introduced. |
