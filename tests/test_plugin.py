def test_entrypoint_fixture_and_decorator_are_auto_loaded(pytester):
    pytester.makepyfile('''
        from uuid import uuid4
        import pytest
        from replay_twice import replay_twice, SCENARIOS
        from replay_twice.examples import SQLiteHandlers

        def test_fixture(replay, tmp_path):
            store = SQLiteHandlers(tmp_path / "fixture.sqlite", "guarded")
            result = replay(case_factory=lambda: store.case("refund", uuid4().hex), scenarios=SCENARIOS)
            assert len(result.trials) == 12
            assert next(t for t in result.trials if t.scenario == "concurrent").deliveries == 4

        @pytest.mark.parametrize("kind", ["refund", "payment.succeeded"])
        @replay_twice(scenarios=SCENARIOS, repeats=2, threads=4)
        def test_decorator(tmp_path, kind):
            store = SQLiteHandlers(tmp_path / "decorator.sqlite", "guarded")
            return store.case(kind, uuid4().hex)
    ''')
    result = pytester.runpytest_subprocess("-q", "--replay-repeats=3", "--replay-threads=4")
    result.assert_outcomes(passed=3)


def test_plugin_failure_is_readable(pytester):
    pytester.makepyfile('''
        from replay_twice import replay_twice, ReplayCase
        @replay_twice(scenarios=["duplicate"], repeats=3)
        def test_broken():
            effects = []
            return ReplayCase(lambda e: effects.append(e), lambda k: len(effects), "e", "k")
    ''')
    result = pytester.runpytest_subprocess("-q")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*duplicate: failed 3/3 repetitions*deliveries*observed effects*"])
