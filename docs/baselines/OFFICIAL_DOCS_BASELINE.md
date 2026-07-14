# Official Documentation and Compatibility Baseline

**Baseline reviewed:** 14 July 2026 UTC  
**Purpose:** starting evidence only. Codex must re-check the exact official documentation and installed versions at each build step. The actual Truehost cPanel account is the final runtime authority.

## Locked product decisions

- Production framework line: Django 5.2 LTS, latest compatible patch.
- Deployment runtime: cPanel/Passenger WSGI, no daemon.
- Frontend: Django templates plus a locally vendored stable HTMX 2.x asset and minimal JavaScript.
- Database: the actual Truehost MySQL/MariaDB engine, InnoDB and `utf8mb4`.
- Jobs: database-backed bounded management commands through cPanel Cron.
- No external runtime API, CDN, cache, queue, analytics, monitoring, CAPTCHA, or AI service.

## Current verified observations

| Area | Observation as of baseline date | Project decision |
|---|---|---|
| Django | Latest overall release is 6.0.7. Latest supported 5.2 LTS patch is 5.2.16; extended support runs to April 2028. | Stay on the latest 5.2.x LTS patch. Do not move to 6.x without an approved architecture/version change. |
| Python | Latest stable release shown by python.org is 3.14.6; Python 3.15 is still pre-release. Django 5.2 supports Python 3.10–3.14 and only the latest micro of each series. | Use the newest supported micro version actually available and proven in Truehost. Baseline preference remains Python 3.12 until S01 evidence approves another version. Never use a pre-release runtime. |
| HTMX | Official docs identify 2.x as the stable current line. GitHub shows stable v2.0.9 while 4.0 releases are beta. | Vendor and checksum an approved stable 2.x file locally. Do not use 4.0 beta or a CDN. Re-check for a newer stable 2.x release at S02/S05. |
| cPanel/Passenger | cPanel Application Manager uses Phusion Passenger; the hosting provider can enable/disable the feature. cPanel’s documentation was updated 8 July 2026. | S01 must prove the exact Truehost feature, Python version, environment variables, restart behavior and logs before production architecture is accepted. |
| Database | Django 5.2 officially supports MariaDB 10.5+ and MySQL 8.0.11+. | Record the exact Truehost engine/version and test transactions, locks, constraints, collation and selected driver against it. |
| Database driver | Truehost documents that GCC may be disabled for cPanel users and suggests pure-Python alternatives when `mysqlclient` cannot build. | Prefer a verified prebuilt compatible wheel only where preflight proves it. Otherwise approve and pin PyMySQL or MySQL Connector/Python after integration testing. |
| OpenAPI | OAS 3.2.0 is the newest published OpenAPI specification. The issued project contract is OpenAPI 3.1. | Keep the existing 3.1 contract until an approved contract/tooling migration. Do not silently change the `openapi` version. |
| HTTP errors | RFC 9457 defines Problem Details and `application/problem+json`, replacing RFC 7807. | Use RFC 9457 as specified by the project contract. |
| Security | OWASP ASVS 5.0.0 is the latest stable ASVS. | Use version-qualified ASVS 5.0.0 Level 2 references in evidence. |
| Accessibility | WCAG 2.2 is a W3C Recommendation and W3C advises its use for current policies. | Applicable staff, portal and signed-link journeys target WCAG 2.2 AA. |
| AI governance | NIST AI RMF 1.0 remains the project governance reference. | Use it as a voluntary risk-management reference, never as a certification claim; re-check current NIST status at S35. |
| Test/build tooling | Official stable documentation currently covers pip 26.x, pytest 9.x, coverage.py 7.x, Ruff, mypy, pytest-django and Playwright Python. | Exact versions are selected and hash-locked at S02 after Python compatibility review. Development tools must not become Truehost runtime dependencies. |

## Official primary sources

### Core runtime

