"""Provenance must say what was fetched and under which access mode."""

import hashlib
import json

import polars as pl
import pytest

from provenance import main


@pytest.mark.parametrize(
    "flags, authenticated", [(["--authenticated"], True), ([], False)]
)
def test_one_row_per_report_with_access_mode(tmp_path, flags, authenticated):
    raw = tmp_path / "lab.json"
    raw.write_text(json.dumps({"@graph": [{"@id": "/labs/a/"}], "total": 1}))
    parquet = tmp_path / "lab.parquet"
    pl.DataFrame({"id": ["/labs/a/"], "name": ["a"]}).write_parquet(parquet)
    sheet = tmp_path / "reports.tsv"
    sheet.write_text("report_id\turl\nlab\thttps://example.org/lab\n")
    out = tmp_path / "provenance.tsv"

    main(
        ["--raw", str(raw), "--parquet", str(parquet), "--sheet", str(sheet)]
        + ["--run-id", "r1", "--output", str(out)]
        + flags
    )

    (row,) = pl.read_csv(out, separator="\t").iter_rows(named=True)
    assert row["report_id"] == "lab"
    assert row["url"] == "https://example.org/lab"
    assert row["authenticated"] is authenticated
    assert (row["rows"], row["columns"]) == (1, 2)
    assert row["sha256"] == hashlib.sha256(raw.read_bytes()).hexdigest()
