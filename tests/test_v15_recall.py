"""v15 tests: layered FTS recall — keys, snippets, budget, savings."""

from aeos.contracts import MemoryClass
from aeos.memory import MemoryRecord, MemoryStore
from aeos.recall import RecallIndex


def stocked_store(tmp_path):
    store = MemoryStore(tmp_path / "m.jsonl")
    store.write(MemoryRecord(key="semantic::deploy",
                             mclass=MemoryClass.SEMANTIC,
                             value="deploy: tests-first then gate-check; "
                                   "validated 4x; never trust green text",
                             source="distiller",
                             evidence=["distilled from 4 episodes"]))
    store.write(MemoryRecord(key="semantic::research",
                             mclass=MemoryClass.SEMANTIC,
                             value="research: sourced brief with ranked "
                                   "findings; cite or silence",
                             source="distiller",
                             evidence=["distilled from 3 episodes"]))
    for i in range(5):
        store.write(MemoryRecord(key=f"lesson::build-core::{i}",
                                 mclass=MemoryClass.EPISODIC,
                                 value="build-core episode with the usual "
                                       "tests-first narrative padding " * 3,
                                 source="loop"))
    return store


class TestRecallIndex:
    def test_build_indexes_every_record(self, tmp_path):
        idx = RecallIndex(str(tmp_path / "r.sqlite"), stocked_store(tmp_path))
        assert idx.build() == 7

    def test_layer0_key_hits_are_cheap(self, tmp_path):
        idx = RecallIndex(str(tmp_path / "r.sqlite"), stocked_store(tmp_path))
        idx.build()
        rep = idx.recall("deploy")
        l0 = rep.layers[0]
        assert "semantic::deploy" in l0.items
        assert l0.tokens <= len(l0.items)      # ~1 token per key

    def test_snippets_respect_the_budget(self, tmp_path):
        idx = RecallIndex(str(tmp_path / "r.sqlite"), stocked_store(tmp_path))
        idx.build()
        rep = idx.recall("tests narrative", budget=40)
        assert rep.recall_tokens <= 40

    def test_layered_recall_beats_full_scan(self, tmp_path):
        idx = RecallIndex(str(tmp_path / "r.sqlite"), stocked_store(tmp_path))
        idx.build()
        rep = idx.recall("deploy", budget=120)
        assert rep.saving > 0
        assert rep.full_scan_tokens > rep.recall_tokens

    def test_recall_never_mutates_the_store(self, tmp_path):
        store = stocked_store(tmp_path)
        idx = RecallIndex(str(tmp_path / "r.sqlite"), store)
        idx.build()
        before = sorted(store.records)
        idx.recall("deploy research build-core")
        assert sorted(store.records) == before

    def test_full_layer_only_when_budget_remains(self, tmp_path):
        idx = RecallIndex(str(tmp_path / "r.sqlite"), stocked_store(tmp_path))
        idx.build()
        tight = idx.recall("deploy", budget=2)     # L0 eats it all
        assert [l.layer for l in tight.layers] == [0]
        rich = idx.recall("deploy", budget=400)
        assert 2 in [l.layer for l in rich.layers]

    def test_rebuild_is_idempotent(self, tmp_path):
        idx = RecallIndex(str(tmp_path / "r.sqlite"), stocked_store(tmp_path))
        assert idx.build() == 7 and idx.build() == 7


class TestEndToEnd:
    def test_reference_run_reports_recall_savings(self, tmp_path):
        from aeos.pipeline import reference_run
        b = reference_run(tmp_path / "ws", intent="Ship it")
        rec = b["dividend"]["recall"]
        assert rec["saving"] >= 0 and rec["full_scan"] > 0

    def test_recall_command_renders(self, tmp_path, capsys):
        from aeos.pipeline import reference_run
        from aeos.cli import main
        reference_run(tmp_path / "ws2", intent="Ship it")
        rc = main(["recall", "--workspace", str(tmp_path / "ws2"),
                   "--query", "deploy research"])
        out = capsys.readouterr().out
        assert rc == 0 and "L0" in out and "L1" in out
