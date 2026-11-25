# Config, report sheet, path constants, and shared helpers.

from pathlib import Path

import polars as pl
from snakemake.exceptions import WorkflowError


configfile: "config/config.yaml"


RESULTS = config["outdir"]
RUN_ID = config["run_id"]
OUTDIR = f"{RESULTS}/{RUN_ID}"          # one immutable directory per IGVF snapshot
LOGDIR = f"logs/{RUN_ID}"
BENCHDIR = f"benchmarks/{RUN_ID}"

# The workspace path is relative to the rule file. Every rule file sits in rules/.
SOFTWARE_ENV = pixi(workspace="../envs", env=config["pixi_env"], locked=True)


# The pixi plugin installs the env inside each job. Parallel SLURM jobs then race
# on a fresh or relocked env, so install it once before any job starts.
onstart:
    shell("pixi install --manifest-path {workflow.basedir:q}/envs/pixi.toml --all --locked")


_SHEET = Path(config["reports"])
if not _SHEET.exists():
    raise WorkflowError(
        f"Report sheet not found: {_SHEET}\n"
        "Columns: report_id, url; see config/reports.tsv."
    )

# All-string read so empty cells are "" (absent), not a type error.
_rows = pl.read_csv(
    _SHEET, separator="\t", infer_schema_length=0, comment_prefix="#"
)

_ids = _rows.get_column("report_id").to_list()
_duplicates = sorted({r for r in _ids if _ids.count(r) > 1})
if _duplicates:
    # Two jobs would otherwise race on one output path.
    raise WorkflowError(f"Duplicate report_id in {_SHEET}: {', '.join(_duplicates)}")

URL_OF = {
    row["report_id"]: row["url"] for row in _rows.iter_rows(named=True)
}
REPORTS = list(URL_OF)

if not REPORTS:
    raise WorkflowError(f"Report sheet {_SHEET} has no rows.")


def _fetch_list():
    """Return the report IDs this run materializes.

    Returns
    -------
    list of str
        Every sheet report when `config["fetch"]` is `all`, else the listed IDs.

    Raises
    ------
    WorkflowError
        If `config["fetch"]` names a report absent from the sheet.
    """
    requested = config["fetch"]
    if requested == "all":
        return REPORTS
    unknown = sorted(set(requested) - set(REPORTS))
    if unknown:
        raise WorkflowError(
            f"config['fetch'] names reports absent from {_SHEET}: "
            f"{', '.join(unknown)}"
        )
    return list(requested)


FETCH = _fetch_list()


def _credentials():
    """Return the dotenv path from `config["credentials"]`, or None for anonymous.

    The file is checked at parse time so a typo fails before 57 jobs do. Only
    variable names are read here. The values never enter the workflow.

    Returns
    -------
    str or None
        Absolute dotenv path, or None when the setting is `false`.

    Raises
    ------
    WorkflowError
        If the file is missing, readable by others, or lacks a variable.
    """
    setting = config["credentials"]
    # --config credentials=false arrives as a string, not a YAML bool.
    if str(setting).lower() == "false":
        return None
    path = Path(setting).expanduser().resolve()
    if not path.is_file():
        raise WorkflowError(f"config['credentials']: {path} not found.")
    if path.stat().st_mode & 0o077:
        raise WorkflowError(
            f"config['credentials']: {path} is readable by others; "
            f"run chmod 600 {path}"
        )
    names = {line.partition("=")[0].strip() for line in path.read_text().splitlines()}
    missing = sorted({"IGVF_API_KEY", "IGVF_SECRET_KEY"} - names)
    if missing:
        raise WorkflowError(
            f"config['credentials']: {path} does not define {', '.join(missing)}."
        )
    return str(path)


CREDENTIALS = _credentials()
# --config tsv=true arrives as a string, not a YAML bool.
TSV = str(config["tsv"]).lower() == "true"


wildcard_constraints:
    report=r"[a-z0-9][a-z0-9_]*",
