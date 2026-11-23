"""Desktop integration test. Skips when Tk cannot open a display."""
import tkinter as tk
import unittest

from gui import GriductiveApp
from models import BINARY, Status
from puzzle_generator import CASES


class Desktop(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as err:
            self.skipTest(str(err))
        self.addCleanup(self.root.destroy)
        self.app = GriductiveApp(self.root)
        self.root.update()

    def click(self, cell, offset=None):
        app = self.app
        app.show_card(cell)
        self.root.update()
        x,y,right,bottom = app.boxes[cell]
        px = (x+right)/2 - app.board.canvasx(0)
        py = ((y+bottom)/2 if offset is None else y+offset) - app.board.canvasy(0)
        app.board.event_generate("<Button-1>",x=round(px),y=round(py))
        self.root.update()

    def test_inspect_reject_hint_step_generate_restart_auto(self):
        app = self.app
        state = app.engine.public_state()
        self.assertEqual((state.num_rows,state.num_cols),(5,4))
        self.click(state.clues[0].owner_cell)
        self.assertEqual(app.highlights,app.references(state.clues[0]))
        app.hint()
        forced = app.focus
        self.assertEqual(state,app.engine.public_state())
        statuses = {p.cell_id:app.agent.classify(state,p.cell_id) for p in state.people if p.cell_id not in state.known}
        unknown = next(i for i,s in statuses.items() if s==Status.UNKNOWN)
        self.click(unknown)
        self.click(unknown,60)
        self.assertIn("NOT_PROVABLE",app.feedback.cget("text"))
        wrong, = set(BINARY)-{statuses[forced]}
        self.click(forced)
        self.click(forced,60 if wrong==Status.INNOCENT else 95)
        self.assertIn("CONTRADICTED",app.feedback.cget("text"))
        self.assertEqual(state,app.engine.public_state())
        self.click(forced)
        self.click(forced,60 if statuses[forced]==Status.INNOCENT else 95)
        self.assertIn(forced,app.engine.public_state().known)
        app.step()
        self.assertEqual(len(app.agent.trace.entries),2)
        app.restart()
        self.assertEqual(state,app.engine.public_state())
        for n,(_,r,c,*_) in enumerate(CASES):
            app.combo.current(n)
            app.combo.event_generate("<<ComboboxSelected>>")
            self.root.update()
            self.assertEqual(len(app.boxes),r*c)
        app.combo.current(2)
        app.combo.event_generate("<<ComboboxSelected>>")
        self.root.update()
        app.generate_new()
        start = app.engine.public_state()
        self.assertEqual((start.num_rows,start.num_cols),(3,3))
        app.toggle_auto()
        app.toggle_auto()
        self.assertIsNone(app.timer)
        app.restart()
        self.assertEqual(app.engine.public_state(),start)
        # Drive real Tk timer callbacks, with a deadline to detect a stalled GUI.
        app.toggle_auto()
        done = tk.BooleanVar(value=False)
        def poll():
            if app.timer is None:
                done.set(True)
            else:
                self.root.after(60,poll)
        self.root.after(60,poll)
        timeout = self.root.after(8000,lambda:done.set(True))
        self.root.wait_variable(done)
        self.root.after_cancel(timeout)
        self.assertEqual(len(app.engine.public_state().known),9)
        self.assertEqual(len(app.agent.trace.entries),8)
        self.assertIn("phá án",app.feedback.cget("text"))
