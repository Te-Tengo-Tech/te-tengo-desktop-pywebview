# Security Policy — te-tengo-desktop-pywebview

Te Tengo handles sensitive data: clips of older adults at home, alerts and family contact details. Please report problems privately and quickly.

## Supported branches

| Branch | Supported |
|---|---|
| `develop` | Yes — fixes land here first |
| `main` | Yes — receives fixes through `hotfix/*` branches |
| Older tags and feature branches | No |

## Reporting a vulnerability

**Do not open an issue or pull request** for a vulnerability or an exposed secret (installation credentials, camera tokens, configuration files with real values).

The repository is private, so GitHub's *private vulnerability reporting* is not available. Instead, e-mail the maintainer, **Jhosepmyr Orlando Gutiérrez Soto** — `jhosepmyrgutierrezsoto@gmail.com`, with:

- a description of the issue and its impact;
- steps to reproduce, or the file and commit where a secret is exposed;
- relevant logs or responses, with tokens and personal data removed.

We acknowledge reports within **72 hours** and aim to fix confirmed issues within **7 days**. An exposed secret is **rotated immediately**; removing it from history comes after the rotation.

## Security practices in this repository

- **No secrets in git.** Only `config.ejemplo.toml` is versioned; the installation file with the real credential stays on the household PC. The pre-commit hook `detect-private-key` blocks private keys.
- **Secrets are never logged:** neither the installation credential nor the camera token.
- **Privacy by design:** no frames are written to disk except the clip of an event until it is uploaded, and the clip is deleted after a successful upload. Without consent, or while paused, the webcam frames never reach the classifier.

## Automated scanning

| Check | Where | When |
|---|---|---|
| Dependabot version updates (uv, GitHub Actions; `mediapipe` stays pinned per ADR 0003) | [`dependabot.yml`](dependabot.yml) | Weekly, PRs to `develop` |
| pip-audit on every locked dependency (fails on any known vulnerability) | [`workflows/audit.yml`](workflows/audit.yml) | Weekly, on demand, and report-only on PRs that change dependencies |
| OSV-Scanner on `uv.lock` (fails on high or critical) | [`workflows/osv-scanner.yml`](workflows/osv-scanner.yml) | Weekly, on demand, and report-only on PRs that change dependencies |
| Lint, strict types, tests with coverage and the Windows package smoke test | [`workflows/ci.yml`](workflows/ci.yml) | Every PR, every push to `develop`, and every release candidate (called by `release.yml`) |
| SBOM, build provenance and SBOM attestations of every release candidate | [`workflows/release.yml`](workflows/release.yml) | Every push to `release/*` and `hotfix/*` |

Reports are uploaded as workflow artifacts and summarised on the run page.

## Limitations of the current plan

The `Te-Tengo-Tech` organization uses the GitHub **Free** plan with private repositories. On that plan:

- **No CodeQL / code scanning.** Code scanning and SARIF uploads require GitHub Advanced Security (GitHub Code Security), which is not available for private repositories on Free. That is why there is no `codeql.yml`; the dependency scanners above run without it and publish their reports as artifacts instead.
- **No secret scanning or push protection** for private repositories (GitHub Secret Protection). The `.gitignore`, the `detect-private-key` pre-commit hook and code review are the only guards; never commit `config.local.toml`, `.env` or other real configuration files.
- **No branch protection or rulesets.** Merging into `develop` or `main` is not blocked by failing checks, so reviewers must confirm that CI is green before merging.
- **Dependabot alerts** can still be enabled under *Settings → Code security* (they use the dependency graph and are free); version updates already run from `dependabot.yml`.
