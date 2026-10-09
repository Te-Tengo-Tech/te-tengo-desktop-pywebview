# How to contribute

## Branches (git flow)

| Branch | From | Merges into | Use |
|---|---|---|---|
| `feature/<module>-<topic>` | `develop` | `develop` | New work, e.g. `feature/captura-contrapresion` |
| `bugfix/<module>-<topic>` | `develop` | `develop` | Fixes found during development, e.g. `bugfix/pose-angulo-vertical` |
| `hotfix/<version>` | `main` | `main`, then `develop` (back-merge) | Urgent fixes to a released version, e.g. `hotfix/0.3.1` (the next patch version) |
| `release/<version>` | `develop` | `main`, then `develop` (back-merge) | Release preparation, e.g. `release/0.3.0`: each push builds a release candidate `v<version>-rc.N`; QA fixes go here (directly or from a `bugfix/*` branch of it) |

`main` only receives releases and hotfixes, and only receives the files a candidate was tested with: production refuses a `main` whose tree differs from every candidate ([docs/RELEASES.md](docs/RELEASES.md)). Branch prefixes follow git flow; commit messages keep their Conventional Commit types (`feat:`, `fix:`, `ci:`, `docs:` …).

## Workflow

1. Create a branch from `develop` with one of the prefixes above.
2. Set up the environment with `make instalar`. This also installs the pre-commit hooks.
3. Before pushing, `make revisar` and `make probar` must pass.
4. Open a *pull request* to `develop` using the template: it lists the definition of done from [AGENTS.md](AGENTS.md).
5. **CI must be green before merging.** The rulesets `proteger-develop` and `proteger-main` require a pull request with one approval and the `Lint, format and types` and `Tests and coverage` checks, and block force-pushes and deletions. The Windows package job is not a required check: reviewers confirm it passed too.

## Continuous integration

| Workflow | Trigger | Jobs |
|---|---|---|
| [CI](.github/workflows/ci.yml) | Push to `main`, `develop`, `release/**`, `hotfix/**`; every PR | `Lint, format and types` (ruff, mypy strict); `Tests and coverage` (pytest, coverage XML/HTML artifact and summary on the run page); then `Windows package` (PyInstaller build, smoke test, app artifact) |
| [Dependency audit](.github/workflows/audit.yml) | Weekly, manual, PRs that change dependencies | pip-audit of every locked dependency; scheduled runs fail on any known vulnerability |
| [OSV-Scanner](.github/workflows/osv-scanner.yml) | Weekly, manual, PRs that change dependencies | Scans `uv.lock`; scheduled runs fail on high or critical |
| [Release](.github/workflows/release.yml) | Push to `release/*` or `hotfix/*`; PRs that change `packaging/` or `.github/scripts/` (builds only) | Version check; lint and tests; Windows installer (PyInstaller, smoke test, Inno Setup, install/uninstall test, optional signing) and macOS `.dmg` (`ENABLE_MAC_DMG`; ad-hoc or notarized) built once and stored as the pre-release `v<version>-rc.N` (SHA-256, tree hash, build number); `staging` (approval) uploads the candidate to R2 `staging/` and checks the downloads; opens the pull request to `main` ([docs/RELEASES.md](docs/RELEASES.md)) |
| [Produccion](.github/workflows/produccion.yml) | Push to `main` (a merged release or hotfix) | Finds the candidate whose tree equals main's; `produccion` (approval) verifies its SHA-256 and uploads the same files to the R2 production keys; only then tag `v<version>` and the GitHub Release (CHANGELOG notes, the candidate's binaries with `ENABLE_DESKTOP_GITHUB_RELEASE`); back-merge pull request `main → develop`. Nothing is built |
| [Rollback](.github/workflows/rollback.yml) | Manual, on `main`, with a version | `produccion` (approval) puts the verified binaries of an earlier release back on the R2 production keys |

CI also runs on pushes to `release/**`, `hotfix/**` and `main` because the pull requests the workflows open with `GITHUB_TOKEN` start no workflows: the required checks come from the push run on the same commit. A new push cancels the superseded CI run of the same branch. Dependabot opens weekly update PRs to `develop` (`mediapipe` stays pinned, see ADR 0003).

## Commit messages

They follow **Conventional Commits 1.0.0**: `type(scope): description in the imperative mood`.

| Type | Use |
|---|---|
| `feat` | New functionality |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Tests |
| `refactor` | Code change that does not change behavior |
| `build` / `ci` / `chore` | Dependencies, packaging, CI and maintenance |

Examples:

```
feat(clasificacion): add unstable movement rule
fix(pose): convert landmarks to pixels before computing the ratio
docs(adr): record decision on VIDEO mode
```

The `conventional-pre-commit` hook rejects messages that do not follow the format.

## Code rules

- Module and class names follow the components of the logical architecture ([docs/architecture.md](docs/architecture.md)).
- `clasificacion/` does no I/O.
- **Every new formula or threshold** is documented in [docs/classification-spec.md](docs/classification-spec.md), with its source or marked as *[Adaptation]*.
- **Architecture decisions** are recorded as ADRs in [docs/adr/](docs/adr/).
- **Secrets are never pushed:** the installation file with the real credential stays on the household PC (only `config.ejemplo.toml` is versioned), and pre-commit checks that there are no private keys.

## Community

- [Code of Conduct](.github/CODE_OF_CONDUCT.md)
- [Security policy](.github/SECURITY.md)

## References

Conventional Commits. (s.f.). *Conventional Commits 1.0.0*. https://www.conventionalcommits.org/es/v1.0.0/
