## What and why

<!-- What does this pull request change, and why? -->

**Area:** <!-- deteccion | captura | backend | envios | ui | bandeja | packaging | scripts | build | ci | docs -->

**Story / task:** <!-- e.g. US-05, WORK_PLAN T12. Closes #… -->

## Type of change

- [ ] `feat` — new feature
- [ ] `fix` — bug fix
- [ ] `refactor` — no behavior change
- [ ] `test` — tests only
- [ ] `docs` — documentation only
- [ ] `build` / `ci` / `chore` — dependencies, packaging, CI or maintenance

## Definition of done

- [ ] The pull request targets `develop` (not `main`), from a `feature/*` or `bugfix/*` branch (`hotfix/*` targets `main`)
- [ ] Every acceptance criterion the task names is covered by a test
- [ ] Backend calls match [`docs/AGENT_CONTRACT.md`](../docs/AGENT_CONTRACT.md) exactly and are tested against the fake backend (`httpx.MockTransport`)
- [ ] `make revisar probar` passes locally (ruff, mypy strict, pytest); no test was skipped or weakened
- [ ] The validation tools still run: `uv run python scripts/evaluar.py --help` and `uv run python scripts/probar_camara.py --help`
- [ ] The validated behaviour of `te_tengo_deteccion` is unchanged, or a new ADR explains the change
- [ ] Conventional Commits in English, with no co-author line
- [ ] The task is checked off in [`docs/WORK_PLAN.md`](../docs/WORK_PLAN.md) and `CHANGELOG.md` is updated
- [ ] No secrets (installation credential, camera token, `config.local.toml`, `.env`) or frames are committed
- [ ] CI is green, including the Windows package (branch protection is not enforced on our plan: reviewers check it before merging)

## How to test

<!-- e.g. uv run te-tengo-captura --backend-falso --config config.ejemplo.toml -->
