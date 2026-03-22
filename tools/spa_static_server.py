#!/usr/bin/env python3
"""
Minimal static-file server with React/SPA fallback.

Serves real files from a build directory and falls back to index.html for
extensionless routes so BrowserRouter deep links keep working in production.
"""

from __future__ import annotations

import argparse
import posixpath
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, help="Static build directory to serve")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=3030, help="Bind port")
    return parser


class SPARequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def send_head(self):
        if self._should_fallback_to_index():
            original_path = self.path
            self.path = "/index.html"
            try:
                return super().send_head()
            finally:
                self.path = original_path
        return super().send_head()

    def _should_fallback_to_index(self) -> bool:
        request_path = urlsplit(self.path).path
        normalized = posixpath.normpath(unquote(request_path))

        if normalized in {"", "."}:
            normalized = "/"

        if normalized == "/":
            return False

        if Path(normalized).suffix:
            return False

        translated = Path(self.translate_path(request_path))
        return not translated.exists()


def main() -> int:
    args = build_parser().parse_args()
    directory = Path(args.directory).resolve()
    if not directory.is_dir():
        raise SystemExit(f"Build directory not found: {directory}")

    handler = partial(SPARequestHandler, directory=str(directory))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving SPA build from {directory} on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
