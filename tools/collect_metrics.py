"""Re-measure every published figure and write docs/metrics.json.

No figure here is transcribed by hand. Values come from the test suite's
machine readable reports, from the experiments' JSON, from the committed fixture
read back off disk, or from the project's own configuration. A sibling
repository hardcoded thirteen of its declared constants, which made its own
claim false and made each one a guard that could not notice the thing it was
guarding change.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "docs" / "experiments"
GENERATED_DIR = ROOT / "docs" / "generated"
METRICS_PATH = ROOT / "docs" / "metrics.json"
JUNIT_PATH = ROOT / "junit.xml"
COVERAGE_PATH = ROOT / "coverage.json"

EXPERIMENTS = (
    "exp01_how_much_churn_is_real",
    "exp02_where_the_churn_is",
    "exp03_what_a_hold_buys",
)

ANCHORS: dict[str, list[str]] = {
    "tests_total": ["{} tests"],
    "coverage_line_pct": ["{}% line coverage"],
    # The thresholds themselves, read from the module rather than typed, so a
    # document claiming the cuts are at eighty and ninety five per cent is
    # checked against the constants the code actually uses.
    "abc_cut_low_pct": ["cut at {}% and"],
    "abc_cut_high_pct": ["and {}% of cumulative value"],
    "xyz_cut_low": ["sample cut at {} and"],
    "xyz_cut_high": ["and {} in that estimate"],
    "class_changes": [
        "quarter and {} items change class",
        "{} class changes, and only",
    ],
    "real_tier_changes": [
        "class; {} actually changed tier",
        "and only {} items changed tier",
    ],
    "justified_pct": ["{}% of the class changes"],
    "hand_review_moves": ["{} items are moved in"],
    "still_class_changes": ["still produces {} class changes"],
    "churn_near_a_cut_pct": ["a cut, {}% of items change class"],
    "churn_away_from_a_cut_pct": ["against {}% of those further away"],
    "churn_ratio": ["{} times the rate"],
    "held_class_changes": ["Class changes fall to\n  {}"],
    "held_hand_review_moves": ["and {} hand review moves"],
    "churn_removed_pct": ["removes {}% of the churn"],
    "hold_delay_periods": ["{} of a period"],
    "moves_never_reflected": ["never reflects {} of them"],
    "fixture_items": ["{} items"],
    "python_min_version": [],
}

FORMATS: dict[str, str] = {
    "tests_total": "{:d}",
    "coverage_line_pct": "{:.2f}",
    "abc_cut_low_pct": "{:.0f}",
    "abc_cut_high_pct": "{:.0f}",
    "xyz_cut_low": "{:.1f}",
    "xyz_cut_high": "{:.1f}",
    "class_changes": "{:.0f}",
    "real_tier_changes": "{:.0f}",
    "justified_pct": "{:.1f}",
    "hand_review_moves": "{:.0f}",
    "still_class_changes": "{:.0f}",
    "churn_near_a_cut_pct": "{:.1f}",
    "churn_away_from_a_cut_pct": "{:.1f}",
    "churn_ratio": "{:.1f}",
    "held_class_changes": "{:.0f}",
    "held_hand_review_moves": "{:.0f}",
    "churn_removed_pct": "{:.0f}",
    "hold_delay_periods": "{:.2f}",
    "moves_never_reflected": "{:.0f}",
    "fixture_items": "{:d}",
    "python_min_version": "{}",
}

GENERATED_BLOCKS = {
    "README.md": ("churn-table.md", "boundary-table.md", "hold-table.md"),
}

CHECKED_DOCUMENTS = (
    "README.md",
    *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "docs" / "adr").glob("ADR-*.md")),
    *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "src" / "axc").glob("*.py")),
    *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "experiments").glob("exp*.py")),
)


def run_tests() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-q",
            f"--junitxml={JUNIT_PATH}",
            "--cov=tta",
            "--cov-report=json",
        ],
        cwd=ROOT,
        check=True,
    )


def run_experiments() -> None:
    env_path = f"{ROOT / 'src'}:{ROOT / 'experiments'}:{ROOT / 'tests'}"
    for name in EXPERIMENTS:
        subprocess.run(
            [sys.executable, str(ROOT / "experiments" / f"{name}.py")],
            cwd=ROOT,
            check=True,
            env={"PYTHONPATH": env_path, "PATH": "/usr/bin:/bin:/usr/local/bin"},
        )


#: The one test file whose failure cannot block collection. Its tests read
#: ``docs/metrics.json`` and assert that every published figure is anchored, so
#: they are red by construction whenever the figures are stale, which is the
#: state collection exists to fix. Blocking on them deadlocks: the file cannot
#: be written until the tests pass and the tests cannot pass until it is
#: written. Every other failure still refuses, and ``make verify`` runs the full
#: suite *after* collection, so a real receipts regression still fails the
#: build. It just no longer stops the file that would clear it from being
#: written. See ADR-006.
RECEIPTS_SUITE = "tests/test_check_numbers.py"


def failing_tests(suite: ElementTree.Element) -> list[str]:
    """Names of the tests that failed or errored, as ``file::test``."""
    failures = []
    for case in suite.iter("testcase"):
        if case.find("failure") is None and case.find("error") is None:
            continue
        path = (case.get("classname") or "").split(".")
        name = case.get("name") or "?"
        failures.append(f"{'/'.join(path)}.py::{name}" if path else name)
    return failures


def read_suite() -> dict[str, float]:
    suite = ElementTree.parse(JUNIT_PATH).getroot()
    if suite.tag != "testsuite":
        suite = suite.find("testsuite")
    failures = failing_tests(suite)
    blocking = [name for name in failures if not name.startswith(RECEIPTS_SUITE)]
    if blocking:
        raise SystemExit(
            f"refusing to publish metrics from a run with {len(blocking)} failing "
            f"tests outside {RECEIPTS_SUITE}: {', '.join(sorted(blocking))}"
        )
    if failures:
        print(
            f"warning: {len(failures)} receipts tests are red, which is expected "
            "while the figures are stale. Re-run the suite after this collection "
            "and treat a remaining failure as real",
            file=sys.stderr,
        )
    coverage = json.loads(COVERAGE_PATH.read_text())
    return {
        "tests_total": int(suite.get("tests")),
        "coverage_line_pct": float(coverage["totals"]["percent_covered"]),
    }


def read_experiment(name: str) -> dict:
    return json.loads((EXPERIMENT_DIR / f"{name}.json").read_text())


TEST_COUNT_DOCUMENTS = ("README.md",)


def sync_test_count(total: int) -> None:
    """Write the measured test count into the badge and the prose that quote it.

    The count moves whenever a test is added, so every commit that added one
    also carried three hand edits to keep the badge, the README sentence and the
    defense guide in step, and a missed edit showed up as a failing receipts
    check rather than as anything a reader would notice. A figure that has to be
    typed in three places is a figure that will eventually be wrong in one.

    The substitution is deliberately narrow: a tests badge, and the exact phrase
    "N tests" where N is some number. Anything looser would rewrite unrelated
    counts.
    """
    for document in TEST_COUNT_DOCUMENTS:
        path = ROOT / document
        body = path.read_text()
        body = re.sub(r"tests-\d+-brightgreen", f"tests-{total}-brightgreen", body)
        body = re.sub(r"\b\d+ tests\b", f"{total} tests", body)
        path.write_text(body)


def sync_generated_blocks(blocks: dict[str, str]) -> None:
    """Write each generated block into the documents that publish it.

    The blocks were pasted into the README by hand and checked for drift
    afterwards, which caught a stale table but left correcting it as a manual
    copy of generated output into prose, every time any figure moved. The paste
    is the step worth removing: a drift gate on a hand copied table tells you
    the copy is wrong, and a generated copy cannot be.

    The markers are HTML comments, so they are invisible in rendered Markdown
    and unambiguous to match, which the previous approach of matching the
    block's own text was not.
    """
    for document, names in GENERATED_BLOCKS.items():
        path = ROOT / document
        body = path.read_text()
        for name in names:
            start = f"<!-- generated: {name} -->"
            end = f"<!-- end generated: {name} -->"
            if start not in body or end not in body:
                raise SystemExit(
                    f"{document} has no markers for the generated block {name}; add "
                    f"{start} and {end} around it"
                )
            head, rest = body.split(start, 1)
            _, tail = rest.split(end, 1)
            body = f"{head}{start}\n{blocks[name]}\n{end}{tail}"
        path.write_text(body)


def derive() -> dict[str, float]:
    """Every published figure, read from a run rather than typed."""
    churn = read_experiment("exp01_how_much_churn_is_real")
    where = read_experiment("exp02_where_the_churn_is")
    hold = read_experiment("exp03_what_a_hold_buys")

    from axc.classify import ABC_CUTS, XYZ_CUTS

    fixture = pd.read_csv(ROOT / "data" / "fixtures" / "assortment.csv")
    requires = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["requires-python"]

    headline = churn["headline"]
    still = next(row for row in churn["series"] if row["transition_rate"] == 0.0)
    tightest = next(row for row in where["series"] if row["comparable"])
    unheld, held = hold["series"][0], hold["series"][1]

    metrics = dict(read_suite())
    metrics.update(
        {
            "abc_cut_low_pct": ABC_CUTS[0] * 100,
            "abc_cut_high_pct": ABC_CUTS[1] * 100,
            "xyz_cut_low": XYZ_CUTS[0],
            "xyz_cut_high": XYZ_CUTS[1],
            "class_changes": headline["class_changes"],
            "real_tier_changes": headline["real_tier_changes"],
            "justified_pct": headline["justified_share"] * 100,
            "hand_review_moves": headline["hand_review_moves"],
            "still_class_changes": still["class_changes"],
            "churn_near_a_cut_pct": tightest["near_a_cut_change_rate"] * 100,
            "churn_away_from_a_cut_pct": tightest["away_from_a_cut_change_rate"] * 100,
            "churn_ratio": tightest["ratio"],
            "held_class_changes": held["class_changes"],
            "held_hand_review_moves": held["hand_review_moves"],
            "churn_removed_pct": hold["churn_removed_share"] * 100,
            "hold_delay_periods": held["mean_delay_on_a_real_move_periods"],
            "moves_never_reflected": held["real_moves_never_reflected"],
            "fixture_items": int(fixture["item"].nunique()),
            "python_min_version": float(requires.lstrip(">=~^ ")),
        }
    )
    _ = unheld
    return metrics


def render_churn_block() -> str:
    """How much reclassification has a real move behind it, by how many really move."""
    churn = read_experiment("exp01_how_much_churn_is_real")
    header = (
        "| Items really moving, per quarter | Class changes | Real tier changes | With a "
        "real move behind them | Hand review moves |\n| --- | --- | --- | --- | --- |"
    )
    rows = [
        f"| {row['transition_rate']:.1%} | {row['class_changes']:.0f} | "
        f"{row['real_tier_changes']:.0f} | {row['justified_share']:.1%} | "
        f"{row['hand_review_moves']:.0f} |"
        for row in churn["series"]
    ]
    return "\n".join([header, *rows])


def render_boundary_block() -> str:
    """Churn near a threshold against churn away from one."""
    where = read_experiment("exp02_where_the_churn_is")
    header = (
        "| Margin | Items near a cut | Churn near a cut | Churn away from one | Ratio |\n"
        "| --- | --- | --- | --- | --- |"
    )
    rows = []
    for row in where["series"]:
        if row["comparable"]:
            rows.append(
                f"| {row['margin']:.2f} | {row['items_near_a_cut']:.0f} | "
                f"{row['near_a_cut_change_rate']:.1%} | "
                f"{row['away_from_a_cut_change_rate']:.1%} | {row['ratio']:.1f}x |"
            )
        else:
            rows.append(
                f"| {row['margin']:.2f} | {row['items_near_a_cut']:.0f} | "
                f"{row['near_a_cut_change_rate']:.1%} | too few to compare | n/a |"
            )
    return "\n".join([header, *rows])


def render_hold_block() -> str:
    """What each hold length removes and what it costs."""
    hold = read_experiment("exp03_what_a_hold_buys")
    header = (
        "| Hold, quarters | Class changes | Hand review moves | Mean delay on a real move, "
        "quarters | Real moves never reflected |\n| --- | --- | --- | --- | --- |"
    )
    rows = [
        f"| {row['hold_periods']} | {row['class_changes']:.0f} | "
        f"{row['hand_review_moves']:.0f} | "
        f"{row['mean_delay_on_a_real_move_periods']:.2f} | "
        f"{row['real_moves_never_reflected']:.0f} |"
        for row in hold["series"]
    ]
    return "\n".join([header, *rows])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-experiments", action="store_true")
    args = parser.parse_args()

    if not args.skip_tests:
        run_tests()
    if not args.skip_experiments:
        run_experiments()

    metrics = derive()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    blocks = {
        "churn-table.md": render_churn_block(),
        "boundary-table.md": render_boundary_block(),
        "hold-table.md": render_hold_block(),
    }
    for name, body in blocks.items():
        (GENERATED_DIR / name).write_text(body + "\n")
    sync_generated_blocks(blocks)
    sync_test_count(int(metrics["tests_total"]))

    formatted = {name: FORMATS.get(name, "{}").format(value) for name, value in metrics.items()}
    METRICS_PATH.write_text(
        json.dumps(
            {
                "metrics": metrics,
                "formatted": formatted,
                "anchors": ANCHORS,
                "formats": FORMATS,
                "checked_documents": list(CHECKED_DOCUMENTS),
                "generated_blocks": {
                    document: list(names) for document, names in GENERATED_BLOCKS.items()
                },
                "badge_only": ["python_min_version"],
                "note": (
                    "every value here is read from a run: the test suite, the "
                    "experiments, the committed fixture, or the project's own "
                    "configuration. No figure is transcribed by hand"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"wrote {METRICS_PATH.relative_to(ROOT)} with {len(metrics)} metrics")
    for name in sorted(metrics):
        print(f"  {name:38s} {formatted[name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
