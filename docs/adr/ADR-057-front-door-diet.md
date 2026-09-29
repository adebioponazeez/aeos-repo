# ADR-057: The Front Door Diet — one door, four rooms

**Status: ACCEPTED (v40.0.0)**

## Context

The audit's register of structural debt named cli.py a 1,129-line
god module: 39 commands' registration and behavior interleaved in
one `main()`, with helpers, lazy imports and guarded fallback chains
(mcp ×4, dashboard ×2) all in one scope. The scope itself hid a
defect: `m = vault.init()` was assigned and never used, masked from
pyflakes by an unrelated `m` loop variable in another command's
branch — single-scope rot.

## Decision

1. **cli.py is a thin front door**: `_build_parser()` (declarative
   registration), `_menu()` (bare `aeos` prints the grouped menu —
   RUN / INSPECT / OPERATE / EXTEND — instead of argparse noise),
   and routing. No behavior.
2. **Behavior lives in four surface modules**, moved verbatim:
   `cli_run` (9 commands: plans that execute), `cli_inspect` (10:
   reading the system's truth), `cli_operate` (10: keeping the
   machine running), `cli_extend` (10: protocols, hooks,
   federation). `_spine` lives with run; `_demo_orchestrator` with
   the hooks demo that still uses it.
3. **The menu and the routing share one source of truth**: the
   surface tuples `_RUN/_INSPECT/_OPERATE/_EXTEND`. A test holds
   registration == menu == routing (39 commands, no orphans, no
   phantoms).
4. **Command count is a claim**: the README now says 39 (it said
   37 — a drift the diet exposed; nothing checked it before).
5. **Hygiene law applies to the new modules individually**:
   pyflakes-zero on each; the split surfaced one pre-existing dead
   assignment (fixed).

## Consequences

- cli.py: 1,129 → ~300 lines, all declarative; the four rooms are
  157–298 lines each.
- `from aeos.cli import main` is unchanged — 27 test files and
  every receipt keep working; behavior differences: bare `aeos`
  now exits 2 with the grouped menu.
- Room-to-room calls would now be an import (visible, reviewable)
  instead of a shared local — the next de-disjointing work is
  mechanically obvious.
- What the diet does NOT do: merge or retire commands (37 vs 39
  was a counting error, not a design); aliasing, `aeos run-demo`
  retirement and deeper grouping remain open for the Outside-Eyes
  round, informed by a real operator's confusion report.
