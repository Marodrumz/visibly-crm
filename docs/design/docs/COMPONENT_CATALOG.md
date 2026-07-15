# Production frontend component catalogue

All components are server-rendered by default and must work without htmx unless the interaction is explicitly progressive.

## Application structure

| Component | Purpose | Required behavior |
|---|---|---|
| `AppShell` | Staff sidebar, top bar and main content | Permission-aware navigation, current route state, responsive collapse, no hidden security assumption |
| `PortalShell` | Customer-facing portal frame | Separate URL/template namespace, plain language, session-derived organization scope |
| `PublicFlowShell` | Signed/public forms | Minimal navigation, privacy notice, abuse controls, safe errors |
| `PageHeader` | Title, description and primary actions | One clear H1, actions ordered by importance, wrap at narrow widths |
| `Breadcrumbs` | Deep administration and record context | Current page not linked; accessible list semantics |

## Navigation and discovery

| Component | Use |
|---|---|
| `PrimaryNav` | Approved information architecture only |
| `GlobalSearch` | Universal permission-filtered search |
| `Tabs` | Stable record subviews; no tab hides unauthorized data in the DOM |
| `SavedViewBar` | Bounded filters and visible active criteria |
| `Pagination` | Cursor/keyset first; default 25, maximum 100 |

## Data and work

| Component | Use | Production rule |
|---|---|---|
| `DataTable` | Desktop list views | Accessible table semantics, indexed sorting only, bounded selection |
| `ResponsiveRecordCard` | Mobile representation of table row | Preserve status, owner, next action and primary action |
| `WorkQueueItem` | Ranked human obligation | Show source, severity, owner/queue, due time and deep link |
| `MetricCard` | Actionable KPI summary | Always link to exact permitted drilldown |
| `Timeline` | Normalized append-only history | Show source, actor, visibility and event time |
| `StateBadge` | Lifecycle/status state | Text + icon; never color alone |
| `OwnerChip` | Accountable owner or queue | Inactive/unassigned state must be explicit |
| `SlaClock` | First-response/update/resolution evidence | Distinguish company, customer-wait and total time |

## Forms and commands

| Component | Production rule |
|---|---|
| `TextField`, `SelectField`, `TextareaField` | Visible label, help, retained value, server validation |
| `ErrorSummary` | Focused on invalid submit; links to exact fields |
| `CommandPanel` | Explicit state transition, required reason/evidence and impact |
| `DestructiveConfirm` | Typed impact, step-up/four-eyes where policy requires |
| `ConflictView` | Explain stale version and provide safe refresh/reapply |
| `JobStatus` | Long operations return promptly and show durable status |

## Communications

| Component | Production rule |
|---|---|
| `EmailThread` | Sanitize inbound HTML, display visibility/direction and threading evidence |
| `MessageComposer` | Approved sender, purpose, template/block origin and policy status |
| `CommunicationGuardSummary` | Explain allow, hold, cancel or defer decision |
| `DeliveryEvidence` | Show deterministic Message-ID, attempts and ambiguous state without blind retry |

## Automation

| Component | Production rule |
|---|---|
| `WorkflowBuilder` | Allowlisted typed steps only; no arbitrary code/SQL/HTTP |
| `WorkflowNode` | Trigger, condition, delay, action or stop with distinct accessible meaning |
| `SimulationResult` | No side effects; exact dates/actions/guards/conflicts/exits |
| `RunTrace` | Append-only trigger/action/attempt history |
| `DeadLetterPanel` | Owner, severity, evidence, reason and guarded replay |
| `KillSwitchPanel` | Scope, reason, actor and immediate claim stop |

## AI and explainability

| Component | Production rule |
|---|---|
| `AiLabel` | Marks AI-assisted content and opens explanation; not decoration |
| `PredictionCard` | Outcome/action, confidence, horizon, version and expiry |
| `ReasonList` | Positive/negative reasons with evidence links |
| `MissingInformation` | Explain uncertainty and abstention |
| `RecommendationFeedback` | Accept, reject, modify, wrong data/category/priority |
| `AutomationBoundary` | State visibly what cannot happen automatically |

## System states

Use the state board for loading, empty, validation, permission, error, conflict, degraded dependency, queued work, success and maintenance.
