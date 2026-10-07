---
name: work
description: Work through docs/WORK_PLAN.md autonomously until every task is done. Use when the user types /work, says "work" or "continue", or asks to finish the plan.
---
Follow the loop in `docs/WORK_PLAN.md` exactly.

1. Read `AGENTS.md`, `docs/WORK_PLAN.md` and `docs/BLOCKERS.md`.
2. Take the first unchecked task. Read its stories in `docs/references/PRODUCT_BACKLOG.md` and its endpoints in `docs/AGENT_CONTRACT.md`. For UI tasks, open its PNG screens in `docs/references/desktop-prototype/screens/` and take the Spanish copy and markup from `docs/references/desktop-prototype/src/core.js`.
3. Implement it with tests (fake backend, fake video sources, injected clock). Make `make revisar probar` pass. Never skip or weaken a test, and never change the validated detection logic.
4. Check the task off, update `CHANGELOG.md`, then commit (Conventional Commits, English, no co-author line) and push.
5. **Immediately continue with the next task. Do not stop to ask for confirmation between tasks.**

Record missing decisions or hardware-only checks in `docs/BLOCKERS.md` and keep going with fakes. Finish only when no unchecked task remains, then open or update a pull request with a summary of the completed tasks, the blockers and the local test checklist.
