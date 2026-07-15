# Install this material pack into the CRM repository

The canonical repository location is `docs/design/`. Do not leave this pack in an arbitrary downloads folder because Codex must resolve the same paths on every task.

## Option A — reviewed shell installer

From the extracted pack directory:

```bash
bash install_into_repo.sh /absolute/path/to/crm-repository
```

The script copies the visual source of truth into `docs/design/` and does not modify application code, dependencies, templates, static files, databases, secrets, or deployment configuration.

After reviewing the copied files, append the contents of:

```text
docs/design/AGENTS_FRONTEND_PATCH.md
```

to the repository-root `AGENTS.md`.

## Option B — manual install

Create `docs/design/` and copy:

- all files from the pack root except `install_into_repo.sh` and this installation guide;
- all directories `assets/`, `brand/`, `mock-data/`, `prototype/`, and `references/`;
- every Markdown file inside the pack's `docs/` directory into `docs/design/` itself.

The expected layout is:

```text
docs/design/
├── README.md
├── AGENTS_FRONTEND_PATCH.md
├── CODEX_FRONTEND_REFERENCE_RULES.md
├── COMPONENT_CATALOG.md
├── FRONTEND_VISUAL_QA.md
├── MATERIAL_ACQUISITION_GUIDE.md
├── PROMPT_MATERIAL_AUDIT.md
├── REFERENCE_CONTACT_SHEET.png
├── design-tokens.json
├── design-tokens.css
├── screen-reference-map.csv
├── asset-source-manifest.csv
├── selected-icon-map.csv
├── LICENSE_NOTICES.md
├── SHA256SUMS.txt
├── assets/icons/
├── brand/
├── mock-data/
├── prototype/
└── references/
```

## Verification

```bash
python - <<'PY'
from pathlib import Path
import csv
root = Path('docs/design')
required = [
    root / 'CODEX_FRONTEND_REFERENCE_RULES.md',
    root / 'screen-reference-map.csv',
    root / 'design-tokens.json',
    root / 'REFERENCE_CONTACT_SHEET.png',
    root / 'references/06-customer-360.png',
    root / 'prototype/screens/06-customer-360.html',
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit('Missing design materials:\n' + '\n'.join(missing))
with (root / 'screen-reference-map.csv').open(newline='', encoding='utf-8') as handle:
    routes = list(csv.DictReader(handle))
if len(routes) != 136:
    raise SystemExit(f'Expected 136 mapped routes, found {len(routes)}')
print('Frontend material gate installed correctly: 136 routes mapped.')
PY
```

## Production implementation boundary

The prototype HTML is visual handoff only. Codex must translate it into reviewed Django templates and project CSS. It must not copy prototype JavaScript or treat prototype data as production data. Security, authorization, API, database and workflow contracts remain authoritative.
