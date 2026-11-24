"""Fetch one IGVF search result as JSON.

The portal answers a search without hits with HTTP 404 and a body whose
`notification` is `No results found`. That body is a valid empty result and is
saved like any other. Every other non-200 status is a failure.
"""

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_TIMEOUT_SECONDS = 900


def build_parser():
    """Build the fetch_report.py command-line parser.

    Returns
    -------
    argparse.ArgumentParser
        Parser for the fetch_report.py flags.
    """
    p = argparse.ArgumentParser(description="Fetch an IGVF search result as JSON.")
    p.add_argument("--url", required=True, help="Search URL with format=json.")
    p.add_argument(
        "--credentials",
        help="Dotenv file with IGVF_API_KEY and IGVF_SECRET_KEY. Omit for anonymous.",
    )
    p.add_argument("-o", "--output", required=True, help="JSON file to write.")
    return p


def basic_authorization(dotenv):
    """Build the HTTP basic auth header value from a dotenv file.

    Parameters
    ----------
    dotenv : str
        File with `IGVF_API_KEY=` and `IGVF_SECRET_KEY=` lines.

    Returns
    -------
    str
        Value for the `Authorization` header.
    """
    values = {}
    for line in Path(dotenv).read_text().splitlines():
        name, separator, value = line.strip().partition("=")
        if separator and not name.startswith("#"):
            values[name] = value.strip("'\"")
    pair = f"{values['IGVF_API_KEY']}:{values['IGVF_SECRET_KEY']}"
    return "Basic " + base64.b64encode(pair.encode()).decode()


def fetch(url, authorization=None):
    """GET a URL and return its status and body, whatever the status.

    Parameters
    ----------
    url : str
        URL to request.
    authorization : str, optional
        `Authorization` header value. It is not resent on a redirect.

    Returns
    -------
    tuple of (int, bytes)
        HTTP status and response body.
    """
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    if authorization:
        # A plain header would follow a redirect to another host.
        request.add_unredirected_header("Authorization", authorization)
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def main(argv=None):
    """Fetch the search result, check it is complete, and write it.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments. Defaults to `sys.argv[1:]`.
    """
    args = build_parser().parse_args(argv)

    authorization = basic_authorization(args.credentials) if args.credentials else None
    status, body = fetch(args.url, authorization)
    document = json.loads(body)

    empty = status == 404 and document.get("notification") == "No results found"
    if status != 200 and not empty:
        sys.exit(f"HTTP {status} from {args.url}: {document.get('description')}")

    rows = len(document["@graph"])
    if rows != document["total"]:
        sys.exit(f"{args.url}: got {rows} of {document['total']} objects")

    Path(args.output).write_bytes(body)
    print(f"{args.output}: HTTP {status}, {rows} objects, {len(body)} bytes")


if __name__ == "__main__":
    main()
