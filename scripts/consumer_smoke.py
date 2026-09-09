from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    request_body = b""

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        type(self).request_body = self.rfile.read(length)
        body = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "problem": "The demo trace contains a missing name.",
                                    "fix": "Define the name before using it.",
                                }
                            )
                        }
                    }
                ]
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        pass


server = HTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

try:
    trace = 'Traceback: File "/home/demo/project/app.py", line 4\nNameError: name \'missing\' is not defined\n'
    env = os.environ.copy()
    env.update(
        {
            "ERRFIX_API_KEY": "smoke-test-key",
            "ERRFIX_API_URL": f"http://127.0.0.1:{server.server_port}",
            "ERRFIX_MODEL": "smoke-test-model",
        }
    )

    result = subprocess.run(
        [sys.executable, "-m", "errfix.cli"],
        input=trace,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"errfix exited with {result.returncode}: {result.stderr}")
    if "missing name" not in result.stdout or "Define the name" not in result.stdout:
        raise SystemExit(f"unexpected CLI output:\n{result.stdout}\n{result.stderr}")

    payload = json.loads(Handler.request_body.decode())
    sent_trace = payload["messages"][1]["content"]
    if "/home/demo/project/app.py" in sent_trace:
        raise SystemExit("sanitizer failed to redact the demo path")

    print("errfix clean consumer smoke test passed")
finally:
    server.shutdown()
    server.server_close()
