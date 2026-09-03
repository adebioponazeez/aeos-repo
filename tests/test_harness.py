"""Harness tests: checkpoints, write boundaries, rollback."""

import pytest
from pathlib import Path

from aeos.harness import Harness


@pytest.fixture
def harness(tmp_path):
    return Harness(tmp_path)


class TestBoundary:
    def test_no_boundary_means_no_writes(self, harness):
        assert harness.path_allowed("anything.py", []) is False

    def test_glob_boundary_matches(self, harness):
        assert harness.path_allowed("src/a/b.py", ["src/*"])
        assert not harness.path_allowed("etc/passwd", ["src/*"])

    def test_unauthorized_writes_are_reverted(self, harness, tmp_path):
        harness.write("docs/readme.md", "original")
        cp = harness.snapshot("before", patterns=None)
        harness.write("docs/readme.md", "tampered")     # docs not in boundary
        harness.write("evil.sh", "rm -rf /")             # new file, not in boundary
        reverted = harness.enforce_boundary(cp, "rogue-agent", patterns=["src/*"])
        assert set(reverted) == {"docs/readme.md", "evil.sh"}
        assert harness.read("docs/readme.md") == "original"
        assert not harness.exists("evil.sh")

    def test_authorized_writes_survive(self, harness):
        cp = harness.snapshot("before")
        harness.write("src/new.py", "print('hi')")
        reverted = harness.enforce_boundary(cp, "builder", patterns=["src/*"])
        assert reverted == []
        assert harness.exists("src/new.py")


class TestCheckpoints:
    def test_snapshot_captures_state(self, harness):
        harness.write("a.txt", "1")
        cp = harness.snapshot("s1")
        harness.write("a.txt", "2")
        harness.write("b.txt", "new")
        restored = harness.rollback(cp)
        assert restored == 1
        assert harness.read("a.txt") == "1"
        assert not harness.exists("b.txt")

    def test_aeos_state_dir_is_always_writable(self, harness):
        cp = harness.snapshot("s")
        harness.write(".aeos/runs/log.txt", "x")
        reverted = harness.enforce_boundary(cp, "anyone", patterns=["src/*"])
        assert reverted == []  # OS state is inside the fence
