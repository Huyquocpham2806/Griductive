"""Zero-dependency Python HTTP backend for the Griductive Web UI.

Strictly preserves the separation between GameEngine (hidden solution) and
DeductiveAgent (public knowledge state only). The frontend never receives
unrevealed statuses or unrevealed clues.
"""
from __future__ import annotations

import json
import mimetypes
import socket
import threading
import webbrowser
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from engine import GameEngine, clue_groups, load_puzzle, validate_puzzle
from logic_agent import DeductiveAgent, uniqueness
from models import Cell, Clue, Puzzle, Status, Verdict
from puzzle_generator import CASES, PUZZLES, generate

WEB_DIR = Path(__file__).resolve().parent / "web"


def _puzzle_from_dict(data: dict[str, Any]) -> Puzzle:
    """Parse and validate a puzzle payload from uploaded JSON."""
    payload = dict(data)
    raw_cells = payload.pop("cells", None)
    if not isinstance(raw_cells, list):
        raise ValueError("Missing or invalid 'cells' list in puzzle JSON")
    cells = []
    for raw in raw_cells:
        item = dict(raw)
        item["true_status"] = Status(item["true_status"])
        item["clue"] = Clue(**item["clue"])
        cells.append(Cell(**item))
    puzzle = Puzzle(**payload, cells=tuple(cells))
    validate_puzzle(puzzle)
    return puzzle


