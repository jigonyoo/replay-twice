import json

from replay_twice.report import build_report, main, markdown


def test_report_observations_and_ranges_are_measured(tmp_path):
    data = build_report(tmp_path, repeats=3, threads=4, runs=3, seed=7)
    assert len(data["rows"]) == 3 * 3 * 4 * 4   # runs x flows x handlers x scenarios
    assert not list(tmp_path.glob("*.sqlite*")), "scratch stores must not land in the output"
    for row in data["rows"]:
        observations = row["observations"]
        assert row["duplicate_trials"] == sum(t["observed_effects"] > 1 for t in observations)
        if row["handler"] != "guarded_raises":
            assert row["error_trials"] == 0
        if row["handler"] == "guarded":
            assert row["failed_trials"] == 0
        if row["handler"] == "guarded_raises":
            assert row["failed_trials"] == 0 and row["duplicate_trials"] == 0
            assert row["error_trials"] == row["trials"]
        if row["handler"] == "naive":
            assert row["duplicate_trials"] == row["trials"]
    md = markdown(data)
    assert "Concurrency can vary across runs" in md
    assert "| refund (async tool) | guarded_raises |" in md


def test_cli_writes_json_markdown_and_preserves_runs(tmp_path, capsys):
    arguments = ["report", "--output", str(tmp_path), "--repeats", "1", "--runs", "1", "--threads", "2"]
    assert main(arguments) == 0
    assert main(arguments) == 0
    assert len(list(tmp_path.glob("report-*.json"))) == 2
    for path in tmp_path.glob("report-*.json"):
        assert json.loads(path.read_text())["environment"]["threads"] == 2
    assert "JSON:" in capsys.readouterr().out
