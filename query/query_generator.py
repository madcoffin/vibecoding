import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import csv
import os

# ── 색상 & 폰트 ──────────────────────────────────────────────
BG      = "#ffffff"
TEXT    = "#111111"
MUTED   = "#888888"
BORDER  = "#e0e0e0"
SQL_BG  = "#f4f4f4"
F_BODY  = ("Helvetica Neue", 11)
F_SM    = ("Helvetica Neue", 9)
F_XS    = ("Helvetica Neue", 8)
F_BOLD  = ("Helvetica Neue", 10, "bold")
F_TITLE = ("Helvetica Neue", 20, "bold")
F_SUB   = ("Helvetica Neue", 10)
F_NUM   = ("Helvetica Neue", 24, "bold")
F_MON   = ("Menlo", 10)
PAD     = 40


# ── macOS 호환 버튼 (Label 기반) ────────────────────────────
class FlatBtn(tk.Label):
    def __init__(self, parent, text, command, dark=True, **kw):
        self._dark = dark
        self._cmd  = command
        self._bg   = "#111111" if dark else BG
        self._fg   = "#ffffff" if dark else TEXT
        self._hov  = "#333333" if dark else "#f0f0f0"
        super().__init__(
            parent, text=text,
            bg=self._bg, fg=self._fg,
            font=F_BOLD if dark else F_SM,
            cursor="hand2",
            padx=20, pady=8,
            **kw
        )
        self.bind("<Button-1>", lambda _: command())
        self.bind("<Enter>",    lambda _: self.config(bg=self._hov))
        self.bind("<Leave>",    lambda _: self.config(bg=self._bg))

    def flash(self, text, temp_bg="#444444", ms=2000):
        orig_text = self["text"]
        self.config(text=text, bg=temp_bg)
        self.after(ms, lambda: self.config(text=orig_text, bg=self._bg))


# ── CSV 파싱 ────────────────────────────────────────────────
def parse_csv(filepath):
    pairs, seen = [], set()
    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise ValueError("CSV 파일이 비어 있습니다.")
        hs = [h.strip() for h in header]
        try:
            ei = hs.index('이메일')
        except ValueError:
            raise ValueError(f"'이메일' 열을 찾을 수 없습니다.\n헤더: {hs}")
        try:
            ci = hs.index('상품코드')
        except ValueError:
            raise ValueError(f"'상품코드' 열을 찾을 수 없습니다.\n헤더: {hs}")
        for row in reader:
            if len(row) <= max(ei, ci):
                continue
            email = row[ei].strip()
            code  = row[ci].strip()
            if not email or not code:
                continue
            key = (email, code)
            if key not in seen:
                seen.add(key)
                pairs.append({'email': email, 'code': code})
    return pairs


# ── 쿼리 생성 ───────────────────────────────────────────────
def sql_str(s):
    return "'" + s.replace("'", "''") + "'"


def build_query(pairs):
    unique_products = list(dict.fromkeys(p['code'] for p in pairs))
    indent = '        '
    value_lines = ',\n'.join(
        f"{indent}({i}, {sql_str(p['email'])}, {sql_str(p['code'])})"
        for i, p in enumerate(pairs, 1)
    )
    in_list = ', '.join(sql_str(c) for c in unique_products)
    return f"""WITH combinations AS (
    -- 조회 대상 (이메일, 상품코드) 조합 — idx는 CSV 원본 행 순서
    SELECT idx, email, product_code
    FROM (VALUES
{value_lines}
    ) AS t(idx, email, product_code)
),
products_mapped AS (
    -- old_product_id → 내부 product_id 매핑
    SELECT p.id AS product_id, p.old_product_id
    FROM products p
    WHERE p.old_product_id IN ({in_list})
)
SELECT
    m.email,
    pm.old_product_id AS product_code,
    mc.progress
FROM members m
JOIN combinations c       ON m.email = c.email
JOIN products_mapped pm   ON pm.old_product_id = c.product_code
JOIN my_contents mc       ON mc.member_id = m.id
                         AND mc.product_id = pm.product_id
ORDER BY c.idx;"""


