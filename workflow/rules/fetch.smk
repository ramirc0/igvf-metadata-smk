# IGVF search JSON -> Parquet -> optional flat TSV, one report per job.


rule fetch_report:
    output:
        f"{OUTDIR}/reports/{{report}}.json",
    params:
        url=lambda w: URL_OF[w.report],
        credentials=["--credentials", CREDENTIALS] if CREDENTIALS else [],
    log:
        f"{LOGDIR}/fetch_report/{{report}}.txt",
    benchmark:
        f"{BENCHDIR}/fetch_report/{{report}}.tsv",
    resources:
        igvf_api=1,
    software:
        SOFTWARE_ENV
    shell:
        r"""
        exec &> >(tee {log:q})

        python {workflow.basedir:q}/scripts/fetch_report.py \
            --url {params.url:q} \
            {params.credentials:q} \
            --output {output:q}

        sync {output:q}
        """


rule report_parquet:
    input:
        f"{OUTDIR}/reports/{{report}}.json",
    output:
        f"{OUTDIR}/parquets/{{report}}.parquet",
    log:
        f"{LOGDIR}/report_parquet/{{report}}.txt",
    benchmark:
        f"{BENCHDIR}/report_parquet/{{report}}.tsv",
    software:
        SOFTWARE_ENV
    shell:
        r"""
        exec &> >(tee {log:q})

        python {workflow.basedir:q}/scripts/report_to_parquet.py \
            --input {input:q} \
            --output {output:q}

        sync {output:q}
        """


rule report_tsv:
    input:
        f"{OUTDIR}/parquets/{{report}}.parquet",
    output:
        f"{OUTDIR}/tsvs/{{report}}.tsv",
    log:
        f"{LOGDIR}/report_tsv/{{report}}.txt",
    benchmark:
        f"{BENCHDIR}/report_tsv/{{report}}.tsv",
    software:
        SOFTWARE_ENV
    shell:
        r"""
        exec &> >(tee {log:q})

        python {workflow.basedir:q}/scripts/parquet_to_tsv.py \
            --input {input:q} \
            --output {output:q}

        sync {output:q}
        """
