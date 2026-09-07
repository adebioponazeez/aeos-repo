"""v36 tests: the notary — save-proof certificates, the merkle root,
the edge outbox, and the SEF-X capability-permanence law."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from aeos import merkle, outbox
from aeos.saveproof import authenticate, run_notary, verify, write

REPO = Path(__file__).resolve().parents[1]


def _make_tree(root: Path) -> None:
    (root / "sub").mkdir(parents=True, exist_ok=True)
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    (root / "sub" / "b.txt").write_text("beta", encoding="utf-8")


class TestMerkle:
    def test_empty_tree_has_constant_root(self, tmp_path):
        snap = merkle.snapshot(tmp_path)
        assert snap["root"] == merkle.EMPTY_ROOT
        assert snap["files"] == 0 and snap["bytes"] == 0

    def test_deterministic_across_rebuilds(self, tmp_path):
        _make_tree(tmp_path)
        first = merkle.snapshot(tmp_path)["root"]
        for p in sorted(tmp_path.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
        _make_tree(tmp_path)
        assert merkle.snapshot(tmp_path)["root"] == first

    def test_known_vector(self, tmp_path):
        # an independent restatement of the documented algorithm:
        # leaf = H(prefix + path + NUL + sha256(content)); node = H(...)
        _make_tree(tmp_path)

        def leaf(path, content):
            return hashlib.sha256(
                b"aeos-merkle-leaf\x00" + path.encode()
                + b"\x00" + hashlib.sha256(content).hexdigest().encode()
            ).digest()

        la, lb = leaf("a.txt", b"alpha"), leaf("sub/b.txt", b"beta")
        expected = hashlib.sha256(
            b"aeos-merkle-node\x00" + la + lb).hexdigest()
        assert merkle.snapshot(tmp_path)["root"] == expected

    def test_content_change_moves_the_root(self, tmp_path):
        _make_tree(tmp_path)
        before = merkle.snapshot(tmp_path)["root"]
        (tmp_path / "a.txt").write_text("ALPHA", encoding="utf-8")
        assert merkle.snapshot(tmp_path)["root"] != before

    def test_rename_moves_the_root(self, tmp_path):
        # leaves are path-bound: same bytes under a new name is a
        # different tree — renames are not free
        _make_tree(tmp_path)
        before = merkle.snapshot(tmp_path)["root"]
        (tmp_path / "a.txt").rename(tmp_path / "c.txt")
        assert merkle.snapshot(tmp_path)["root"] != before

    def test_volatile_trees_do_not_count(self, tmp_path):
        _make_tree(tmp_path)
        baseline = merkle.snapshot(tmp_path)["root"]
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"junk")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref", encoding="utf-8")
        (tmp_path / "save-proofs").mkdir()
        (tmp_path / "save-proofs" / "c.json").write_text("{}", encoding="utf-8")
        assert merkle.snapshot(tmp_path)["root"] == baseline

    def test_build_metadata_never_counts(self, tmp_path):
        # v36.0.1 regression: egg-info is regenerated on every install
        # and its content depends on WHEN pip ran — a warm worktree and
        # a cold clone must hash to the SAME root. Found the hard way:
        # the fresh clone refused v36.0.0's certificate.
        _make_tree(tmp_path)
        baseline = merkle.snapshot(tmp_path)["root"]
        egg = tmp_path / "src" / "aeos.egg-info"
        egg.mkdir(parents=True)
        (egg / "SOURCES.txt").write_text("generated-tuesday",
                                         encoding="utf-8")
        (egg / "PKG-INFO").write_text("also-generated", encoding="utf-8")
        (tmp_path / ".DS_Store").write_bytes(b"\x00\x01finder")
        assert merkle.snapshot(tmp_path)["root"] == baseline

    def test_diff_names_every_change(self, tmp_path):
        _make_tree(tmp_path)
        pre = merkle.snapshot(tmp_path)
        (tmp_path / "a.txt").write_text("changed", encoding="utf-8")
        (tmp_path / "new.txt").write_text("n", encoding="utf-8")
        (tmp_path / "sub" / "b.txt").unlink()
        d = merkle.diff(pre, merkle.snapshot(tmp_path))
        changes = {(e["change"], e["path"]) for e in d["events"]}
        assert ("modified", "a.txt") in changes
        assert ("added", "new.txt") in changes
        assert ("removed", "sub/b.txt") in changes
        assert d["total"] == 3 and not d["truncated"]


class TestSaveProof:
    def test_clean_run_is_verified(self, tmp_path):
        _make_tree(tmp_path)
        cert = run_notary(tmp_path, [sys.executable, "-c", "pass"])
        assert cert["outcome"] == "verified"
        assert cert["pre_root"] == cert["post_root"]
        assert cert["test_exit"] == 0 and cert["drift"]["total"] == 0
        ok, why = verify(cert)
        assert ok, why

    def test_certificate_is_deterministic(self, tmp_path):
        _make_tree(tmp_path)
        cmd = [sys.executable, "-c", "pass"]
        one = json.dumps(run_notary(tmp_path, cmd), sort_keys=True)
        two = json.dumps(run_notary(tmp_path, cmd), sort_keys=True)
        assert one == two        # no clocks, no paths-that-move, no timing

    def test_drifted_run_names_the_files(self, tmp_path):
        _make_tree(tmp_path)
        cert = run_notary(tmp_path, [sys.executable, "-c",
                                     "open('leftover.txt','w').write('x')"])
        assert cert["outcome"] == "drifted"
        assert cert["pre_root"] != cert["post_root"]
        assert {"change": "added", "path": "leftover.txt"} in \
            cert["drift"]["events"]

    def test_failed_run_is_named(self, tmp_path):
        _make_tree(tmp_path)
        cert = run_notary(tmp_path, [sys.executable, "-c",
                                     "raise SystemExit(3)"])
        assert cert["outcome"] == "tests-failed"
        assert cert["test_exit"] == 3 and cert["drift"]["total"] == 0

    def test_drift_and_failure_are_both_named(self, tmp_path):
        _make_tree(tmp_path)
        cert = run_notary(
            tmp_path,
            [sys.executable, "-c",
             "open('junk.txt','w').write('x'); raise SystemExit(1)"])
        assert cert["outcome"] == "drifted-and-failed"
        assert cert["drift"]["total"] == 1

    def test_tampered_certificate_refused(self, tmp_path):
        _make_tree(tmp_path)
        cert = run_notary(tmp_path, [sys.executable, "-c", "pass"])
        cert["test_exit"] = 5                 # an edit after the fact
        ok, why = verify(cert)
        assert not ok and "digest mismatch" in why

    def test_digest_consistent_lie_still_refused(self, tmp_path):
        # a forger who re-signs is caught by arithmetic: "verified"
        # must mean exit 0 AND equal roots
        _make_tree(tmp_path)
        cert = run_notary(tmp_path, [sys.executable, "-c",
                                     "raise SystemExit(1)"])
        cert["outcome"] = "verified"
        authenticate(cert)                     # re-sign the lie
        ok, why = verify(cert)
        assert not ok and "arithmetic disagrees" in why

    def test_tree_mismatch_refused(self, tmp_path):
        _make_tree(tmp_path)
        cert = run_notary(tmp_path, [sys.executable, "-c", "pass"])
        (tmp_path / "a.txt").write_text("mutated", encoding="utf-8")
        ok, why = verify(cert, root=tmp_path)
        assert not ok and "no longer matches" in why

    def test_hmac_upgrade_needs_the_key(self, tmp_path):
        _make_tree(tmp_path)
        cert = run_notary(tmp_path, [sys.executable, "-c", "pass"],
                          key="shared-secret")
        assert cert["auth"]["scheme"] == "hmac-sha256"
        assert verify(cert, key="shared-secret")[0]
        assert not verify(cert)[0]             # no key -> cannot check
        assert not verify(cert, key="wrong")[0]

    def test_ledger_write_roundtrips(self, tmp_path):
        _make_tree(tmp_path)
        cert = run_notary(tmp_path, [sys.executable, "-c", "pass"])
        path = write(cert, tmp_path / "save-proofs")
        assert path.name.startswith("save-proof-")
        back = json.loads(path.read_text(encoding="utf-8"))
        assert verify(back)[0]


class TestOutbox:
    def test_enqueue_is_idempotent(self, tmp_path):
        db = tmp_path / "outbox.db"
        conn = outbox.connect(db)
        try:
            one = outbox.enqueue(conn, "https://collector.example/v1", "r1")
            two = outbox.enqueue(conn, "https://collector.example/v1", "r1")
            assert one["created"] and not two["created"]
            assert one["id"] == two["id"]       # ONE row, not two
            outbox.enqueue(conn, "https://collector.example/v1", "r2")
            c = outbox.counts(conn)
            assert c["pending"] == 2
        finally:
            conn.close()

    def test_replay_delivers_exactly_once(self, tmp_path):
        conn = outbox.connect(tmp_path / "outbox.db")
        try:
            outbox.enqueue(conn, "https://collector.example/v1", "r1")
            calls = []
            receipt = outbox.drain(
                conn, lambda row: calls.append(row["id"]) or True)
            assert receipt["delivered"] == 1 and calls == [1]
            again = outbox.drain(
                conn, lambda row: calls.append(row["id"]) or True)
            assert again["delivered"] == 0 and calls == [1]  # never resent
            assert outbox.counts(conn)["sent"] == 1
        finally:
            conn.close()

    def test_failed_delivery_burns_attempts_then_deads(self, tmp_path):
        conn = outbox.connect(tmp_path / "outbox.db")
        try:
            outbox.enqueue(conn, "https://collector.example/v1", "r1")
            for _ in range(3):                  # three honest tries
                outbox.drain(conn, lambda row: False)
            c = outbox.counts(conn)
            assert c["dead"] == 1 and c["pending"] == 0
        finally:
            conn.close()

    def test_state_survives_reopen(self, tmp_path):
        # WAL + commit: a process that dies between enqueues loses
        # nothing that was committed
        db = tmp_path / "outbox.db"
        conn = outbox.connect(db)
        outbox.enqueue(conn, "https://collector.example/v1", "r1")
        conn.close()
        conn = outbox.connect(db)
        try:
            assert outbox.counts(conn)["pending"] == 1
        finally:
            conn.close()

    def test_bad_endpoint_refused(self, tmp_path):
        conn = outbox.connect(tmp_path / "outbox.db")
        try:
            with pytest.raises(ValueError):
                outbox.enqueue(conn, "ftp://not-http.example", "r1")
        finally:
            conn.close()

    def test_wire_exceptions_are_receipts_not_crashes(self, tmp_path):
        conn = outbox.connect(tmp_path / "outbox.db")
        try:
            outbox.enqueue(conn, "https://collector.example/v1", "r1")

            def hostile(row):
                raise RuntimeError("the wire is on fire")

            receipt = outbox.drain(conn, hostile)
            assert receipt["failed"] == 1 and receipt["delivered"] == 0
            assert outbox.counts(conn)["pending"] == 1
        finally:
            conn.close()

    def test_health_verdicts(self, tmp_path):
        verdict, detail = outbox.health(tmp_path / "absent.db")
        assert verdict == "PASS" and "not initialized" in detail
        db = tmp_path / "queue.db"
        conn = outbox.connect(db)
        outbox.enqueue(conn, "https://collector.example/v1", "r1")
        conn.close()
        verdict, detail = outbox.health(db)
        assert verdict == "PASS" and "buffered by design" in detail
        corrupt = tmp_path / "corrupt.db"
        corrupt.write_bytes(b"this is not a database" * 64)
        verdict, detail = outbox.health(corrupt)
        assert verdict == "FAIL"


class TestCapabilityPermanence:
    def test_capability_verbs_never_removed(self):
        # SEF-X core law, made machine-checkable: a capability that
        # ever shipped still parses today. Needs a checkout with tags
        # (CI clones shallow and skips; the ship-time receipt in
        # evidence/handover-v36.txt carries the full-history proof).
        def verbs_at(ref: str) -> set:
            proc = subprocess.run(["git", "show", f"{ref}:src/aeos/cli.py"],
                                  cwd=REPO, capture_output=True, text=True)
            if proc.returncode != 0:
                return set()
            import re
            return set(re.findall(r'add_parser\(\s*"([^"]+)"',
                                  proc.stdout))

        tags = subprocess.run(["git", "tag"], cwd=REPO,
                              capture_output=True, text=True).stdout.split()
        if not tags:
            pytest.skip("no tags in this checkout (shallow clone)")
        current = verbs_at("HEAD")
        for tag in sorted(tags):
            past = verbs_at(tag)
            removed = past - current
            assert not removed, \
                f"capabilities are permanent — removed at {tag}: {removed}"


class TestDoctorRows:
    def test_doctor_carries_the_new_rows(self, monkeypatch):
        monkeypatch.setenv("AEOS_OUTBOX_DB",
                           str(Path(tempfile.gettempdir())
                               / "aeos-outbox-doctor.db"))
        from aeos.doctor import doctor
        rep = doctor(None)
        areas = {r["area"]: r for r in rep["rows"]}
        assert "edge outbox" in areas
        assert areas["edge outbox"]["verdict"] in ("PASS", "WARN")
        assert "save-proof ledger" in areas

    def test_tampered_ledger_fails_the_doctor(self, tmp_path):
        from aeos.doctor import saveproof_rows
        _make_tree(tmp_path)
        cert = run_notary(tmp_path, [sys.executable, "-c", "pass"])
        write(cert, tmp_path / "evidence" / "save-proofs")
        forged = tmp_path / "evidence" / "save-proofs" / \
            "save-proof-deadbeefcafe-verified.json"
        # same auth digest, different body -> the lie is detectable
        forged.write_text(json.dumps({**cert, "files": cert["files"] + 1}),
                          encoding="utf-8")
        rows = saveproof_rows(tmp_path)
        assert rows[0][1] == "FAIL" and "TAMPERED" in rows[0][2]

    def test_empty_ledger_is_honestly_empty(self, tmp_path):
        from aeos.doctor import saveproof_rows
        rows = saveproof_rows(tmp_path)
        assert rows[0][0] == "save-proof ledger"
        assert rows[0][1] == "PASS" and "no certificates" in rows[0][2]