- Django downloads/support: https://www.djangoproject.com/download/
- Django 5.2 documentation: https://docs.djangoproject.com/en/5.2/
- Django/Python compatibility: https://docs.djangoproject.com/en/5.2/faq/install/
- Django databases: https://docs.djangoproject.com/en/5.2/ref/databases/
- Django deployment checklist: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- Django security: https://docs.djangoproject.com/en/5.2/topics/security/
- Django authentication: https://docs.djangoproject.com/en/5.2/topics/auth/
- Django password management: https://docs.djangoproject.com/en/5.2/topics/auth/passwords/
- Django sessions: https://docs.djangoproject.com/en/5.2/topics/http/sessions/
- Django CSRF: https://docs.djangoproject.com/en/5.2/howto/csrf/
- Django transactions: https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- Django querysets/locking: https://docs.djangoproject.com/en/5.2/ref/models/querysets/
- Django migrations: https://docs.djangoproject.com/en/5.2/topics/migrations/
- Django email: https://docs.djangoproject.com/en/5.2/topics/email/
- Django file uploads: https://docs.djangoproject.com/en/5.2/topics/http/file-uploads/
- Django static deployment: https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/
- Django testing: https://docs.djangoproject.com/en/5.2/topics/testing/
- Python releases: https://www.python.org/downloads/
- Python standard library: https://docs.python.org/3/

### Frontend

- HTMX documentation: https://htmx.org/docs/
- HTMX releases: https://github.com/bigskysoftware/htmx/releases
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- WAI-ARIA Authoring Practices: https://www.w3.org/WAI/ARIA/apg/

### Hosting and data

- cPanel Application Manager: https://docs.cpanel.net/cpanel/software/application-manager/
- cPanel Python WSGI application: https://docs.cpanel.net/knowledge-base/web-services/how-to-install-a-python-wsgi-application/
- Truehost Django/cPanel guide: https://truehost.com/support/knowledge-base/how-to-deploy-django-web-application-on-shared-hosting-cpanel/
- Truehost shared-host resource usage: https://truehost.com/support/knowledge-base/understanding-resource-usage-shared-hosting/
- Truehost mysqlclient build limitation: https://truehost.com/support/knowledge-base/failed-building-wheel-for-mysqlclient-on-cpanel/
- MySQL reference: https://dev.mysql.com/doc/
- MariaDB server documentation: https://mariadb.com/docs/server/
- MySQL Connector/Python: https://dev.mysql.com/doc/connector-python/en/
- PyMySQL documentation: https://pymysql.readthedocs.io/

### HTTP and contracts

- RFC 9110 HTTP Semantics: https://www.rfc-editor.org/rfc/rfc9110.html
- RFC 9457 Problem Details: https://www.rfc-editor.org/rfc/rfc9457.html
- OpenAPI authoritative specification: https://spec.openapis.org/oas/latest.html

### Security and AI governance

- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- OWASP API Security Top 10: https://owasp.org/API-Security/
- OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
- NIST AI RMF: https://www.nist.gov/itl/ai-risk-management-framework

### Development and validation tools

- pip repeatable installs/hash checking: https://pip.pypa.io/en/stable/topics/repeatable-installs/
- Python packaging/pyproject: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Ruff: https://docs.astral.sh/ruff/
- mypy: https://mypy.readthedocs.io/en/stable/
- pytest: https://docs.pytest.org/en/stable/
- pytest-django: https://pytest-django.readthedocs.io/en/latest/
- coverage.py: https://coverage.readthedocs.io/en/latest/
- Playwright Python: https://playwright.dev/python/docs/intro

## Freshness procedure for every prompt

1. Run the installed tool’s version command.
2. Read the documentation matching that version or selected major/minor line.
3. Read release notes from the installed version through the latest compatible patch.
4. Search official docs for deprecated/removed/breaking/security/compatibility notices.
5. Confirm Truehost runtime compatibility and wheel/no-compilation behavior.
6. Record findings in `docs/compatibility/Sxx-*.md`.
7. Propose rather than perform a major upgrade or unapproved dependency addition.
