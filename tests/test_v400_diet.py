"""v40.0.0 — THE FRONT DOOR DIET (ADR-057): one door, four rooms.

The audit's register of structural debt named cli.py a 1,100-line
god module. The diet: cli.py is a thin front door (parser + grouped
menu + routing); behavior lives in four surface modules — cli_run,
cli_inspect, cli_operate, cli_extend. These tests hold the door
honest: every registered command is on the grouped menu, every menu
entry routes to the surface that owns it, every command's --help
works, and the spine still runs through the new door.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from aeos.cli import (_EXTEND, _INSPECT, _OPERATE, _RUN, _build_parser,
                      main)

_REPO = Path(__file__).resolve().parent.parent
_ALL = sorted(_RUN + _INSPECT + _OPERATE + _EXTEND)


def _choices():
    sub = [a for a in _build_parser()._actions
           if isinstance(a, argparse._SubParsersAction)][0]
    return set(sub.choices)


class TestTheDoor:
    def test_bare_aeos_prints_the_grouped_menu(self, capsys):
        assert main([]) == 2
        out = capsys.readouterr().out
        for label in ("RUN", "INSPECT", "OPERATE", "EXTEND"):
            assert f"  {label}" in out
        assert "the spine:" in out

    def test_every_registered_command_is_on_the_menu(self, capsys):
        main([])
        out = capsys.readouterr().out
        for cmd in _ALL:
            assert cmd in out, f"{cmd} missing from the grouped menu"

    def test_registration_matches_the_surfaces_exactly(self):
        # no orphan commands, no phantom menu entries — the door and
        # the rooms agree
        assert _choices() == set(_ALL)
        assert len(_ALL) == len(set(_ALL)) == 39
        assert not (set(_RUN) & set(_INSPECT) & set(_OPERATE)
                    & set(_EXTEND))

    def test_every_command_help_works(self, capsys):
        for cmd in _ALL:
            with pytest.raises(SystemExit) as e:
                main([cmd, "--help"])
            assert e.value.code == 0, cmd
            assert capsys.readouterr().out.strip()


class TestTheRooms:
    def test_four_surface_modules_own_dispatch(self):
        from aeos import (cli_extend, cli_inspect, cli_operate, cli_run)
        for mod in (cli_run, cli_inspect, cli_operate, cli_extend):
            assert callable(mod.dispatch)

    def test_routing_sends_each_command_to_its_surface(self, monkeypatch):
        import aeos.cli as door
        from aeos import cli_extend, cli_inspect, cli_operate, cli_run
        seen = []
        for mod in (cli_run, cli_inspect, cli_operate, cli_extend):
            monkeypatch.setattr(mod, "dispatch",
                                lambda a, m=mod: seen.append(m.__name__) or 7)
        monkeypatch.setattr("sys.argv", ["aeos", "selftest"])
        assert door.main() == 7
        assert seen == ["aeos.cli_inspect"], "selftest must route to INSPECT"

    def test_the_spine_survives_the_diet(self, tmp_path, monkeypatch,
                                         capsys):
        ws = tmp_path / "ws"
        monkeypatch.setattr(
            "sys.argv", ["aeos", "run", "--graph",
                         str(_REPO / "examples" / "ship-graph.dot"),
                         "--style", str(_REPO / "examples" / "routing.style"),
                         "--workspace", str(ws)])
        assert main() == 0
        assert "SPINE RUN — ACCEPTED" in capsys.readouterr().out
        assert (ws / "seed" / "core.py").exists()
