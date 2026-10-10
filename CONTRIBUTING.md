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
5. **CI must be green before merging.** The rulesets `proteger-develop` and `proteger-main` require a pull request with one approval and green checks, and block force-pushes and deletions. `ci-ok`, the last job of CI, passes only when every CI job passed (the Windows package included), so it is the one check to require; pull requests into `main` also need `release-gate`, and every pull request `pr-title`.

## Continuous integration

| Workflow | Trigger | Jobs |
|---|---|---|
| [CI](.github/workflows/ci.yml) | Every PR; push to `develop`; called by Release on the release branch | `Lint, format and types` (ruff, mypy strict); `Tests and coverage` (pytest, coverage XML/HTML artifact and summary on the run page); then `Windows package` (PyInstaller build, smoke test, app artifact); `ci-ok` (every job passed). On PRs into `main` only `ci-ok` runs: the commit was tested when its candidate was built |
| [PR title](.github/workflows/pr-title.yml) | Every PR | `pr-title`: the title is a Conventional Commit |
| [Release gate](.github/workflows/release-gate.yml) | PRs into `main` | `release-gate`: merging puts into `main` exactly the tree of an approved release candidate |
| [Dependency audit](.github/workflows/audit.yml) | Weekly, manual, PRs that change dependencies | pip-audit of every locked dependency; scheduled runs fail on any known vulnerability |
| [OSV-Scanner](.github/workflows/osv-scanner.yml) | Weekly, manual, PRs that change dependencies | Scans `uv.lock`; scheduled runs fail on high or critical |
| [Release](.github/workflows/release.yml) | Push to `release/*` or `hotfix/*`; PRs that change `packaging/` or `.github/scripts/` (builds only) | Version check (the branch, `pyproject.toml` and `__version__` agree); CI called on the commit; the end-to-end test of the agent against the production API image; Windows installer (PyInstaller, smoke test, Inno Setup, install/uninstall test, optional signing) and macOS `.dmg` (`ENABLE_MAC_DMG`; ad-hoc or notarized) built once and stored as the pre-release `v<version>-rc.N` (SBOM, SHA-256, provenance and SBOM attestations, tree hash, build number); `staging` (approval) uploads the candidate to R2 `staging/` and checks the downloads; opens the pull request to `main` as the release bot ([docs/RELEASES.md](docs/RELEASES.md)) |
| [Produccion](.github/workflows/produccion.yml) | Push to `main` (a merged release or hotfix) | Finds the approved candidate whose tree equals main's (`buscar_candidata.sh`, as the release gate); `produccion` (approval) verifies its SHA-256 and uploads the same files to the R2 production keys; only after that succeeded, tag `v<version>` and the GitHub Release (CHANGELOG notes, the candidate's files with `ENABLE_DESKTOP_GITHUB_RELEASE`) and the back-merge pull request `main → develop` (release bot). Nothing is built; with every channel off, nothing is tagged |
| [Rollback](.github/workflows/rollback.yml) | Manual, on `main`, with a version | `produccion` (approval) puts the verified binaries of an earlier release back on the R2 production keys |

Each commit is tested once per stage: on its pull request, after the merge into `develop`, and on the release branch, where Release calls CI. The workflows open their pull requests as the GitHub App te-tengo-release-bot, so the pull request checks run on them. A new push cancels the superseded CI run of the same pull request. Dependabot opens weekly update PRs to `develop` (`mediapipe` stays pinned, see ADR 0003).

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
