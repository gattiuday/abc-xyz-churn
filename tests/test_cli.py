"""The command line contract."""

from __future__ import annotations

import pandas as pd
import pytest

from axc.cli import main, read_assortment


@pytest.fixture
def assortment_file(tmp_path):
    out = tmp_path / "assortment.csv"
    assert main(["generate", "--out", str(out), "--items", "40"]) == 0
    return out


def test_generate_writes_a_readable_assortment(assortment_file):
    assortment = read_assortment(assortment_file)
    assert len(assortment.items) == 40
    assert assortment.periods == 8


def test_churn_exits_one_when_most_reclassification_is_unexplained(assortment_file, capsys):
    assert main(["churn", "--assortment", str(assortment_file)]) == 1
    out = capsys.readouterr().out
    assert "with a real move behind them" in out
    assert "not computable without the true tiers" in out


def test_hold_prints_the_trade_for_every_hold_length(assortment_file, capsys):
    assert main(["hold", "--assortment", str(assortment_file)]) == 0
    out = capsys.readouterr().out
    assert "class changes" in out
    assert "both are costs" in out


def test_boundaries_prints_the_distance_to_a_cut(assortment_file, capsys):
    assert main(["boundaries", "--assortment", str(assortment_file), "--top", "3"]) == 0
    out = capsys.readouterr().out
    assert "to a cut" in out
    assert "same confidence" in out


def test_an_assortment_missing_a_column_exits_two(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"item": ["A"], "period": [0]}).to_csv(bad, index=False)
    assert main(["churn", "--assortment", str(bad)]) == 2
    assert "not an assortment this tool can read" in capsys.readouterr().err


def test_an_empty_assortment_exits_one(tmp_path, capsys):
    from axc.cli import COLUMNS

    empty = tmp_path / "empty.csv"
    pd.DataFrame(columns=list(COLUMNS)).to_csv(empty, index=False)
    assert main(["churn", "--assortment", str(empty)]) == 1
    assert "undefined rather than a stable assortment" in capsys.readouterr().err
