# CRM frontend visual reference material pack

This pack is the production-grade equivalent of the seven-image `prompt_material.zip` example. It gives Codex exact visual references and route-level rules so the Django frontend is not invented blindly.

## Contents

- **32 original reference screens** in `references/` and editable static HTML in `prototype/screens/`.
- **Reference gallery** at `prototype/index.html`.
- **All 136 CRM routes mapped** in `screen-reference-map.csv`.
- **Machine-readable tokens** in `design-tokens.json` and `design-tokens.css`.
- **Reviewed local Lucide icon subset** in `assets/icons/`.
- **Component catalogue** in `docs/COMPONENT_CATALOG.md`.
- **Codex rules** in `docs/CODEX_FRONTEND_REFERENCE_RULES.md`.
- **Visual QA checklist** in `docs/FRONTEND_VISUAL_QA.md`.
- **Exact source guide** in `docs/MATERIAL_ACQUISITION_GUIDE.md`.
- **Deep audit of the example archive** in `docs/PROMPT_MATERIAL_AUDIT.md`.
- **Synthetic fixture data** in `mock-data/crm-demo-data.json`.
- **Repository installation guide** in `INSTALL_IN_REPOSITORY.md` and the bounded `install_into_repo.sh` helper.

## How Codex must use the pack

1. Look up the target route in `screen-reference-map.csv`.
2. Open its reference PNG and HTML.
3. Reuse the tokens and named components.
4. Implement the route in its assigned build step only.
5. Implement all required alternate states using `26-ui-states-board`.
6. Capture desktop and mobile evidence before completion.
7. Stop rather than invent when a requested route or visual change has no approved reference.

## Important constraints

- The HTML prototypes are **visual handoff**, not production application code.
- Security, authorization, state machines and API contracts always override visual convenience.
- Do not introduce React, a separate SPA, Bootstrap, Tabler runtime or Carbon React from these materials.
- Do not use runtime CDNs.
- Do not contact customer addresses or use production data while producing visual evidence.
- Replace placeholder company branding only with approved company-owned files.

## Reference inventory

32 screen references, 136 mapped routes and 145 locally stored SVG icons.
