# S00 Compatibility and Official Documentation Freshness

Access date: 2026-07-15
Build step: S00 - Freeze product, policy and company configuration

## Local and Repository Version Observations

| Area | Observed version/state | S00 disposition |
|---|---|---|
| Local Python | `Python 3.14.2` from `python --version` | Local workstation only. Not approved as production runtime by S00. |
| Project dependency files | No `pyproject.toml`, `requirements.in`, `requirements.txt`, `requirements-dev.txt`, lock file, `package.json`, or frontend asset directory found. | No dependency can be installed, upgraded, removed, or approved in S00. |
| Django | Not installed or pinned in repository. Baseline target remains Django 5.2 LTS latest compatible patch. | S02 must lock; S01 must prove Truehost runtime capability. |
| Database driver | Not installed or pinned. | S01/S02 must choose only after actual Truehost engine and wheel/no-compilation evidence. |
| MySQL/MariaDB engine | Not available in repository evidence. | S01 must record exact Truehost engine/version/charset/collation. |
| HTMX | No vendored HTMX asset found. | S02/S05 must vendor approved local stable 2.x asset; no runtime CDN. |
| cPanel/Passenger | No actual account evidence in repository. | S01 remains mandatory before runtime acceptance. |
| Test tools | No pinned toolchain exists. | S02 must pin development tools; S00 can only record planned evidence. |

## Official Sources Checked

| Topic | Official source | Finding |
|---|---|---|
| PRD/source precedence | Internal PRD/manual/AGENTS source rules | No public official standard governs this project-specific precedence. S00 uses the repository rule: approved PRD, implementation manual, contracts, matrices/registers, accepted ADRs, then code/migrations. |
| NIST AI RMF | https://www.nist.gov/itl/ai-risk-management-framework | AI RMF 1.0 was released on 2023-01-26 and is being revised. It remains a voluntary risk-management reference, not a certification claim. |
| NIST AI RMF publication | https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10 | Confirms AI RMF 1.0 purpose: managing AI risks and supporting trustworthy/responsible AI systems. |
| OWASP ASVS | https://owasp.org/www-project-application-security-verification-standard/ | Latest stable ASVS is 5.0.0. Requirement references should be version-qualified because identifiers may change between versions. |
| WCAG 2.2 normative recommendation | https://www.w3.org/TR/WCAG22/ | WCAG 2.2 is the applicable W3C recommendation baseline for accessible web content. |
| WCAG 2.2 changes | https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/ | WCAG 2.2 adds nine success criteria over 2.1; Success Criterion 4.1.1 Parsing is obsolete and removed. |
| Django download/support | https://www.djangoproject.com/download/ | Latest overall Django release observed is 6.0.7, but project architecture stays on Django 5.2 LTS pending approved version lock. |
| Django 5.2 release notes | https://docs.djangoproject.com/en/6.0/releases/5.2/ | Django 5.2 supports Python 3.10, 3.11, 3.12, 3.13, and Python 3.14 as of Django 5.2.8; only latest micro releases are recommended/officially supported. |
| Django 5.2.16 release notes | https://docs.djangoproject.com/en/6.0/releases/5.2.16/ | Latest 5.2 patch observed in official docs is 5.2.16, dated 2026-07-07, with low-severity security fixes. |
| Python downloads | https://www.python.org/downloads/ | Active Python releases include 3.14 as bugfix and 3.12/3.11 as security branches; 3.15 is pre-release. |
| Python source releases | https://www.python.org/downloads/source/ | Latest Python 3.14 source release observed is 3.14.6, dated 2026-06-10. |
| Python 3.14.2 release | https://www.python.org/downloads/release/python-3142/ | Local Python 3.14.2 is an older 3.14 maintenance release and not the latest 3.14 micro. |
| HTMX releases/changelog | https://github.com/bigskysoftware/htmx/blob/master/CHANGELOG.md | Latest stable 2.x changelog entry observed is 2.0.10, dated 2026-04-21. |
| cPanel Application Manager | https://docs.cpanel.net/cpanel/software/application-manager/102/ | Application Manager deploys applications with Phusion Passenger. Actual provider enablement remains S01 evidence. |
| cPanel Python WSGI | https://docs.cpanel.net/knowledge-base/web-services/how-to-install-a-python-wsgi-application/ | cPanel documents Python WSGI app installation. Exact Truehost capability must be checked in the account. |

## Deprecations, Removals, Security, Breaking, Migration, and Compatibility Notes

- NIST AI RMF 1.0 is being revised; the project must not imply NIST certification or freeze future AI governance without review.
- OWASP ASVS identifiers can change between versions; evidence should cite `v5.0.0-<requirement>` style where specific controls are referenced.
- WCAG 2.2 removes Success Criterion 4.1.1 Parsing and adds nine criteria beyond 2.1; accessibility tests must target WCAG 2.2 AA where applicable.
- Django 6.0 is newer than the selected project line. Moving from Django 5.2 LTS to 6.x is out of S00 scope and would require an approved architecture/version change.
- Django 5.2.16 includes recent security fixes related to caching/private data exposure, GDALRaster, and DomainNameValidator newline acceptance. S02 should pin the latest compatible 5.2.x after a fresh review.
- Local Python 3.14.2 is older than the latest Python 3.14.6 observed. S01 must prove the exact Truehost Python version; S02 must lock to a compatible supported micro release actually available on Truehost.
- HTMX 2.0.10 includes fixes after 2.0.9. S02/S05 must vendor and checksum a stable 2.x asset locally; runtime CDN use remains prohibited.
- cPanel/Passenger documentation confirms the mechanism but not Truehost account availability. S01 is the final authority for Python App, Passenger, environment variables, restart behavior, logs, and resource constraints.

## Compatibility Conclusion

S00 is compatible to proceed as documentation/governance work only. It adds no production dependency, changes no runtime configuration, and introduces no Django, database, HTMX, cPanel, API, migration, or frontend behavior.

Runtime compatibility is not approved by S00. S01 must verify the actual Truehost account. S02 must create the dependency lock after official documentation and security review.

## Blocked or Deferred Decisions

| Decision | Owner | Deadline/gate | Status |
|---|---|---|---|
| Exact Truehost Python runtime | Oghenemaro | Before S02 dependency lock | Deferred to S01. |
| Exact MySQL/MariaDB engine and charset/collation | Oghenemaro | Before S06 database conventions | Deferred to S01. |
| Database driver selection | Oghenemaro | Before S02/S06 implementation | Deferred pending S01 engine and wheel/no-compilation evidence. |
| Vendored HTMX version and checksum | Oghenemaro | Before S05 design system | Deferred to S02/S05. |
| Production Django patch pin | Oghenemaro | Before S02 lock | Deferred to S02 after fresh review. |
