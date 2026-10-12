"""
Swipe Keyboard for PC
=====================
Draw a path across letters with your mouse to type words.
- Hold left mouse button and drag across letters to swipe
- Release to complete a word (it will be predicted and appended)
- Click a single letter to type it directly
- Backspace / Space / Clear buttons available
- Works on Windows, Mac, Linux (requires Python 3 + tkinter)

Run:  python swipe_keyboard.py
"""

import tkinter as tk
from tkinter import font as tkfont
import math
import itertools

# ── Word list for swipe prediction ──────────────────────────────────────────
# A compact but useful English word list (extend as you like)
WORD_LIST = """
the be to of and a in that have it for not on with he as you do at
this but his by from they we say her she or an will my one all would
there their what so up out if about who get which go me when make can
like time no just him know take people into year your good some could
them see other than then now look only come its over think also back
after use two how our work first well way even new want because any
these give day most us able about above across act actually add afraid
after age ago agree ahead air all allow almost alone along already also
always am among and animal another answer any area around art ask at
away back bad ball bank base be bear beat beautiful because become
before begin behind believe below best better between big bird black
blue body book born both box boy break bring build burn buy call
came can care carry catch cause change check child choose city
clean clear close cold color come common control cool cost could
country couple course create cut dark day dead deal deep describe
different direct dog done door down draw dream drink drive drop
during each early earth easy eat either end enough even ever every
example eye face fact fail fall family far fast feel few field
fight fill find fire fish fit follow food force forget form found
free friend from front full fun game get girl give glass go
good great green group grow guess hand happen hard have he head
hear heart help here high him his home hope horse hot house how
human hundred idea if important include information inside interest
into it its job keep kind know land large last late laugh lead learn
leave left less let level life light like line list little live
long look lose love low make man many matter maybe mean meet mind
miss money month more most move much must name near need never new
next night no north nothing now number off often old once only open
order other our out over own page part pass people pick picture
place plan play point possible power put question quite reach read
ready real reason red remember rest right road rock room run said
same say second see seem send serious set short should show side
since sit sleep slow small smile so some son soon sorry south
speak stand start state stay still stop story strong student
such summer sure take talk tell than that the their them then there
these they thing think though thought three time today together too
top toward town tree try turn under until up use very voice wait
walk want war watch water way week well west what when where which
while who why wide will window wish with word work world would
write year yes yet you young your
""".split()

WORD_LIST = sorted(set(w.lower() for w in WORD_LIST if len(w) >= 2))

# ── Keyboard layout ──────────────────────────────────────────────────────────
ROWS = [
    list("qwertyuiop"),
    list("asdfghjkl"),
    list("zxcvbnm"),
]

# ── Geometry ─────────────────────────────────────────────────────────────────
KEY_W, KEY_H = 64, 64
KEY_PAD = 6
CORNER_R = 10
WIN_BG = "#1a1a2e"
KEY_BG = "#16213e"
KEY_HOVER = "#0f3460"
KEY_ACTIVE = "#e94560"
KEY_FG = "#eaeaea"
TRAIL_COLOR = "#e94560"
TRAIL_WIDTH = 3
ACCENT = "#e94560"
TEXT_BG = "#0f0f1a"
FONT_KEY = ("Courier New", 17, "bold")
FONT_TEXT = ("Courier New", 14)
FONT_SMALL = ("Courier New", 11)


# ── Prediction engine ─────────────────────────────────────────────────────────

def key_center(row_idx, col_idx, row_offsets):
    x = row_offsets[row_idx] + col_idx * (KEY_W + KEY_PAD) + KEY_W // 2
    y = 80 + row_idx * (KEY_H + KEY_PAD) + KEY_H // 2
    return x, y


def nearest_key(x, y, centers):
    best, best_dist = None, float("inf")
    for key, (cx, cy) in centers.items():
        d = math.hypot(x - cx, y - cy)
        if d < best_dist:
            best_dist, best = d, key
    return best if best_dist < (KEY_W * 0.85) else None


def word_to_path(word, centers):
    """Convert a word to a sequence of key centers."""
    path = []
    for ch in word.lower():
        if ch in centers:
            path.append(centers[ch])
    return path


def path_similarity(swipe_points, word_path):
    """
    Score how well a swipe matches a word path.
    Uses DTW-lite: resample both to N points, sum distances.
    """
    if not word_path or not swipe_points:
        return float("inf")

    def resample(pts, n):
        if len(pts) == 1:
            return pts * n
        result = []
        total = sum(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])
                    for i in range(len(pts)-1))
        if total == 0:
            return pts[:1] * n
        step = total / (n - 1)
        acc = 0.0
        result.append(pts[0])
        seg = 0
        for _ in range(1, n):
            acc += step
            while seg < len(pts) - 2:
                seg_len = math.hypot(pts[seg+1][0]-pts[seg][0],
                                     pts[seg+1][1]-pts[seg][1])
                if acc <= seg_len + 1e-9:
                    break
                acc -= seg_len
                seg += 1
            seg_len = math.hypot(pts[seg+1][0]-pts[seg][0],
                                 pts[seg+1][1]-pts[seg][1])
            t = acc / seg_len if seg_len > 0 else 0
            rx = pts[seg][0] + t * (pts[seg+1][0] - pts[seg][0])
            ry = pts[seg][1] + t * (pts[seg+1][1] - pts[seg][1])
            result.append((rx, ry))
        return result

    N = max(20, max(len(swipe_points), len(word_path)))
    sp = resample(swipe_points, N)
    wp = resample(word_path, N)
    return sum(math.hypot(sp[i][0]-wp[i][0], sp[i][1]-wp[i][1]) for i in range(N)) / N


