"""Tiny HTTP server for previewing Skybridge widgets in VS Code.

Serves the widget_preview.html page and exposes widget HTML files
at /widget-file?path=<relative-path>.

Usage:
    python tests/widget_preview_server.py
    Then open http://localhost:8888 in VS Code Simple Browser.
"""

import mimetypes
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PORT = 8888
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            # Serve the preview page
            self._serve_file(Path(__file__).parent / "widget_preview.html")
            return

        if parsed.path == "/widget-file":
            # Serve widget HTML file from workspace
            qs = parse_qs(parsed.query)
            rel_path = qs.get("path", [None])[0]
            if not rel_path:
                self.send_error(400, "Missing 'path' query parameter")
                return
            full_path = PROJECT_ROOT / rel_path
            if not full_path.exists():
                self.send_error(404, f"File not found: {rel_path}")
                return
            # Prevent directory traversal
            try:
                full_path.resolve().relative_to(PROJECT_ROOT.resolve())
            except ValueError:
                self.send_error(403, "Access denied")
                return
            self._serve_file(full_path)
            return

        self.send_error(404, "Not found")

    def _serve_file(self, path: Path):
        content = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "text/html"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        # Quieter logging
        pass


def main():
    server = HTTPServer(("127.0.0.1", PORT), PreviewHandler)
    print(f"Widget preview server at http://localhost:{PORT}")
    print("Open this URL in VS Code Simple Browser (Ctrl+Shift+P → Simple Browser: Show)")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
