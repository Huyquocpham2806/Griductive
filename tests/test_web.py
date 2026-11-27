"""End-to-end HTTP integration tests for the Griductive Web UI server."""
import json
import threading
import unittest
from urllib.request import Request, urlopen

from models import Status
from web_server import create_server


class WebServerIntegration(unittest.TestCase):
    def setUp(self):
        self.server, self.url, self.session = create_server(host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _get(self, path):
        with urlopen(self.url + path) as resp:
            return resp.status, resp.read()

    def _post_json(self, path, payload):
        req = Request(
            self.url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def test_static_and_public_state_boundary(self):
        code, html = self._get("/")
        self.assertEqual(code, 200)
        self.assertIn(b"Griductive", html)

        _, raw_cases = self._get("/api/cases")
        cases = json.loads(raw_cases)["cases"]
        self.assertEqual(len(cases), 8)

        _, raw_state = self._get("/api/state")
        state = json.loads(raw_state)
        self.assertEqual(state["stats"]["mode"], "DPLL")
        self.assertEqual(state["stats"]["sat_calls"], 0)
        self.assertEqual(set(state["known"]), set(state["clues"]))
        for person in state["people"]:
            self.assertNotIn("true_status", person)
            self.assertNotIn("clue", person)

    def test_play_flow_verdicts_hint_step_generate_and_roundtrip(self):
        # Select 3x3 easy case (index 2)
        _, state = self._post_json("/api/case", {"index": 2})
        self.assertEqual((state["puzzle"]["num_rows"], state["puzzle"]["num_cols"]), (3, 3))
        self.assertEqual(state["open_count"], 1)

        # Hint must not leak verdict status
        _, hint_res = self._post_json("/api/hint", {})
        hint = hint_res["hint"]
        self.assertIsNotNone(hint)
        self.assertNotIn("status", hint)
        target = hint["cell_id"]

        # Unprovable cell is rejected with NOT_PROVABLE even if guessing true status
        unknown = next(
            p["cell_id"] for p in state["people"]
            if p["cell_id"] not in state["known"]
            and self.session.agent.classify(self.session.engine.public_state(), p["cell_id"]) == Status.UNKNOWN
        )
        _, rej_np = self._post_json("/api/submit", {"cell_id": unknown, "status": "CRIMINAL"})
        self.assertEqual(rej_np["verdict"], "NOT_PROVABLE")
        self.assertNotIn(unknown, rej_np["state"]["known"])

        # Opposite of forced status is rejected with CONTRADICTED
        forced = self.session.agent.classify(self.session.engine.public_state(), target)
        wrong = "INNOCENT" if forced == Status.CRIMINAL else "CRIMINAL"
        _, rej_con = self._post_json("/api/submit", {"cell_id": target, "status": wrong})
        self.assertEqual(rej_con["verdict"], "CONTRADICTED")
        self.assertNotIn(target, rej_con["state"]["known"])

        # Correct forced verdict is ACCEPTED and records trace
        _, acc = self._post_json("/api/submit", {"cell_id": target, "status": forced.value})
        self.assertEqual(acc["verdict"], "ACCEPTED")
        self.assertIn(target, acc["state"]["known"])
        self.assertEqual(len(acc["state"]["trace"]), 1)

        # Step solves one more cell, restart restores initial state
        _, stepped = self._post_json("/api/step", {})
        self.assertIsNotNone(stepped["revealed"])
        self.assertEqual(stepped["state"]["open_count"], 3)

        _, restarted = self._post_json("/api/restart", {})
        self.assertEqual(restarted["open_count"], 1)
        self.assertEqual(restarted["trace"], [])

        # Uniqueness check + export + upload roundtrip
        _, uniq = self._post_json("/api/check_uniqueness", {})
        self.assertTrue(uniq["unique"])

        _, exported_raw = self._get("/api/export")
        exported_puzzle = json.loads(exported_raw.decode("utf-8"))
        _, uploaded = self._post_json("/api/load_json", {"puzzle": exported_puzzle})
        self.assertEqual(uploaded["puzzle"]["puzzle_id"], exported_puzzle["puzzle_id"])

        # Generate a fresh 3x3 puzzle with seed
        _, generated = self._post_json("/api/generate", {"rows": 3, "cols": 3, "extensions": True, "seed": 42})
        self.assertEqual((generated["puzzle"]["num_rows"], generated["puzzle"]["num_cols"]), (3, 3))
        _, gen_uniq = self._post_json("/api/check_uniqueness", {})
        self.assertTrue(gen_uniq["unique"])
