"""Report Parquet -> flat TSV, one text cell per value.

Arrays of scalars are joined with `|`. Nested objects and arrays of them are
JSON strings. Cells that hold a tab, a newline or a quote are quoted the CSV
way, so read the file with a CSV parser.
"""

import argparse
import json

import polars as pl

# No array element in the 2026-11-24 snapshot holds a pipe. Commas and
# semicolons both occur.
ARRAY_SEPARATOR = "|"


def build_parser():
    """Build the parquet_to_tsv.py command-line parser.

    Returns
    -------
    argparse.ArgumentParser
        Parser for the parquet_to_tsv.py flags.
    """
    p = argparse.ArgumentParser(description="Flatten a report Parquet to TSV.")
    p.add_argument("-i", "--input", required=True, help="Report Parquet.")
    p.add_argument("-o", "--output", required=True, help="TSV file to write.")
    return p


def flat(column):
    """Turn a nested column into a string column.

    Parameters
    ----------
    column : polars.Series
        Any column of a report table.

    Returns
    -------
    polars.Series
        The column unchanged if it is scalar. An array of scalars joined with
        `ARRAY_SEPARATOR`. Any other nested value as a JSON string.
    """
    dtype = column.dtype
    if not dtype.is_nested():
        return column
    if isinstance(dtype, pl.List) and not dtype.inner.is_nested():
        return column.cast(pl.List(pl.String)).list.join(ARRAY_SEPARATOR)
    return pl.Series(
        column.name,
        [None if value is None else json.dumps(value) for value in column.to_list()],
        dtype=pl.String,
    )


def main(argv=None):
    """Read a report Parquet and write it as a flat TSV.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments. Defaults to `sys.argv[1:]`.
    """
    args = build_parser().parse_args(argv)

    df = pl.read_parquet(args.input)
    df = df.select(flat(df[name]) for name in df.columns)

    df.write_csv(args.output, separator="\t")
    print(f"{args.output}: {df.height} rows x {df.width} columns")


if __name__ == "__main__":
    main()
