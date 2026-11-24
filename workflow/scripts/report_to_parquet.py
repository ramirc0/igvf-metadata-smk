"""IGVF search JSON -> Parquet, one row per object.

Arrays become lists and nested objects become structs, so a value that contains
a comma stays one value. Links stay `@id` paths, which join tables to each other.
"""

import argparse
import json

import polars as pl


def build_parser():
    """Build the report_to_parquet.py command-line parser.

    Returns
    -------
    argparse.ArgumentParser
        Parser for the report_to_parquet.py flags.
    """
    p = argparse.ArgumentParser(description="Convert a search JSON to Parquet.")
    p.add_argument("-i", "--input", required=True, help="Search result JSON.")
    p.add_argument("-o", "--output", required=True, help="Parquet file to write.")
    return p


def main(argv=None):
    """Read the `@graph` rows and write them as Parquet.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments. Defaults to `sys.argv[1:]`.
    """
    args = build_parser().parse_args(argv)

    with open(args.input, "rb") as handle:
        rows = json.load(handle)["@graph"]

    # Objects omit unset properties, so the schema needs every row.
    df = pl.DataFrame(rows, infer_schema_length=None)
    # No IGVF schema has a property named `id` or `type`.
    df = df.rename({"@id": "id", "@type": "type"}, strict=False)
    # First-appearance order depends on the server's row order.
    df = df.select(sorted(df.columns))

    df.write_parquet(args.output)
    print(f"{args.output}: {df.height} rows x {df.width} columns")


if __name__ == "__main__":
    main()