# ── 원형 프로필 이미지 ──────────────────────────────────────
def load_author_photo(size=40):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for name in ("author.jpg", "author.jpeg", "author.png"):
        path = os.path.join(script_dir, name)
        if os.path.exists(path):
            try:
                from PIL import Image, ImageTk, ImageDraw, ImageOps
                img = Image.open(path).convert("RGBA")
                img = ImageOps.fit(img, (size, size), Image.LANCZOS)
                mask = Image.new("L", (size, size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
                img.putalpha(mask)
                return ImageTk.PhotoImage(img)
            except Exception:
                pass
    return None


# ── 구분선 ──────────────────────────────────────────────────
def divider(parent):
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")


# ── 메인 앱 ─────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("진도율 쿼리문 생성")
        self.geometry("880x820")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._pairs = []
        self._photo_ref = None   # GC 방지
        self._style_tree()
        self._build_ui()

    def _style_tree(self):
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("M.Treeview",
                    background=BG, foreground=TEXT,
                    fieldbackground=BG, rowheight=26,
                    font=F_SM, borderwidth=0)
        s.configure("M.Treeview.Heading",
                    background=BG, foreground=MUTED,
                    font=F_XS, borderwidth=0, relief="flat")
        s.map("M.Treeview",
              background=[("selected", "#eeeeee")],
              foreground=[("selected", TEXT)])
        s.layout("M.Treeview",
                 [("M.Treeview.treearea", {"sticky": "nswe"})])

    def _build_ui(self):

        # ── 타이틀 + 작성자 ────────────────────────────────
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=PAD, pady=(32, 0))

        # 왼쪽: 타이틀
        left = tk.Frame(top, bg=BG)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text="진도율 쿼리문 생성",
                 bg=BG, fg=TEXT, font=F_TITLE, anchor="w").pack(fill="x")
        tk.Label(left,
                 text="CSV 파일의 이메일·상품코드를 읽어 수강률 조회 쿼리를 생성합니다.",
                 bg=BG, fg=MUTED, font=F_SUB, anchor="w").pack(fill="x", pady=(4, 0))

        # 오른쪽: 작성자
        author = tk.Frame(top, bg=BG)
        author.pack(side="right", anchor="ne")

        photo = load_author_photo(size=44)
        if photo:
            self._photo_ref = photo
            tk.Label(author, image=photo, bg=BG, bd=0).pack(side="left", padx=(0, 8))
        else:
            # 사진 없으면 이니셜 원
            circle = tk.Canvas(author, width=44, height=44,
                               bg=BG, highlightthickness=0)
            circle.create_oval(0, 0, 44, 44, fill="#111111", outline="")
            circle.create_text(22, 22, text="M",
                               fill="white", font=("Helvetica Neue", 16, "bold"))
            circle.pack(side="left", padx=(0, 8))

        tk.Label(author, text="madcoffin",
                 bg=BG, fg=MUTED, font=F_SM, anchor="e").pack(side="left")

        tk.Frame(self, bg=BG, height=24).pack()
        divider(self)

        # ── 파일 선택 ──────────────────────────────────────
        fsec = tk.Frame(self, bg=BG)
        fsec.pack(fill="x", padx=PAD, pady=22)

        info = tk.Frame(fsec, bg=BG)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text="FILE", bg=BG, fg=MUTED,
                 font=F_XS, anchor="w").pack(fill="x")
        self.path_var = tk.StringVar(value="선택된 파일 없음")
        tk.Label(info, textvariable=self.path_var,
                 bg=BG, fg=TEXT, font=F_BODY, anchor="w").pack(fill="x", pady=(3, 0))

        FlatBtn(fsec, "열기", self._open_file, dark=True).pack(side="right")

        divider(self)

        # ── 통계 ───────────────────────────────────────────
        ssec = tk.Frame(self, bg=BG)
        ssec.pack(fill="x", padx=PAD, pady=18)
        self._stat = {}
        for key, label in [("pairs","조합"), ("emails","이메일"),
                           ("products","상품코드"), ("rows","데이터 행")]:
            col = tk.Frame(ssec, bg=BG)
            col.pack(side="left", expand=True, fill="x")
            v = tk.Label(col, text="—", bg=BG, fg=TEXT, font=F_NUM, anchor="w")
            v.pack(fill="x")
            tk.Label(col, text=label, bg=BG, fg=MUTED, font=F_SM, anchor="w").pack(fill="x")
            self._stat[key] = v

        divider(self)

        # ── 미리보기 ───────────────────────────────────────
        psec = tk.Frame(self, bg=BG)
        psec.pack(fill="x", padx=PAD, pady=(14, 0))
        tk.Label(psec, text="PREVIEW", bg=BG, fg=MUTED,
                 font=F_XS, anchor="w").pack(fill="x", pady=(0, 6))

        cols = ("#", "이메일", "상품코드")
        self.tree = ttk.Treeview(psec, columns=cols,
                                 show="headings", height=4,
                                 style="M.Treeview")
        for c in cols:
            self.tree.heading(c, text=c, anchor="w")
        self.tree.column("#",        width=36,  anchor="w", stretch=False)
        self.tree.column("이메일",   width=300, anchor="w")
        self.tree.column("상품코드", width=160, anchor="w")
        self.tree.pack(fill="x")

        divider(self)

        # ── SQL ────────────────────────────────────────────
        qsec = tk.Frame(self, bg=BG)
        qsec.pack(fill="x", padx=PAD, pady=(14, 6))
        tk.Label(qsec, text="SQL", bg=BG, fg=MUTED,
                 font=F_XS, anchor="w").pack(side="left")

        brow = tk.Frame(qsec, bg=BG)
        brow.pack(side="right")
        self.copy_btn = FlatBtn(brow, "복사", self._copy_query, dark=True)
        self.copy_btn.pack(side="left", padx=(0, 8))
        FlatBtn(brow, "저장", self._save_file, dark=False).pack(side="left")

        self.sql_box = scrolledtext.ScrolledText(
            self, font=F_MON,
            bg=SQL_BG, fg=TEXT,
            insertbackground=TEXT,
            relief="flat", wrap="none",
            height=24,                      # ← 2배
            padx=16, pady=14,
            selectbackground="#dddddd",
            selectforeground=TEXT)
        self.sql_box.pack(fill="both", expand=True, padx=PAD, pady=(4, 28))

    # ── 핸들러 ─────────────────────────────────────────────

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="CSV 파일 선택",
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")])
        if not path:
            return
        try:
            pairs = parse_csv(path)
        except Exception as e:
            messagebox.showerror("오류", f"파일 읽기 실패:\n{e}")
            return
        if not pairs:
            messagebox.showwarning("경고", "'이메일'·'상품코드' 열에서 유효한 데이터를 찾지 못했습니다.")
            return

        self._pairs = pairs
        self.path_var.set(os.path.basename(path))

        ue = len(set(p['email'] for p in pairs))
        up = len(set(p['code']  for p in pairs))
        self._stat["rows"].config(text=str(len(pairs)))
        self._stat["emails"].config(text=str(ue))
        self._stat["products"].config(text=str(up))
        self._stat["pairs"].config(text=str(len(pairs)))

        for row in self.tree.get_children():
            self.tree.delete(row)
        for i, p in enumerate(pairs[:10], 1):
            self.tree.insert("", "end", values=(i, p['email'], p['code']))

        self.sql_box.delete("1.0", "end")
        self.sql_box.insert("1.0", build_query(pairs))

    def _copy_query(self):
        q = self.sql_box.get("1.0", "end-1c")
        if not q.strip():
            return
        self.clipboard_clear()
        self.clipboard_append(q)
        self.copy_btn.flash("복사됨 ✓")

    def _save_file(self):
        q = self.sql_box.get("1.0", "end-1c")
        if not q.strip():
            messagebox.showwarning("경고", "저장할 쿼리가 없습니다.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".sql",
            filetypes=[("SQL 파일", "*.sql"), ("텍스트 파일", "*.txt")],
            initialfile="query.sql")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(q)
        messagebox.showinfo("저장 완료", f"저장되었습니다:\n{path}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
