"""The Parquet table must keep what report.tsv loses: exact arrays and nesting."""

import json

import polars as pl

from report_to_parquet import main


def convert(tmp_path, rows):
    source = tmp_path / "report.json"
    source.write_text(json.dumps({"@graph": rows, "total": len(rows)}))
    out = tmp_path / "report.parquet"
    main(["--input", str(source), "--output", str(out)])
    return pl.read_parquet(out)


def test_array_value_with_a_comma_stays_one_element(tmp_path):
    synonyms = ["poly(A) binding protein, cytoplasmic 2", "PABP"]

    df = convert(tmp_path, [{"@id": "/genes/x/", "synonyms": synonyms}])

    assert df["synonyms"].to_list() == [synonyms]


def test_missing_properties_are_null(tmp_path):
    df = convert(tmp_path, [{"@id": "/a/"}, {"@id": "/b/", "doi": "10.1/x"}])

    assert df.sort("id")["doi"].to_list() == [None, "10.1/x"]


def test_array_of_objects_keeps_every_key(tmp_path):
    rows = [
        {"@id": "/a/", "locations": [{"assembly": "GRCh38", "start": 1}]},
        {"@id": "/b/", "locations": [{"assembly": "GRCm39", "end": 9}]},
    ]

    df = convert(tmp_path, rows)

    fields = {f.name for f in df.schema["locations"].inner.fields}
    assert fields == {"assembly", "start", "end"}


def test_nested_object_becomes_a_struct(tmp_path):
    df = convert(tmp_path, [{"@id": "/a/", "attachment": {"href": "x", "size": 3}}])

    assert df["attachment"].struct.field("size").to_list() == [3]


def test_at_prefixed_keys_lose_the_prefix_and_columns_are_sorted(tmp_path):
    df = convert(tmp_path, [{"uuid": "u", "@type": ["Lab", "Item"], "@id": "/labs/a/"}])

    assert df.columns == ["id", "type", "uuid"]


def test_empty_result_writes_an_empty_table(tmp_path):
    assert convert(tmp_path, []).shape == (0, 0)
