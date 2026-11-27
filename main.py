"""Entry point for Griductive Solver Web UI."""
import argparse

from web_server import run_web_app


def main():
    parser = argparse.ArgumentParser(description="Griductive Solver Web UI")
    parser.add_argument("--port", type=int, default=8765, help="Port for local Web UI server (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Start Web UI server without auto-opening browser")
    args = parser.parse_args()
    run_web_app(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
