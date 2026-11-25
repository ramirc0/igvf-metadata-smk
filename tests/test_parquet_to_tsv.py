"""The flat TSV must hold one text cell per value and keep nested data readable."""

import csv
import json

import polars as pl

from parquet_to_tsv import main


def flatten(tmp_path, df):
    source = tmp_path / "report.parquet"
    df.write_parquet(source)
    out = tmp_path / "report.tsv"
    main(["--input", str(source), "--output", str(out)])
    with open(out, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_array_is_joined_with_a_pipe_so_commas_survive(tmp_path):
    synonyms = ["poly(A) binding protein, cytoplasmic 2", "PABP"]

    rows = flatten(tmp_path, pl.DataFrame({"synonyms": [synonyms]}))

    assert rows[0]["synonyms"].split("|") == synonyms


def test_numeric_array_is_joined(tmp_path):
    rows = flatten(tmp_path, pl.DataFrame({"sizes": [[1, 2, 3]]}))

    assert rows[0]["sizes"] == "1|2|3"


def test_nested_object_is_json(tmp_path):
    attachment = {"href": "x", "size": 3}

    rows = flatten(tmp_path, pl.DataFrame({"attachment": [attachment]}))

    assert json.loads(rows[0]["attachment"]) == attachment


def test_array_of_objects_is_json(tmp_path):
    loci = [{"assembly": "GRCh38", "start": 1}, {"assembly": "GRCm39", "start": 9}]

    rows = flatten(tmp_path, pl.DataFrame({"loci": [loci]}))

    assert json.loads(rows[0]["loci"]) == loci


def test_null_is_an_empty_cell(tmp_path):
    df = pl.DataFrame(
        {
            "id": ["/a/", "/b/"],
            "aliases": [None, ["x"]],
            "attachment": [None, {"href": "x"}],
        }
    )

    rows = flatten(tmp_path, df)

    assert rows[0] == {"id": "/a/", "aliases": "", "attachment": ""}


def test_tab_and_newline_in_a_value_stay_in_one_cell(tmp_path):
    rows = flatten(tmp_path, pl.DataFrame({"description": ['a\tb\n"c"']}))

    assert rows == [{"description": 'a\tb\n"c"'}]


def test_empty_table_writes_an_empty_file(tmp_path):
    assert flatten(tmp_path, pl.DataFrame()) == []