def predict(swipe_points, swiped_keys, centers, top_n=5):
    """Return top_n predicted words."""
    if not swiped_keys:
        return []

    first = swiped_keys[0]
    last = swiped_keys[-1]

    candidates = [w for w in WORD_LIST
                  if w[0] == first and w[-1] == last and len(w) >= 2]

    # Also consider words that merely start with the first letter if list thin
    if len(candidates) < 5:
        candidates += [w for w in WORD_LIST
                       if w[0] == first and w not in candidates]

    scored = []
    for word in candidates:
        wp = word_to_path(word, centers)
        score = path_similarity(swipe_points, wp)
        scored.append((score, word))

    scored.sort()
    return [w for _, w in scored[:top_n]]


# ── Main App ──────────────────────────────────────────────────────────────────

class SwipeKeyboard:
    def __init__(self, root):
        self.root = root
        root.title("Swipe Keyboard")
        root.configure(bg=WIN_BG)
        root.resizable(False, False)

        # Compute layout
        self.row_offsets = []
        for row in ROWS:
            total = len(row) * KEY_W + (len(row) - 1) * KEY_PAD
            offset = (10 * (KEY_W + KEY_PAD) - total) // 2 + 8
            self.row_offsets.append(offset)

        self.centers = {}
        for ri, row in enumerate(ROWS):
            for ci, ch in enumerate(row):
                self.centers[ch] = key_center(ri, ci, self.row_offsets)

        canvas_w = int(10 * (KEY_W + KEY_PAD) + 16)
        canvas_h = int(len(ROWS) * (KEY_H + KEY_PAD) + 80 + 20)

        # ── Text display ──
        self.text_var = tk.StringVar(value="")
        text_frame = tk.Frame(root, bg=TEXT_BG, pady=4)
        text_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Label(text_frame, text="✎", bg=TEXT_BG, fg=ACCENT,
                 font=("Courier New", 14)).pack(side=tk.LEFT, padx=(8, 4))
        self.text_display = tk.Entry(
            text_frame, textvariable=self.text_var,
            font=FONT_TEXT, bg=TEXT_BG, fg=KEY_FG,
            insertbackground=ACCENT, relief=tk.FLAT,
            highlightthickness=1, highlightcolor=ACCENT,
            highlightbackground="#333"
        )
        self.text_display.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        # ── Suggestions bar ──
        sug_frame = tk.Frame(root, bg=WIN_BG)
        sug_frame.pack(fill=tk.X, padx=10, pady=(4, 0))
        self.sug_buttons = []
        for i in range(5):
            b = tk.Button(
                sug_frame, text="", font=FONT_SMALL,
                bg="#0f3460", fg=KEY_FG, activebackground=ACCENT,
                activeforeground="#fff", relief=tk.FLAT,
                padx=8, pady=3, cursor="hand2",
                command=lambda idx=i: self._pick_suggestion(idx)
            )
            b.pack(side=tk.LEFT, padx=3, pady=2)
            self.sug_buttons.append(b)

        # ── Canvas ──
        self.canvas = tk.Canvas(
            root, width=canvas_w, height=canvas_h,
            bg=WIN_BG, highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=8)

        # ── Special buttons ──
        btn_frame = tk.Frame(root, bg=WIN_BG)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        for label, cmd in [
            ("⌫  Backspace", self._backspace),
            ("␣  Space", self._space),
            ("⌦  Clear all", self._clear),
            ("⎘  Copy", self._copy),
        ]:
            tk.Button(
                btn_frame, text=label, font=FONT_SMALL,
                bg=KEY_BG, fg=KEY_FG, activebackground=ACCENT,
                activeforeground="#fff", relief=tk.FLAT,
                padx=10, pady=6, cursor="hand2", command=cmd
            ).pack(side=tk.LEFT, padx=4)

        # ── State ──
        self.swipe_points = []
        self.swiped_keys = []
        self.trail_ids = []
        self.key_items = {}   # ch -> (rect_id, text_id)
        self.suggestions = []
        self.dragging = False
        self.last_key = None

        self._draw_keys()

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # status label
        self.status = tk.Label(root, text="Draw across letters to swipe a word",
                               bg=WIN_BG, fg="#555", font=FONT_SMALL)
        self.status.pack(pady=(0, 6))

    # ── Drawing ──────────────────────────────────────────────────────────────

    def _draw_keys(self):
        self.canvas.delete("keys")
        self.key_items.clear()
        for ri, row in enumerate(ROWS):
            for ci, ch in enumerate(row):
                cx, cy = self.centers[ch]
                x0 = cx - KEY_W // 2
                y0 = cy - KEY_H // 2
                x1 = cx + KEY_W // 2
                y1 = cy + KEY_H // 2
                rid = self._rounded_rect(x0, y0, x1, y1, CORNER_R, KEY_BG, tags="keys")
                tid = self.canvas.create_text(
                    cx, cy, text=ch.upper(),
                    font=FONT_KEY, fill=KEY_FG, tags="keys"
                )
                self.key_items[ch] = (rid, tid)

    def _rounded_rect(self, x0, y0, x1, y1, r, fill, outline="", tags=""):
        pts = [
            x0+r, y0,  x1-r, y0,
            x1, y0,    x1, y0+r,
            x1, y1-r,  x1, y1,
            x1-r, y1,  x0+r, y1,
            x0, y1,    x0, y1-r,
            x0, y0+r,  x0, y0,
            x0+r, y0,
        ]
        return self.canvas.create_polygon(
            pts, smooth=True,
            fill=fill, outline=outline, tags=tags
        )

    def _highlight_key(self, ch, color):
        if ch in self.key_items:
            self.canvas.itemconfig(self.key_items[ch][0], fill=color)

    def _reset_key_colors(self):
        for ch, (rid, _) in self.key_items.items():
            self.canvas.itemconfig(rid, fill=KEY_BG)

    def _add_trail_point(self, x, y):
        if self.swipe_points:
            px, py = self.swipe_points[-1]
            lid = self.canvas.create_line(
                px, py, x, y,
                fill=TRAIL_COLOR, width=TRAIL_WIDTH,
                capstyle=tk.ROUND, smooth=True
            )
            self.trail_ids.append(lid)
            # dot
            dot = self.canvas.create_oval(
                x-4, y-4, x+4, y+4,
                fill=TRAIL_COLOR, outline=""
            )
            self.trail_ids.append(dot)

    def _clear_trail(self):
        for i in self.trail_ids:
            self.canvas.delete(i)
        self.trail_ids.clear()

    # ── Mouse events ─────────────────────────────────────────────────────────

    def _on_press(self, event):
        self.dragging = True
        self.swipe_points = [(event.x, event.y)]
        self.swiped_keys = []
        self.last_key = None
        self._clear_trail()
        self._reset_key_colors()
        self._update_suggestions([])

        k = nearest_key(event.x, event.y, self.centers)
        if k:
            self.swiped_keys.append(k)
            self.last_key = k
            self._highlight_key(k, KEY_ACTIVE)

    def _on_drag(self, event):
        if not self.dragging:
            return
        self._add_trail_point(event.x, event.y)
        self.swipe_points.append((event.x, event.y))

        k = nearest_key(event.x, event.y, self.centers)
        if k and k != self.last_key:
            self.swiped_keys.append(k)
            self.last_key = k
            self._highlight_key(k, KEY_ACTIVE)

    def _on_release(self, event):
        if not self.dragging:
            return
        self.dragging = False

        if len(self.swiped_keys) == 1:
            # single tap → type the letter
            self._type_text(self.swiped_keys[0])
            self.status.config(text=f"Typed: {self.swiped_keys[0].upper()}")
        elif len(self.swiped_keys) > 1:
            preds = predict(self.swipe_points, self.swiped_keys, self.centers)
            if preds:
                self._type_text(preds[0] + " ")
                self._update_suggestions(preds)
                self.status.config(text=f"Swiped: {''.join(self.swiped_keys)} → {preds[0]}")
            else:
                self.status.config(text="No match found. Try again.")

        self._reset_key_colors()
        self._clear_trail()
        self.swipe_points = []
        self.swiped_keys = []
        self.last_key = None

    # ── Text helpers ──────────────────────────────────────────────────────────

    def _type_text(self, s):
        cur = self.text_var.get()
        self.text_var.set(cur + s)
        self.text_display.icursor(tk.END)

    def _backspace(self):
        cur = self.text_var.get()
        if cur:
            # Delete last word if ends with space, else last char
            if cur.endswith(" "):
                self.text_var.set(cur[:-1])
            else:
                idx = cur.rfind(" ")
                self.text_var.set(cur[:idx+1] if idx >= 0 else "")

    def _space(self):
        self._type_text(" ")

    def _clear(self):
        self.text_var.set("")

    def _copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.text_var.get())
        self.status.config(text="Copied to clipboard!")

    def _update_suggestions(self, words):
        self.suggestions = words
        for i, btn in enumerate(self.sug_buttons):
            if i < len(words):
                btn.config(text=words[i], state=tk.NORMAL)
            else:
                btn.config(text="", state=tk.DISABLED)

    def _pick_suggestion(self, idx):
        if idx >= len(self.suggestions):
            return
        word = self.suggestions[idx]
        cur = self.text_var.get()
        # Replace the last word
        parts = cur.rstrip().rsplit(" ", 1)
        base = parts[0] + " " if len(parts) > 1 else ""
        self.text_var.set(base + word + " ")
        self.text_display.icursor(tk.END)
        self._update_suggestions([])


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app = SwipeKeyboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()