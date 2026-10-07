# How to contribute

## Branches (git flow)

| Branch | From | Merges into | Use |
|---|---|---|---|
| `feature/<module>-<topic>` | `develop` | `develop` | New work, e.g. `feature/captura-contrapresion` |
| `bugfix/<module>-<topic>` | `develop` | `develop` | Fixes found during development, e.g. `bugfix/pose-angulo-vertical` |
| `hotfix/<topic>` | `main` | `main` **and** `develop` | Urgent fixes to a release |
| `release/<version>` | `develop` | `main` and `develop` | Release preparation (no releases are cut yet) |

`main` only receives releases and hotfixes. Branch prefixes follow git flow; commit messages keep their Conventional Commit types (`feat:`, `fix:`, `ci:`, `docs:` …).

## Workflow

1. Create a branch from `develop` with one of the prefixes above.
2. Set up the environment with `make instalar`. This also installs the pre-commit hooks.
3. Before pushing, `make revisar` and `make probar` must pass.
4. Open a *pull request* to `develop` using the template: it lists the definition of done from [AGENTS.md](AGENTS.md).
5. **CI must be green before merging.** The organization is on the GitHub Free plan, where branch protection is not enforced for private repositories: nothing blocks a merge with failing checks, so **reviewers must open the checks tab and confirm every job passed**, including the Windows package, before merging.

## Continuous integration

| Workflow | Trigger | Jobs |
|---|---|---|
| [CI](.github/workflows/ci.yml) | Push to `main`/`develop`, every PR | `Lint, format and types` (ruff, mypy strict); `Tests and coverage` (pytest, coverage XML/HTML artifact and summary on the run page); then `Windows package` (PyInstaller build, smoke test, app artifact) |
| [Dependency audit](.github/workflows/audit.yml) | Weekly, manual, PRs that change dependencies | pip-audit of every locked dependency; scheduled runs fail on any known vulnerability |
| [OSV-Scanner](.github/workflows/osv-scanner.yml) | Weekly, manual, PRs that change dependencies | Scans `uv.lock`; scheduled runs fail on high or critical |

A new push cancels the superseded CI run of the same branch. Dependabot opens weekly update PRs to `develop` (`mediapipe` stays pinned, see ADR 0003).

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
