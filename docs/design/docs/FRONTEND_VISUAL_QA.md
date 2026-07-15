# Frontend visual and interaction quality checklist

## Before coding

- [ ] Route exists in `screen-reference-map.csv`.
- [ ] Desktop and mobile reference files have been opened.
- [ ] Required components are confirmed from the authoritative frontend matrix.
- [ ] Current official Django/htmx documentation matches installed versions.
- [ ] No new framework, font, icon family or chart runtime is being introduced.

## Default state

- [ ] H1, subtitle and primary action match the reference hierarchy.
- [ ] Status, owner, next action, due time and risk appear above the fold on operational detail pages.
- [ ] Table columns and card summaries preserve the route’s operational purpose.
- [ ] AI-assisted content is visibly labeled and explainable.
- [ ] Customer-visible, internal and restricted content are persistently distinguished.

## Alternate states

- [ ] Loading/progress state.
- [ ] Empty state with next permitted action.
- [ ] Validation summary and field errors without losing valid input.
- [ ] Unauthorized / existence-sensitive 404 state.
- [ ] Optimistic-lock conflict state.
- [ ] Dependency degraded/unavailable state.
- [ ] Successful mutation state.
- [ ] Maintenance state where applicable.

## Responsive

- [ ] Desktop screenshot at 1440 × 1000.
- [ ] 1024 × 900 layout remains functional.
- [ ] 390 × 844 reference check.
- [ ] 360 CSS-pixel viewport has no lost action.
- [ ] 200% zoom has no clipped content or hidden controls.
- [ ] Wide tables use accessible scroll or responsive cards.

## Accessibility

- [ ] Landmark and heading hierarchy.
- [ ] Visible labels and descriptions.
- [ ] Logical tab order and visible focus.
- [ ] No color-only meaning.
- [ ] Icon-only buttons have accessible names.
- [ ] Dialog focus and escape behavior.
- [ ] Error summary is focused and links to fields.
- [ ] Reduced motion is respected.
- [ ] Core action works without JavaScript.

## Security and privacy

- [ ] Unauthorized data is absent from HTML, counts, attributes and JSON—not merely hidden.
- [ ] CSRF is present on unsafe browser requests.
- [ ] No raw stack, secret, SQL, path or provider detail in errors.
- [ ] Private files have no public URL.
- [ ] Signed/public flows do not accept target organization/contact identifiers from the browser.
- [ ] Inbound rich content is sanitized.

## Performance

- [ ] Route meets its p95, SQL count and compressed-response budget.
- [ ] No N+1 query.
- [ ] No unbounded list, selection or payload.
- [ ] Static assets are local, fingerprinted and reusable.
- [ ] Optional decoration does not delay the primary operation.
