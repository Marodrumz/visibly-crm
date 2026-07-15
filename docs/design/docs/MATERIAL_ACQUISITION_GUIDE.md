# Exact material acquisition guide

This project should be buildable without a designer inventing assets during implementation. Use the supplied original references first. External sources are limited to reviewed, versioned material.

## 1. Company-owned materials required before visual freeze

Obtain these from the company sponsor and store them under the private design source repository, not improvised by Codex:

1. **Primary logo in SVG** — clean vector, no embedded remote image.
2. **Horizontal wordmark in SVG** — light and dark variants if available.
3. **Favicon/source mark in SVG**.
4. **Approved company display name and product name**.
5. **Primary domain and support/sales mailbox labels**.
6. **Approved brand colors** or written approval to use this pack’s navy/teal baseline.
7. **Email signature content** and legal footer.
8. **Privacy notice, acceptable-use text and signed-link wording**.
9. **Product/service names and short descriptions**.
10. **Staff names/roles**; staff photos are optional. Initial avatars are the default and avoid unnecessary image handling.

The placeholder files in `brand/` must not silently become the legal production logo.

## 2. Typography

- Exact source: `https://rsms.me/inter/`
- Repository and license: `https://github.com/rsms/inter`
- License: SIL Open Font License 1.1
- Project rule: download a stable release, record exact version and SHA-256, self-host it locally, and do not use Google Fonts or another runtime CDN.
- This deliverable intentionally does not redistribute font files.

## 3. Icons

- Exact browser: `https://lucide.dev/icons/`
- Exact source repository: `https://github.com/lucide-icons/lucide`
- License: ISC
- Reviewed source version in this pack: `lucide-static 1.24.0`
- Local subset: `assets/icons/`
- Usage map: `selected-icon-map.csv`

Do not mix Lucide with Heroicons, Font Awesome, Material Symbols, emoji and bespoke line icons on the same interface.

## 4. Enterprise component references

### Tabler

- Live reference: `https://tabler.io/admin-template`
- Source: `https://github.com/tabler/tabler`
- License: MIT
- Use: study responsive admin shell, card/table density and layout examples.
- Constraint: do not add Bootstrap or Tabler runtime to the Django project without an approved architecture change.

### Carbon Design System

- System: `https://carbondesignsystem.com/`
- Data tables: `https://carbondesignsystem.com/components/data-table/usage/`
- Empty states: `https://carbondesignsystem.com/patterns/empty-states-pattern/`
- AI label: `https://carbondesignsystem.com/components/ai-label/usage/`
- Figma kit guidance: `https://carbondesignsystem.com/designing/kits/figma/`
- Use: component anatomy, keyboard behavior, data density and AI transparency.
- Constraint: use as design/behavior reference only; do not introduce Carbon React.

### USWDS

- System and components: `https://designsystem.digital.gov/`
- Accessibility guidance: `https://designsystem.digital.gov/documentation/accessibility/`
- Use: additional accessible form, alert, tag and interaction checks.

## 5. Optional illustrations

The CRM does not need a mascot or decorative scenes. For a rare first-use or empty state:

- Gallery: `https://undraw.co/illustrations`
- License: `https://undraw.co/license`
- Download one relevant SVG, recolor it to the approved brand accent, store it locally, record its exact source URL and date, and do not redistribute a library of unDraw assets.

Preferred search concepts: `No data`, `Search`, `Secure files`, `Maintenance`, `Completed`, `Team collaboration`.

Do not use illustrations in dense tables, customer records, tickets, audit views, security pages or incident workflows.

## 6. Charts and data visualization

The reference screens use original static SVG chart patterns. Production should prefer server-rendered SVG for small operational charts. Do not add a chart library automatically.

A chart dependency may be proposed only when:

- the route cannot be implemented accessibly with small local SVG;
- the dependency works without CDN or daemon;
- its size, license, keyboard/summary behavior and Truehost resource impact are reviewed;
- the user explicitly approves the addition.

Every chart must include text summary and exact drilldown; chart color alone cannot carry meaning.

## 7. Photos and avatars

- Default staff/customer avatar: initials generated in HTML/CSS.
- Customer logos: use only customer-provided/authorized files and store privately or in approved static assets.
- Avoid stock portraits and remote avatar APIs.
- Do not use real customer photos in fixtures or screenshots.

## 8. Design workspace

The supplied HTML prototypes are the primary handoff and can be opened without Figma:

- Gallery: `prototype/index.html`
- Screen sources: `prototype/screens/`
- Screenshots: `references/`
- Tokens: `design-tokens.json` and `design-tokens.css`

Where a Figma file is desired, rebuild the same tokens/components in a company-controlled Figma project. Do not depend on an unverified community CRM kit as the source of truth.
