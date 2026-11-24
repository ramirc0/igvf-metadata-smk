# igvf-metadata-smk

A [Snakemake](https://snakemake.readthedocs.io/) workflow that turns
[IGVF portal](https://data.igvf.org/) metadata into Parquet tables using
[Polars](https://pola.rs/).

## Description

Each run writes one immutable snapshot under `results/<run_id>/`. A provenance
table records the URL, access mode, fetch time, byte count and SHA-256 of every
report.

```
config/reports.tsv     report_id + url, one row per IGVF object type
      |
fetch_report           search JSON -> results/<run_id>/reports/<report>.json
report_parquet         @graph rows -> results/<run_id>/parquets/<report>.parquet
      |
provenance             url, authenticated, fetched_at, bytes, sha256, rows, columns
summary_card           headline numbers, rendered with Typst
```

| Path under `results/<run_id>/` | Contents |
| --- | --- |
| `reports/<report>.json` | the portal's bytes, kept so a conversion change costs no download |
| `parquets/<report>.parquet` | one row per object, one column per property |
| `report/provenance.tsv` | what was fetched, when, how big, and under which access mode |
| `report/summary.{typ,png}` | headline numbers for the snapshot |

### Tables

Each report is `search/?type=<Type>&frame=object&limit=all&format=json`. That
frame returns every property of every object.

- Arrays are `List` columns and nested objects are `Struct` columns. The
  portal's `report.tsv` joins arrays with commas, which cannot be undone for
  values such as the gene synonym `poly(A) binding protein, cytoplasmic 2`.
- Links are `@id` paths such as `/labs/anshul-kundaje/`. Tables join on them:
  `measurement_set.lab` equals `lab.id`.
- `@id` and `@type` are stored as `id` and `type`. Columns are sorted by name.
- An object omits a property it does not set. A table has a column only if at
  least one fetched object sets it.

### Access mode

An anonymous fetch returns released objects only. On 2026-11-24 it returned
305,064 objects against 524,971 with credentials. A snapshot is therefore one
or the other, and `provenance.tsv` says which in its `authenticated` column.
Use one mode per `run_id`.

An authenticated snapshot holds unreleased consortium metadata. Keep
`results/` readable by you alone.

## Getting Started

### Dependencies

- Linux x86-64.
- [pixi](https://pixi.sh/) on `PATH`.
- Network access to GitHub and `api.data.igvf.org`.
- An IGVF access key for authenticated snapshots.
- A SLURM cluster for `profiles/slurm`.

### Installing

```sh
git clone https://github.com/ramirc0/igvf-metadata-smk.git
cd igvf-metadata-smk
pixi install
cp config/config.yaml.template config/config.yaml   # then set run_id
```

Put the access key in a dotenv file with mode 600, outside the repository:

```sh
IGVF_API_KEY=...
IGVF_SECRET_KEY=...
```

Point `credentials:` in `config/config.yaml` at that file, or set it to `false`
for an anonymous snapshot. The workflow checks the file before any job starts.
It passes only the path to the fetch script, so the secret stays out of command
lines and logs.

### Executing program

```sh
pixi shell                                          # launcher env
snakemake --profile profiles/local                  # local
pixi run slurm 2026-11-24                           # SLURM, run_id as argument
snakemake --profile profiles/local -n -p            # dry run
snakemake --profile profiles/local --config fetch='[lab,award]'   # two reports
snakemake --profile profiles/local --config run_id=2026-11-24-public credentials=false
pixi run test                                       # unit tests
pixi run smoke                                      # three reports from the live API, anonymous
pixi run lint                                       # ruff check, ruff format --check, numpydoc lint
```

`run_id` names the snapshot directory. Use the snapshot date and bump it for a
fresh pull. Earlier snapshots stay untouched.

The launcher env (`pixi.toml` at the root) has Snakemake and its plugins. Rule
tools (`polars`, `typst`) come from a second pixi workspace, `workflow/envs/`.
Add a rule dependency with `pixi add <pkg>` there.

## Help

- **A new portal type is missing.** `config/reports.tsv` lists the types as of
  the day it was generated. Regenerate it and read the `git diff`:

  ```sh
  curl -sS 'https://api.data.igvf.org/profiles/?format=json' | jq -r '
    ["report_id","url"],
    (to_entries[]
     | select((.value|type)=="object" and (.value|has("properties")))
     | [(.value["$id"]|capture("/profiles/(?<n>.+)\\.json").n),
        "https://api.data.igvf.org/search/?type=\(.key)&frame=object&limit=all&format=json"])
    | @tsv' | (read -r header; echo "$header"; sort) > config/reports.tsv
  ```

- **A report has zero rows.** The portal answers a search without hits with
  HTTP 404 and `No results found`. The fetch saves that as an empty result.
  Three types were empty with credentials on 2026-11-24, and `access_key` is
  also empty without them.
- **A fetch fails with HTTP 401.** The portal rejected the key. It does not fall
  back to anonymous.
- **Every rule reran.** Any change to the rule env manifest or lock reruns every
  rule, `fetch_report` included. Rerunning an existing `run_id` then overwrites
  that snapshot. Pass `--rerun-triggers mtime` to keep it. Changing
  `credentials` has the same effect.

```sh
snakemake --help
```

## Authors

Christian Ramirez ([@ramirc0](https://github.com/ramirc0))

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Acknowledgments

- [encode-metadata-smk](https://github.com/ramirc0/encode-metadata-smk), the ENCODE counterpart.
- [snakemake-software-deployment-plugin-pixi](https://github.com/cademirch/snakemake-software-deployment-plugin-pixi)
