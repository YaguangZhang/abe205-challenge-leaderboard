#!/usr/bin/env python3
"""Prepare the latest data and serve only the static site with no dependencies."""

import argparse
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from prepare_data import DataError, ROOT, write_data


class LocalHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    try:
        data, warnings = write_data(ROOT)
        for warning, count in warnings.items():
            print(f"Warning: {warning} ({count}).", file=sys.stderr)
        handler = partial(LocalHandler, directory=str(ROOT / "site"))
        with ThreadingHTTPServer((args.host, args.port), handler) as server:
            print(f"Loaded {data['metadata']['sourceFile']}.", flush=True)
            print(f"\nLeaderboard: http://{args.host}:{server.server_port}/", flush=True)
            print("Press Ctrl+C to stop. After changing a CSV, restart or run scripts/prepare_data.py and refresh.\n", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    except (DataError, OSError, OverflowError) as exc:
        print(f"Cannot start leaderboard: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
