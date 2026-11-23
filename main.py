"""Entry point for Griductive Solver (Web UI by default, optional --tk desktop mode)."""
import argparse


def main():
    parser = argparse.ArgumentParser(description="Griductive Solver GUI")
    parser.add_argument("--tk", action="store_true", help="Launch legacy Tkinter desktop GUI instead of Web UI")
    parser.add_argument("--port", type=int, default=8765, help="Port for local Web UI server (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Start Web UI server without auto-opening browser")
    args = parser.parse_args()

    if args.tk:
        import tkinter as tk
        from gui import GriductiveApp

        root = tk.Tk()
        GriductiveApp(root)
        root.mainloop()
    else:
        from web_server import run_web_app

        run_web_app(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
