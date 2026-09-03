"""v22 tests: cache telemetry — hit rates, effective tokens, honesty."""

from aeos.telemetry import (UsageSnapshot, effective_tokens,
                            parse_usage)


class TestParse:
    def test_anthropic_style_usage_block_parsed(self):
        snap = parse_usage({"usage": {
            "input_tokens": 120, "output_tokens": 80,
            "cache_read_input_tokens": 4000,
            "cache_creation_input_tokens": 200}})
        assert snap is not None
        assert snap.cache_read_tokens == 4000
        assert snap.cache_hit_rate > 0.9

    def test_missing_usage_is_none_not_invented(self):
        assert parse_usage({"id": "msg_1"}) is None
        assert parse_usage({"usage": "garbage"}) is None

    def test_malformed_numbers_fail_closed(self):
        assert parse_usage({"usage": {"input_tokens": "many"}}) is None


class TestEconomics:
    def test_cache_reads_cut_effective_tokens(self):
        snap = UsageSnapshot(input_tokens=100, cache_read_tokens=4000)
        # 4000 cached reads bill like 400
        assert effective_tokens(4100, snap) == 4100 - 3600

    def test_hit_rate_zero_without_cache(self):
        snap = UsageSnapshot(input_tokens=500)
        assert snap.cache_hit_rate == 0.0
        assert effective_tokens(500, snap) == 500

    def test_effective_never_negative(self):
        snap = UsageSnapshot(cache_read_tokens=10_000)
        assert effective_tokens(100, snap) == 0


class TestHonesty:
    def test_live_mode_requires_opt_in(self, monkeypatch, capsys):
        monkeypatch.delenv("AEOS_LIVE", raising=False)
        from aeos.cli import main
        rc = main(["telemetry", "--live"])
        out = capsys.readouterr().out
        assert rc == 1 and "AEOS_LIVE=1" in out

    def test_fixture_command_renders(self, capsys):
        from aeos.cli import main
        rc = main(["telemetry"])
        out = capsys.readouterr().out
        assert rc == 0 and "TELEMETRY" in out and "hit rate" in out
