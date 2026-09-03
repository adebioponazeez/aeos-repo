"""v23 tests: eval suites — deterministic judges, robust to raises."""

from aeos.evals import EvalCase, EvalSuite, run_self_eval


class TestSuite:
    def test_perfect_executor_passes(self):
        s = EvalSuite().add(EvalCase("double", judge=lambda o:
                                     1.0 if o == 4 else 0.0))
        rep = s.run(lambda inp: 2 * 2)
        assert rep.passed and rep.score == 1.0

    def test_failing_judge_fails_the_suite(self):
        s = EvalSuite().add(EvalCase("law", judge=lambda o:
                                     1.0 if o else 0.0))
        rep = s.run(lambda inp: False)
        assert not rep.passed and rep.score == 0.0

    def test_weights_shape_the_score(self):
        s = (EvalSuite(threshold=0.5)
             .add(EvalCase("heavy", judge=lambda o: 0.0, weight=3.0))
             .add(EvalCase("light", judge=lambda o: 1.0, weight=1.0)))
        rep = s.run(lambda inp: None)
        assert abs(rep.score - 0.25) < 1e-9 and not rep.passed

    def test_raising_case_fails_without_crashing(self):
        s = EvalSuite().add(EvalCase("boom", judge=lambda o: 1.0))
        rep = s.run(lambda inp: 1 / 0)
        assert rep.results[0].score == 0.0
        assert "ZeroDivision" in rep.results[0].detail

    def test_partial_credit_is_clamped(self):
        s = EvalSuite().add(EvalCase("p", judge=lambda o: 7.0))
        assert s.run(lambda inp: None).score == 1.0

    def test_render_names_every_case(self):
        s = EvalSuite().add(EvalCase("named-case", judge=lambda o: 1.0))
        text = s.run(lambda inp: None).render()
        assert "named-case" in text and "EVAL" in text


class TestSelfEval:
    def test_aeos_grades_its_own_laws(self, tmp_path):
        rep = run_self_eval(tmp_path / "mirror")
        names = [r.name for r in rep.results]
        assert len(names) == 6
        assert rep.passed, rep.render()

    def test_mirror_catches_a_broken_law(self, tmp_path):
        # sabotage: no STANDARDS.md -> standards case must fail honest
        from aeos.standards import check_plan
        res = check_plan("uncited", tmp_path / "nowhere" / "STANDARDS.md")
        assert not res["gated"]      # ungated honestly, not faked

    def test_eval_command_renders(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["eval", "--workspace", str(tmp_path / "ws")])
        out = capsys.readouterr().out
        assert rc == 0 and "EVAL" in out and "PASS" in out
