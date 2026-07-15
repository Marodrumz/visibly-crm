# Codex frontend reference rules

Place this file at `docs/design/CODEX_FRONTEND_REFERENCE_RULES.md` and reference it from `AGENTS.md`.

## Mandatory reference gate

Before changing any staff, portal or public-facing UI, Codex must:

1. Read `AGENTS.md`.
2. Read the current build-step prompt and its explicit path allowlist.
3. Find the route in `docs/design/screen-reference-map.csv`.
4. Open the listed desktop reference PNG and HTML source.
5. Open the listed mobile reference when the route is part of a core responsive journey.
6. Read `docs/design/design-tokens.json`, `docs/design/COMPONENT_CATALOG.md` and `docs/design/FRONTEND_VISUAL_QA.md`.
7. Check the exact installed Django and htmx versions and current official documentation before using framework-specific behavior.
8. Stop and request an approved reference when a route is absent from the map or the requested design conflicts with the approved tokens.

Codex must never treat a verbal phrase such as “modern dashboard” or “make it beautiful” as permission to invent an unrelated design system.

## Source-of-truth order for frontend work

1. Product/security behavior in the approved PRD and engineering contracts.
2. Route/component/API matrices and authorization policy.
3. `screen-reference-map.csv` for layout family.
4. Reference HTML and PNG for visual hierarchy.
5. `design-tokens.json` and the component catalogue.
6. Current official framework documentation.
7. Existing reviewed project patterns.

A screenshot never overrides security, authorization, consent, state-machine or data-integrity requirements.

## Allowed implementation style

- Django templates and reusable template partials.
- Semantic HTML first.
- Locally hosted, stable htmx 2.x only for bounded progressive enhancement.
- Minimal vanilla JavaScript where a native HTML solution is insufficient.
- Local CSS compiled or organized under the project’s approved static pipeline.
- Local SVG icons from the reviewed icon subset.
- Server-rendered states and authoritative business logic.

## Prohibited frontend changes without explicit approval

- React, Vue, Angular, Svelte, Next.js or a separate SPA.
- Bootstrap, Tabler runtime, Carbon React or another major UI framework merely because it appears in a reference source.
- Runtime CDN fonts, icons, scripts, analytics, charting or illustrations.
- A second icon family.
- A new font family.
- New brand colors outside the token set.
- Public APIs, JWT, CORS or browser-side authorization logic.
- Browser-local authoritative customer or workflow state.
- Dynamic HTML injection from untrusted content.
- Hidden fields as an authorization control.
- Drag-only interactions.
- unbounded client-side tables or bulk selection.

## Route-specific no-touch rule

For a feature prompt, Codex may only modify:

- the route, templates, partials and static component files assigned to that build step;
- reusable components already named by the authoritative frontend matrix;
- tests and documentation required by that step.

It must not redesign unrelated navigation, tokens, authentication, portal scope, message policy or shared components without a separately approved change.

## Visual fidelity requirements

For an approved reference, preserve:

- information hierarchy;
- grid and content width;
- navigation placement;
- component density;
- spacing rhythm;
- typography hierarchy;
- border radius and elevation level;
- status color meaning;
- icon family and icon names;
- primary and secondary action order;
- mobile priority fields;
- all visible labels relevant to the business journey.

The agent may improve semantics and accessibility without changing the visual intent. It may not replace a design with a generic admin template.

## Required states

Every route must implement the applicable states below, even when only the default state appears in a route screenshot:

- initial/default;
- loading or htmx progress;
- empty with a permitted next action;
- field and form validation;
- authorization unavailable / existence-sensitive 404;
- stale-version conflict for mutable records;
- dependency degraded or unavailable;
- successful mutation confirmation;
- maintenance mode where applicable;
- narrow viewport and 200% zoom;
- JavaScript-disabled core operation.

Use `26-ui-states-board` as the common visual reference.

## Screenshot and visual-regression evidence

Before completion, capture at minimum:

- desktop: 1440 × 1000;
- narrow desktop/tablet: 1024 × 900;
- mobile: 390 × 844 and a 360 CSS-pixel functional check;
- 200% zoom for the critical route;
- keyboard focus for the primary action path.

Store evidence under the current build-step evidence directory. Dynamic values may differ, but hierarchy, components and spacing must match the selected reference family.

## Accessibility

- Meet applicable WCAG 2.2 AA.
- Use correct landmarks and headings.
- Associate every form control with a visible label.
- Provide error summary plus field-level errors.
- Keep focus visible and logical.
- Use text/icon meaning with every status color.
- Preserve browser zoom and reflow.
- Provide keyboard alternatives for every action.
- Use live regions only for important asynchronous changes.

## Completion response

When finishing a frontend task, report:

- route(s) implemented;
- reference file(s) used;
- files changed;
- reusable components added or reused;
- states implemented;
- desktop/mobile screenshots captured;
- accessibility checks run;
- exact tests and commands run;
- known visual variance, with reason and approval status.
