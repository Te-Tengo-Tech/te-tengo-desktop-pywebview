# How to contribute

## Workflow

1. Create a branch from `develop` (`main` only receives releases merged from `develop`) with the type and a short name: `feat/captura-contrapresion`, `fix/angulo-vertical`, `docs/protocolo`.
2. Set up the environment with `make instalar`. This also installs the pre-commit hooks.
3. Before pushing, `make revisar` and `make probar` must pass.
4. Open a *pull request* to `develop`. CI runs the same checks again.

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

## References

Conventional Commits. (s.f.). *Conventional Commits 1.0.0*. https://www.conventionalcommits.org/es/v1.0.0/
