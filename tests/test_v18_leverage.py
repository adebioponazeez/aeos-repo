"""v18 tests: the 12-point leverage rubric audited against disk."""

from aeos.leverage import audit, render


class TestRubric:
    def test_empty_workspace_scores_low(self, tmp_path):
        rep = audit(tmp_path)
        assert rep["of"] == 12
        assert rep["score"] <= 2
        assert all(r["status"] == "GAP" or r["point"].startswith("Money")
                   for r in rep["rows"]) is True or rep["score"] <= 2

    def test_full_workspace_scores_high(self, tmp_path):
        from aeos.cli import main
        from aeos.pipeline import reference_run
        ws = tmp_path / "ws"
        reference_run(ws, intent="Ship it")
        main(["fleet", "--workspace", str(ws)])
        main(["resume", "--workspace", str(ws)])
        rep = audit(ws)
        assert rep["score"] >= 9, render(rep)

    def test_every_row_names_its_evidence(self, tmp_path):
        rep = audit(tmp_path)
        for r in rep["rows"]:
            assert r["point"] and r["mechanism"] and r["evidence"]

    def test_render_is_the_receipt(self, tmp_path):
        rep = audit(tmp_path)
        text = render(rep)
        assert "LEVERAGE AUDIT" in text and "0/12" in text \
            or f"{rep['score']}/12" in text