class GameSession:
    """Stateful session wrapping GameEngine + DeductiveAgent behind a lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.base_index = 0
        self.case_index: int | None = 0
        self.current: Puzzle | None = None
        self.engine: GameEngine | None = None
        self.agent: DeductiveAgent | None = None
        self.select_case(0)

    def _references(self, clue: Clue) -> list[str]:
        assert self.current is not None
        seen: list[str] = []
        for group in clue_groups(clue, self.current.num_rows, self.current.num_cols):
            for cid in group:
                if cid not in seen:
                    seen.append(cid)
        return seen

    def _load(self, puzzle: Puzzle, case_index: int | None) -> dict[str, Any]:
        self.current = puzzle
        self.case_index = case_index
        self.engine = GameEngine(puzzle)
        self.agent = DeductiveAgent(self.engine)
        state = self.engine.public_state()
        if state.clues:
            try:
                self.agent.classify(state, state.clues[0].owner_cell)
            except NotImplementedError:
                pass
        return self._serialize_state()

    def _serialize_state(self) -> dict[str, Any]:
        assert self.current is not None and self.engine is not None and self.agent is not None
        state = self.engine.public_state()
        stats = self.agent.stats
        clues_payload = {}
        for clue in state.clues:
            clues_payload[clue.owner_cell] = {
                "clue_id": clue.clue_id,
                "owner_cell": clue.owner_cell,
                "clue_type": clue.clue_type,
                "text": clue.text,
                "references": self._references(clue),
            }
        first_focus = state.clues[0].owner_cell if state.clues else None
        return {
            "puzzle": {
                "puzzle_id": self.current.puzzle_id,
                "title": self.current.title,
                "difficulty": self.current.difficulty,
                "num_rows": self.current.num_rows,
                "num_cols": self.current.num_cols,
                "description": self.current.description,
                "case_index": self.case_index,
            },
            "people": [
                {
                    "cell_id": p.cell_id,
                    "row": p.row,
                    "col": p.col,
                    "name": p.name,
                    "profession": p.profession,
                }
                for p in state.people
            ],
            "known": {cid: st.value for cid, st in state.known.items()},
            "clues": clues_payload,
            "initial_focus": first_focus,
            "stats": {
                "mode": stats.mode,
                "primary_vars": stats.primary_vars,
                "aux_vars": stats.aux_vars,
                "cnf_clauses": stats.cnf_clauses,
                "sat_calls": stats.sat_calls,
                "decisions": stats.decisions,
                "propagations": stats.propagations,
                "backtracks": stats.backtracks,
                "runtime_ms": round(stats.runtime_sec * 1000, 2),
            },
            "trace": list(self.agent.trace.entries),
            "solved": len(state.known) == len(state.people),
            "open_count": len(state.known),
            "total_count": len(state.people),
        }

    def list_cases(self) -> list[dict[str, Any]]:
        return [
            {
                "index": idx,
                "id": slug,
                "rows": rows,
                "cols": cols,
                "title": title,
                "difficulty": difficulty,
                "extensions": ext,
            }
            for idx, (slug, rows, cols, title, difficulty, ext) in enumerate(CASES)
        ]

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return self._serialize_state()

    def select_case(self, index: int) -> dict[str, Any]:
        with self._lock:
            if not (0 <= index < len(CASES)):
                raise ValueError("Case index out of range")
            self.base_index = index
            slug = CASES[index][0]
            puzzle = load_puzzle(PUZZLES / f"{slug}.json")
            return self._load(puzzle, index)

    def restart(self) -> dict[str, Any]:
        with self._lock:
            assert self.current is not None
            return self._load(self.current, self.case_index)

    def generate_new(
        self,
        rows: int | None = None,
        cols: int | None = None,
        extensions: bool | None = None,
        difficulty: str | None = None,
        seed: int | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            _, br, bc, _, bdiff, bext = CASES[self.base_index]
            r = int(rows) if rows is not None else br
            c = int(cols) if cols is not None else bc
            if not (2 <= r <= 6 and 2 <= c <= 6):
                raise ValueError("Grid size must be between 2x2 and 6x6")
            ext = bool(extensions) if extensions is not None else bext
            diff = difficulty or bdiff
            puzzle = generate(
                r, c, seed=seed, extensions=ext,
                title=f"Generated {r}×{c} Case", difficulty=diff,
            )
            return self._load(puzzle, None)

    def load_uploaded(self, raw_json: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            puzzle = _puzzle_from_dict(raw_json)
            return self._load(puzzle, None)

    def submit(self, cell_id: str, status_str: str) -> dict[str, Any]:
        with self._lock:
            assert self.agent is not None
            status = Status(status_str)
            verdict = self.agent.submit(cell_id, status)
            return {
                "verdict": verdict.value,
                "cell_id": cell_id,
                "status": status.value,
                "state": self._serialize_state(),
            }

    def hint(self) -> dict[str, Any]:
        with self._lock:
            assert self.agent is not None
            hint = self.agent.get_hint()
            # Never spoil the verdict label; return only the cell + related clue owners.
            hint_payload = (
                {"cell_id": hint.cell_id, "related": list(hint.related)}
                if hint is not None else None
            )
            return {
                "hint": hint_payload,
                "state": self._serialize_state(),
            }

    def step(self) -> dict[str, Any]:
        with self._lock:
            assert self.agent is not None
            hint = self.agent.step()
            return {
                "revealed": hint.cell_id if hint is not None else None,
                "related": list(hint.related) if hint is not None else [],
                "state": self._serialize_state(),
            }

    def check_uniqueness(self) -> dict[str, Any]:
        with self._lock:
            assert self.current is not None
            clues = [c.clue for c in self.current.cells]
            is_unique = uniqueness(clues, self.current.num_rows, self.current.num_cols)
            return {"unique": bool(is_unique)}

    def export_puzzle_json(self) -> tuple[str, str]:
        with self._lock:
            assert self.current is not None
            filename = f"{self.current.puzzle_id}.json"
            body = json.dumps(asdict(self.current), ensure_ascii=False, indent=2) + "\n"
            return filename, body


def _make_handler(session: GameSession):
    class GriductiveHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            # Keep terminal output clean during interactive play.
            return

        def _send_json(self, payload: Any, code: int = HTTPStatus.OK) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))

        def _serve_static(self, rel_path: str) -> None:
            clean = "index.html" if rel_path in ("", "/") else rel_path.lstrip("/")
            target = (WEB_DIR / clean).resolve()
            if not str(target).startswith(str(WEB_DIR.resolve())) or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return
            mime, _ = mimetypes.guess_type(str(target))
            if target.suffix == ".js":
                mime = "application/javascript; charset=utf-8"
            elif target.suffix == ".css":
                mime = "text/css; charset=utf-8"
            elif target.suffix == ".html":
                mime = "text/html; charset=utf-8"
            data = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            try:
                if path == "/api/cases":
                    self._send_json({"cases": session.list_cases()})
                elif path == "/api/state":
                    self._send_json(session.get_state())
                elif path == "/api/export":
                    fname, content = session.export_puzzle_json()
                    raw = content.encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                else:
                    self._serve_static(path)
            except Exception as err:
                self._send_json({"error": str(err)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                body = self._read_json()
                if path == "/api/case":
                    self._send_json(session.select_case(int(body["index"])))
                elif path == "/api/restart":
                    self._send_json(session.restart())
                elif path == "/api/generate":
                    seed_val = body.get("seed")
                    seed = int(seed_val) if seed_val not in (None, "") else None
                    self._send_json(
                        session.generate_new(
                            rows=body.get("rows"),
                            cols=body.get("cols"),
                            extensions=body.get("extensions"),
                            difficulty=body.get("difficulty"),
                            seed=seed,
                        )
                    )
                elif path == "/api/load_json":
                    self._send_json(session.load_uploaded(body["puzzle"]))
                elif path == "/api/submit":
                    self._send_json(session.submit(str(body["cell_id"]), str(body["status"])))
                elif path == "/api/hint":
                    self._send_json(session.hint())
                elif path == "/api/step":
                    self._send_json(session.step())
                elif path == "/api/check_uniqueness":
                    self._send_json(session.check_uniqueness())
                else:
                    self._send_json({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
            except NotImplementedError as err:
                self._send_json(
                    {"error": f"Hàm chưa được cài đặt (NotImplementedError): {err}"},
                    HTTPStatus.NOT_IMPLEMENTED,
                )
            except (KeyError, ValueError, TypeError, json.JSONDecodeError) as err:
                self._send_json({"error": str(err)}, HTTPStatus.BAD_REQUEST)
            except Exception as err:
                self._send_json({"error": str(err)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    return GriductiveHandler


def _find_port(host: str, preferred: int) -> int:
    for port in (preferred, *range(preferred + 1, preferred + 25), 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return sock.getsockname()[1]
            except OSError:
                continue
    raise OSError("Could not bind a free localhost port")


def create_server(host: str = "127.0.0.1", port: int = 8765) -> tuple[ThreadingHTTPServer, str, GameSession]:
    session = GameSession()
    actual_port = _find_port(host, port)
    server = ThreadingHTTPServer((host, actual_port), _make_handler(session))
    url = f"http://{host}:{actual_port}"
    return server, url, session


def run_web_app(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    server, url, _ = create_server(host=host, port=port)
    print(f"Griductive Web UI is running at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Griductive server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_web_app()

