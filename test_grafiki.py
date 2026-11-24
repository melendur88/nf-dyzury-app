from pathlib import Path

import yaml


ROOT = Path(__file__).parent / "grafiki"


def test_rosters_have_matching_months_and_only_duties():
    for path in ROOT.glob("*.yaml"):
        if path.stem == "index":
            continue
        roster = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert roster["month"] == path.stem
        assert roster["dyzurni"]
        names = [row["name"].casefold() for row in roster["dyzurni"]]
        assert len(names) == len(set(names))
        for row in roster["dyzurni"]:
            assert row["days"]
            assert len(row["days"]) == len(set(row["days"]))
            assert set(row["days"]) <= {"pn", "wt", "sr", "czw", "pt", "sob", "nd"}
        assert set(roster) == {"month", "dyzurni"}


def test_december_change_preserves_oldguard_in_previous_months():
    rosters = {
        path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in ROOT.glob("*.yaml") if path.stem != "index"
    }
    october = {row["name"] for row in rosters["2026-10"]["dyzurni"]}
    november = {row["name"]: row["days"] for row in rosters["2026-11"]["dyzurni"]}
    december = {row["name"]: row["days"] for row in rosters["2026-12"]["dyzurni"]}
    assert "OldGuard" in october
    assert november["OldGuard"] == ["pt"]
    assert "OldGuard" not in december
    assert december == {name: days for name, days in november.items() if name != "OldGuard"}


def test_directory_filenames_are_sufficient_to_select_effective_changes():
    months = [p.stem for p in ROOT.glob("*.yaml")]
    assert not (ROOT / "index.yaml").exists()
    # An unchanged December roster is effective in the next year too.
    assert max(month for month in months if month <= "2027-01") == "2026-12"
    assert max(month for month in months if month <= "2026-11") == "2026-11"
