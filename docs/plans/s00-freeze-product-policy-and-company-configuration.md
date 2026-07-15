# S00 Plan - Freeze product, policy and company configuration

Date: 2026-07-15
Step: S00
Owner approval evidence: Oghenemaro approved the PRD implementation, assigned Oghenemaro to all S00 owner roles, and approved PRD implementation effective 2026-07-15 in the active Codex conversation.

## Scope

S00 is documentation and product governance only. It introduces no product code, Django app, route, service, migration, production configuration, customer-facing UI, external effect, dependency, or runtime behavior.

Allowed responsibility areas:

- Product governance baseline.
- Owner and decision register.
- Requirement traceability baseline.
- ADR template and S00 architecture decision set.
- Threat model v1 and security/privacy classification baseline.
- Capability, state-machine, event, screen, API, vocabulary, and glossary catalogs.
- Compatibility/freshness evidence for S00 references.
- S00 test and review evidence.
- Build ledger update without claiming unverified product implementation.

Shared support-file exception:

- `prompt-support/validate_changed_paths.py` may be added because the S00 prompt requires running it and the repository did not contain it. The script is validation tooling only, not product code, runtime configuration, application scaffolding, or a later-step implementation.

## Requirement IDs

S00 addresses the governance baseline for these PRD groups:

- UX: UX-01 through UX-12.
- STM: STM-01 through STM-08.
- CFG: CFG-001 through CFG-012.
- SEC: SEC-001 through SEC-037.
- NFR: NFR-001 through NFR-045.
- OPS: OPS-001 through OPS-030.
- TST: TST-001 through TST-030.

The exact row-level traceability is generated in `docs/matrices/s00_requirement_traceability_matrix.csv`.

## Source Review

Read before editing:

- `AGENTS.md`.
- `docs/specs/Production_PRD_Internal_CRM_AI_Truehost.docx`.
- `docs/specs/Full_Production_Frontend_Backend_Build_Manual.md`, S00 section.
- `docs/matrices/build_step_acceptance_matrix.csv`, S00 row.
- `docs/matrices/frontend_route_component_matrix.csv`, S00 filtered rows: none.
- `docs/matrices/backend_service_command_matrix.csv`, S00 filtered rows: none.
- `docs/matrices/api_endpoint_implementation_matrix.csv`, S00 filtered rows: none.
- `docs/contracts/internal_crm_openapi_v2.yaml`.
- `docs/contracts/internal_crm_data_model.dbml`.
- `docs/contracts/database_table_catalog.csv`.
- `docs/matrices/prd_requirement_register.csv`.
- `docs/progress/BUILD_LEDGER.md`.
- Existing `docs/adr`, `docs/plans`, `docs/compatibility`, `docs/test-evidence`, and `docs/threat-model` contents.

No nearer `AGENTS.md` file exists below the repository root.

## S00 Prerequisites

Declared prerequisites:

- Approved PRD.
- Named sponsor.
- Named product owner.
- Named technical owner.
- Named security/privacy owner.
- Named process owners.

Prerequisite disposition:

- Met by owner approval in the active conversation on 2026-07-15.
- Oghenemaro is assigned to all S00 owner roles.
- Human business acceptance remains human-owned; Codex records evidence but does not independently create formal acceptance authority.

## Data and API Changes

No database tables, constraints, indexes, migrations, API operations, Django services, routes, templates, static assets, jobs, events, or production settings are created or changed in S00.

Documentation will define canonical identifiers, timezone/currency semantics, record classes, retention classes, and preliminary table/storage budgets as implementation inputs for later steps.

## Risks and Controls

Risk level: high governance impact, low runtime impact.

- Missing company-specific values must not be invented. The decision register records unresolved values with Oghenemaro as owner and a gate before dependent build steps.
- Source precedence is locked as PRD, manual, contracts, matrices/registers, accepted ADRs, code/migrations.
- The system remains bounded to one Truehost Starter account, one MySQL/MariaDB database, Passenger WSGI, cPanel Cron, Truehost SMTP/IMAP, local HTMX, and local explainable AI only.
- Any future change to hosting, auth, API, database, mail, AI tier, retention, or customer communication policy requires ADR/change-control review.

## Rollout

S00 produces documentation artifacts only. Rollout is repository-only:

1. Record owner approval and source evidence.
2. Publish compatibility freshness evidence.
3. Publish governance baseline and catalogs.
4. Publish threat model v1.
5. Publish row-level S00 traceability.
6. Update ledger to a non-VERIFIED state unless every machine-verifiable gate, including the requested changed-path validator, runs successfully.

## Rollback and Repair

Rollback is document-only:

- Revert the S00 documentation files and ledger row.
- No database, customer data, customer communication, runtime dependency, or static asset rollback is required.
- If later review rejects an S00 decision, create a follow-up ADR/change-control record and update dependent matrices before implementation.

## Test and Evidence Paths

Evidence directory:

- `docs/test-evidence/s00-freeze-product-policy-and-company-configuration/`

Expected evidence files:

- `review-evidence.md`: source review, workshop/review status, changed-path validation status, limitations, and commands.
- `s00_requirement_traceability_matrix.csv`: stored under `docs/matrices/` as release-controlled traceability evidence.

Machine-verifiable checks planned:

- `git status --short`.
- S00 matrix filters for routes/services/API operations.
- Requirement register group counts.
- `python prompt-support/validate_changed_paths.py --step S00` if the script exists.

Repository limitation:

- No `pyproject.toml`, requirements files, Django project, or test runner exists at S00. Runtime/test commands from later steps cannot run yet.
- `prompt-support/validate_changed_paths.py` was absent at plan time and is added as the minimal support-file exception needed to validate S00 scope.
