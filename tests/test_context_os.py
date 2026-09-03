"""Context OS tests: budget, classification, freshness, disclosure."""

from aeos.context_os import ContextOS, ContextUnit, approx_tokens
from aeos.contracts import ContextTier


def make_ctx(**kw):
    return ContextOS(budget_tokens=150, **kw)


class TestBudget:
    def test_budget_is_enforced(self):
        ctx = make_ctx()
        ctx.put(ContextUnit(key="a", body="x" * 400, tier=ContextTier.USEFUL))    # 100 tok
        ctx.put(ContextUnit(key="b", body="y" * 400, tier=ContextTier.OPTIONAL))  # 100 tok
        result = ctx.assemble("anything")  # budget 150: a fits, b must drop
        assert result.tokens <= 150
        assert result.tokens == 100
        assert ("b", "over budget") in result.dropped

    def test_drops_are_recorded_not_silent(self):
        ctx = make_ctx()
        ctx.put(ContextUnit(key="big", body="z" * 4000, tier=ContextTier.OPTIONAL))
        result = ctx.assemble("q")
        assert ("big", "over budget") in result.dropped

    def test_essential_over_budget_is_flagged_loudly(self):
        ctx = make_ctx()
        ctx.put(ContextUnit(key="core", body="e" * 4000, tier=ContextTier.ESSENTIAL))
        result = ctx.assemble("q")
        assert any("compress or raise budget" in r for _, r in result.dropped)


class TestClassification:
    def test_expired_units_become_stale_and_drop(self):
        import time
        ctx = make_ctx()
        ctx.put(ContextUnit(key="old", body="stale fact", tier=ContextTier.ESSENTIAL,
                            created_at=time.time() - 100,
                            expires_at=time.time() - 10))
        result = ctx.assemble("q")
        assert ctx.units["old"].tier is ContextTier.STALE
        assert ("old", "expired") in result.dropped

    def test_irrelevant_never_enters_prompt(self):
        ctx = make_ctx()
        ctx.put(ContextUnit(key="junk", body="irrelevant", tier=ContextTier.IRRELEVANT))
        assert "junk" not in ctx.assemble("q").text

    def test_conflicts_are_surfaced(self):
        ctx = make_ctx()
        ctx.put(ContextUnit(key="doc/a", body="use postgres", authority="team-a",
                            conflict_keys=["doc/b"], tier=ContextTier.ESSENTIAL))
        ctx.put(ContextUnit(key="doc/b", body="use sqlite", authority="team-b",
                            conflict_keys=[], tier=ContextTier.USEFUL))
        result = ctx.assemble("q")
        assert result.conflicts and result.conflicts[0][0] == "doc/a"


class TestProgressiveDisclosure:
    def test_metadata_first_not_full_dump(self):
        ctx = make_ctx()
        ctx.put(ContextUnit(key="kb/one", body="SHORT SUMMARY\n" + "body " * 500,
                            tier=ContextTier.USEFUL))
        listing = ctx.progressive_disclosure("kb/")
        assert len(listing) == 1
        assert "body body" not in listing[0]  # body NOT in the index
        assert "SHORT SUMMARY" in listing[0]  # first line IS


def test_approx_tokens_sane():
    assert approx_tokens("abcd" * 10) == 10
