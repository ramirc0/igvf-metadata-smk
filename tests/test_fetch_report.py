"""The fetch must separate an empty type from a failure and keep the secret quiet."""

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from fetch_report import main

SECRET = "s3cretvalue16chr"
RESPONSES = {
    "/ok": (200, {"@graph": [{"@id": "/labs/a/"}], "total": 1}),
    "/empty": (404, {"@graph": [], "total": 0, "notification": "No results found"}),
    "/missing": (404, {"@type": ["HTTPNotFound", "Error"], "description": "gone"}),
    "/denied": (401, {"@type": ["HTTPUnauthorized", "Error"], "description": "no"}),
    "/short": (200, {"@graph": [{"@id": "/labs/a/"}], "total": 2}),
}


AUTHORIZATIONS = []


class Portal(BaseHTTPRequestHandler):
    def do_GET(self):
        AUTHORIZATIONS.append(self.headers.get("Authorization"))
        status, document = RESPONSES[self.path]
        body = json.dumps(document).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def portal():
    AUTHORIZATIONS.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Portal)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def dotenv(tmp_path):
    path = tmp_path / ".env"
    path.write_text(f"IGVF_API_KEY=KEYID123\nIGVF_SECRET_KEY={SECRET}\n")
    return path


def test_result_is_saved_byte_for_byte(portal, tmp_path):
    out = tmp_path / "lab.json"

    main(["--url", f"{portal}/ok", "--output", str(out)])

    assert json.loads(out.read_bytes()) == RESPONSES["/ok"][1]


def test_type_without_visible_objects_is_saved_as_empty(portal, tmp_path):
    out = tmp_path / "empty.json"

    main(["--url", f"{portal}/empty", "--output", str(out)])

    assert json.loads(out.read_bytes())["@graph"] == []


@pytest.mark.parametrize("path", ["/missing", "/denied", "/short"])
def test_failures_exit_without_output(portal, tmp_path, path):
    out = tmp_path / "report.json"

    with pytest.raises(SystemExit) as failure:
        main(["--url", f"{portal}{path}", "--output", str(out)])

    assert failure.value.code not in (0, None)
    assert not out.exists()


def test_credentials_become_a_basic_auth_header(portal, tmp_path, dotenv, capsys):
    out = tmp_path / "lab.json"

    main(["--url", f"{portal}/ok", "--credentials", str(dotenv), "--output", str(out)])

    expected = "Basic " + base64.b64encode(f"KEYID123:{SECRET}".encode()).decode()
    assert AUTHORIZATIONS == [expected]
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err
    assert expected not in captured.out + captured.err


def test_anonymous_fetch_sends_no_authorization(portal, tmp_path):
    main(["--url", f"{portal}/ok", "--output", str(tmp_path / "lab.json")])

    assert AUTHORIZATIONS == [None]
