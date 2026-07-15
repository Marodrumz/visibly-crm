# Deep audit of `prompt_material.zip`

## What the example pack contains

The example archive contains exactly seven PNG references:

1. `01-design-system.png` — brand mark, Poppins typography, color tokens and type scale.
2. `02-onboarding-screen.png` — one mobile onboarding / first-run screen.
3. `03-auth-screen.png` — one mobile registration screen.
4. `04-language-selection-screen.png` — a searchable selection-list pattern.
5. `05-home-and-tab-navigation.png` — dashboard and persistent tab navigation.
6. `06-lesson-screen.png` — list/detail progression and locked/completed states.
7. `07-audio-lesson-screen.png` — full-screen media interaction and feedback summary.

## Why the example works as prompt material

The pack gives a coding agent visual facts instead of only adjectives:

- one explicit design system establishes the palette, type family and hierarchy;
- each important feature has a named image that can be cited in a prompt;
- recurring navigation and component treatments are visible across screens;
- the illustration style and product personality are consistent;
- screen proportions communicate spacing, density and mobile hierarchy;
- selected, completed, locked and active states are visible rather than inferred.

The important prompting pattern is therefore:

> “Build route X by following reference image Y, reusing the design system in image 01 and preserving the navigation/component language shown in images 05–07.”

That is much safer than “build a beautiful modern screen.”

## Gaps that would still cause blind production work

The example is useful for a teaching app but is not sufficient for a production CRM because it omits:

- desktop and tablet layouts;
- route-to-reference mapping;
- loading, empty, validation, permission, conflict, maintenance and dependency-failure states;
- hover, focus, pressed and disabled states;
- form anatomy, table density, bulk actions and long-data behavior;
- responsive transformation of data tables;
- accessibility requirements and keyboard paths;
- icon names and asset provenance;
- source licenses and local-storage rules;
- exact reusable components and design tokens in machine-readable form;
- visual acceptance evidence and screenshot dimensions;
- rules preventing a coding agent from importing an incompatible UI framework;
- a decision for routes that do not have an individual screenshot.

## How this CRM pack improves the pattern

This pack supplies:

- 32 original high-fidelity HTML visual references;
- matching PNG screenshots;
- desktop, mobile and customer-portal patterns;
- a full design-system board;
- a required UI-state board;
- a responsive data-table/card pattern;
- a route map covering all 136 frontend routes from the engineering matrix;
- machine-readable JSON and CSS tokens;
- a local subset of Lucide SVG icons with license;
- exact external source locations and usage/licensing rules;
- synthetic screen data;
- Codex-specific no-guess rules and visual completion gates.

## Design interpretation for the CRM

The example pack’s playful mobile style is not copied. This CRM uses a restrained enterprise visual language that matches the approved PRD:

- navy and teal express dependability and operational control;
- blue identifies customer communication and information;
- purple marks local AI-assisted content consistently;
- green, amber and red are reserved for operational status and are always paired with text/icon meaning;
- dense lists and tables remain readable without resembling a spreadsheet application;
- mobile views prioritize customer context and task completion rather than reproducing every desktop column;
- no mascot, stock photography or decorative illustration is required for core workflows.
