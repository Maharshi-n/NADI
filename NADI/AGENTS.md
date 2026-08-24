# AGENTS.md — read this first, every session

You are one of many sessions building NADI. You have no memory of previous
sessions. These files are the memory. Follow this protocol exactly.

---

## Start-of-session ritual (non-negotiable)

Read, in this order:

1. `docs/PROJECT.md` — what we are building and for whom. Never violate this.
2. `docs/CONTEXT.md` — architecture, stack, conventions, data model summary.
3. `docs/HANDOFF.md` — what the last session did, what is next.
4. `docs/PHASES.md` — find the current phase, read only that phase.

Then read only the specific files relevant to your task. Do not read the
whole repo.

If `HANDOFF.md` says the last session left something broken, fix that
before starting new work.

---

## End-of-session ritual (non-negotiable)

Before you finish, update these:

| File | When to update | What to write |
|---|---|---|
| `docs/HANDOFF.md` | **Every session** | Overwrite the "Current state" block. Append to the session log. |
| `docs/DECISIONS.md` | When you chose between real options | Append one ADR entry. Never edit past entries. |
| `docs/CONTEXT.md` | Only if architecture, stack, or conventions changed | Edit the affected section. |
| `docs/API.md` | If you added or changed an endpoint | Update the contract. |
| `docs/DATA_MODEL.md` | If you changed the schema | Update the table and add a migration note. |
| `docs/PHASES.md` | When a phase's acceptance criteria pass | Tick the boxes. Do not rewrite the phase. |
| `docs/PROJECT.md` | Almost never | Only if scope genuinely changed, and say why in DECISIONS.md. |

A session that writes code but not `HANDOFF.md` has wasted the next
session's first twenty minutes. This is the single most important rule
in this file.

---

## Rules of engagement

**Stay in phase.** If you are in Phase 3, do not build Phase 6 features
because they seem interesting. Out-of-phase work creates merge conflicts
between parallel sessions and half-finished features that nobody owns.

**Vertical slices only.** Every phase ends with something a human can
click. Never leave a phase with a backend that has no UI or a UI with no
data.

**Do not invent domain terms.** Use `docs/GLOSSARY.md`. If a term is
missing, add it there rather than coining a synonym. `CBI`, `days of
cover`, `PHC`, `CMHO` have exact meanings.

**Do not refactor outside your task.** If you spot something wrong
elsewhere, write it under "Known issues" in `HANDOFF.md` instead of
fixing it. Drive-by refactors break other sessions' in-flight work.

**Never hardcode secrets.** Env vars only. `.env.example` stays current.

**Never fake a feature in the UI.** A button that does nothing is worse
than no button. If a feature is not built, do not render its control.

**Do not change the seed data shape** without updating
`docs/DATA_MODEL.md` and flagging it loudly in `HANDOFF.md` — every
other session depends on it.

---

## Parallel session coordination

When multiple sessions run at once, claim your area in `HANDOFF.md`
under "In flight" before starting, using this format:

```
- [session-2026-08-24-b] backend forecasting — apps/api/forecast/*, ml/forecasting/*
```

Ownership boundaries designed to not collide:

| Area | Owns |
|---|---|
| Backend core | `apps/api/**` except `forecast/`, `optimizer/` |
| ML forecasting | `ml/forecasting/**`, `apps/api/forecast/**` |
| Optimizer | `ml/optimizer/**`, `apps/api/plan/**` |
| Command web | `apps/command-web/**` |
| PHC app | `apps/phc-app/**` |
| Data + infra | `data/**`, `docker-compose.yml`, deploy configs |

If you need to touch another area, note it in `HANDOFF.md` and keep the
change minimal.

---

## Quality bar

Before marking anything done:

- It runs from a clean clone via the documented command
- Seed data produces a non-empty screen
- No console errors on the happy path
- The acceptance criteria in `PHASES.md` actually pass, tested by hand
- `HANDOFF.md` reflects reality, not intention
