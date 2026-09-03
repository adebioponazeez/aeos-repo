"""v19 tests: standards cited up front — the plan gate."""

from aeos.standards import STANDARDS_TEMPLATE, check_plan, cited_ids, init_template, registered_ids


class TestStandards:
    def test_template_registers_five_standards(self, tmp_path):
        p = init_template(tmp_path)
        assert registered_ids(p) == [f"STD-{i}" for i in range(1, 6)]

    def test_init_is_idempotent(self, tmp_path):
        init_template(tmp_path)
        p = init_template(tmp_path)
        assert p.read_text(encoding="utf-8") == STANDARDS_TEMPLATE

    def test_plan_with_valid_citation_passes(self, tmp_path):
        p = init_template(tmp_path)
        res = check_plan("ship the module per [STD-1] and [STD-3]", p)
        assert res["gated"] and res["ok"]
        assert res["cited"] == ["STD-1", "STD-3"]

    def test_plan_without_citation_is_refused(self, tmp_path):
        p = init_template(tmp_path)
        res = check_plan("just ship it, trust me", p)
        assert res["gated"] and not res["ok"] and res["cited"] == []

    def test_unregistered_citation_is_refused(self, tmp_path):
        p = init_template(tmp_path)
        res = check_plan("per [STD-99]", p)
        assert not res["ok"] and res["missing"] == ["STD-99"]

    def test_no_standards_file_no_gate(self, tmp_path):
        res = check_plan("anything goes", tmp_path / "STANDARDS.md")
        assert not res["gated"] and res["ok"]


class TestEndToEnd:
    def test_uncited_intent_fails_when_standards_registered(self, tmp_path):
        from aeos.pipeline import reference_run
        ws = tmp_path / "ws"
        ws.mkdir()
        init_template(ws)
        b = reference_run(ws, intent="Ship it, no citations")
        assert b["accepted"] is False
        assert "standards" in b["reason"] or "standards" in b

    def test_cited_intent_is_accepted(self, tmp_path):
        from aeos.pipeline import reference_run
        ws = tmp_path / "ws2"
        ws.mkdir()
        init_template(ws)
        b = reference_run(ws, intent="Ship it per [STD-1] and [STD-5]")
        assert b["accepted"] is True
        assert b["standards"]["cited"] == ["STD-1", "STD-5"]

    def test_standards_command(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["standards", "--workspace", str(tmp_path / "ws"),
                   "--init"])
        out = capsys.readouterr().out
        assert rc == 0 and "STANDARDS" in out and "STD-1" in out
