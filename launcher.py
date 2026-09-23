import os
import sys
import json
import time
import sqlite3
import hashlib
import threading
import subprocess
import customtkinter as ctk
from tkinter import messagebox
import tkinter.filedialog as fd
from datetime import datetime

from gta2_reader import get_stats_if_changed


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "arcade.db")
SRC_DIR = os.path.join(BASE_DIR, "src")


PALETTE = {
    "bg_1": "#0a0a1a",
    "bg_2": "#1a0a2a",
    "bg_3": "#2a0a3a",
    "bg_4": "#0a1a3a",
    "surface": "#14142a",
    "surface_alt": "#1e1e3a",
    "surface_hover": "#2a2a4a",
    "border": "#3a3a5a",
    "text": "#f0f0ff",
    "text_dim": "#9090b0",
    "white": "#ffffff",
    "snake": "#06b6d4",
    "snake_dark": "#06b6d4",
    "flappy": "#06b6d4",
    "flappy_dark": "#06b6d4",
    "tetris": "#06b6d4",
    "tetris_dark": "#06b6d4",
    "pacman": "#06b6d4",
    "pacman_dark": "#06b6d4",
    "mk": "#06b6d4",
    "mk_dark": "#06b6d4",
    "gta": "#06b6d4",
    "gta_dark": "#0891b2",
    "tanks": "#06b6d4",
    "tanks_dark": "#06b6d4",
    "scores": "#38bdf8",
    "scores_dark": "#38bdf8",
    "stats": "#38bdf8",
    "stats_dark": "#2090d0",
    "logout": "#f97316",
    "logout_dark": "#d06020",
    "exit": "#64748b",
    "exit_dark": "#475569",
    "accent": "#8b5cf6",
    "accent_dark": "#6d28d9",
    "success": "#10b981",
    "success_dark": "#059669",
    "danger": "#ef4444",
    "danger_dark": "#b91c1c",
}


GAMES = [
    {"key": "snake", "emoji": "🐍", "name": "Змейка", "color": "snake"},
    {"key": "flappybird", "emoji": "🐦", "name": "Flappy Bird", "color": "flappy"},
    {"key": "tetris", "emoji": "🧱", "name": "Tetris", "color": "tetris"},
    {"key": "pacmen", "emoji": "👻", "name": "Pac-Man", "color": "pacman"},
    {"key": "mc", "emoji": "⚔️", "name": "Mortal Kombat", "color": "mk"},
    {"key": "tanks", "emoji": "🔫", "name": "Battle City", "color": "tanks"},
    {"key": "gta2", "emoji": "🚗", "name": "GTA 2", "color": "gta"},
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game TEXT NOT NULL,
            score INTEGER NOT NULL,
            played_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS gta2_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            save_name TEXT,
            save_hash TEXT,
            money INTEGER,
            district INTEGER,
            day INTEGER,
            kills INTEGER,
            police_kills INTEGER,
            cars_destroyed INTEGER,
            missions_done INTEGER,
            played_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, hash_password(password), datetime.now().isoformat())
        )
        conn.commit()
        uid = c.lastrowid
        conn.close()
        return uid
    except sqlite3.IntegrityError:
        conn.close()
        return None


def login_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row and row[1] == hash_password(password):
        return row[0]
    return None


def add_score(user_id, game, score):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO scores (user_id, game, score, played_at) VALUES (?, ?, ?, ?)",
        (user_id, game, score, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_top_scores(game=None, limit=15):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if game:
        c.execute("""
            SELECT u.username, s.game, s.score, s.played_at
            FROM scores s JOIN users u ON u.id = s.user_id
            WHERE s.game = ? ORDER BY s.score DESC LIMIT ?
        """, (game, limit))
    else:
        c.execute("""
            SELECT u.username, s.game, s.score, s.played_at
            FROM scores s JOIN users u ON u.id = s.user_id
            ORDER BY s.score DESC LIMIT ?
        """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def insert_gta2_stats(user_id, stats):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO gta2_stats (
            user_id, save_name, save_hash, money, district, day,
            kills, police_kills, cars_destroyed, missions_done, played_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        stats.get("name", ""),
        stats.get("hash", ""),
        stats.get("money", 0),
        stats.get("district", 0),
        stats.get("day", 0),
        stats.get("kills", 0),
        stats.get("police_kills", 0),
        stats.get("cars_destroyed", 0),
        stats.get("missions_done", 0),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def last_gta2_hash(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT save_hash FROM gta2_stats
        WHERE user_id = ? ORDER BY played_at DESC LIMIT 1
    """, (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_gta2_stats(user_id, limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT save_name, money, district, day, kills, police_kills,
               cars_destroyed, missions_done, played_at
        FROM gta2_stats WHERE user_id = ?
        ORDER BY played_at DESC LIMIT ?
    """, (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


class GTA2Watcher(threading.Thread):
    def __init__(self, user_id, process, interval=60):
        super().__init__(daemon=True)
        self.user_id = user_id
        self.process = process
        self.interval = interval
        self.stop_flag = threading.Event()
        self.last_hash = last_gta2_hash(user_id)

    def run(self):
        while not self.stop_flag.is_set():
            time.sleep(self.interval)
            if self.process.poll() is not None:
                self.check_once()
                break
            self.check_once()

    def check_once(self):
        try:
            stats, new_hash = get_stats_if_changed(self.last_hash)
            if stats:
                insert_gta2_stats(self.user_id, stats)
                self.last_hash = new_hash
        except Exception:
            pass


class ArcadeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.current_user_id = None
        self.current_username = None
        self.watcher = None

        ctk.set_appearance_mode("dark")
        self.attributes("-fullscreen", True)
        self.title("Аркадный Автомат")
        self.configure(fg_color=PALETTE["bg_1"])
        self.bind("<Escape>", self.on_escape)

        self.update_idletasks()
        self.W = self.winfo_screenwidth()
        self.H = self.winfo_screenheight()

        ref_w, ref_h = 1920, 1080
        self.scale = min(self.W / ref_w, self.H / ref_h)
        self.scale = max(0.45, min(self.scale, 2.5))

        self._build_background()

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.show_login()

    # ---------- утилиты ----------

    def s(self, px):
        return max(1, int(px * self.scale))

    def fs(self, px, minimum=11):
        return max(minimum, int(px * self.scale))

    def _build_background(self):
        canvas = ctk.CTkCanvas(self, highlightthickness=0, bd=0)
        canvas.place(x=0, y=0, relwidth=1, relheight=1)
        try:
            canvas.tk.call("lower", canvas._w)
        except Exception:
            pass

        stops = [
            PALETTE["bg_1"],
            PALETTE["bg_2"],
            PALETTE["bg_3"],
            PALETTE["bg_4"],
            PALETTE["bg_1"],
        ]

        def hex_rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

        rgb_stops = [hex_rgb(c) for c in stops]
        steps = 160
        segments = len(rgb_stops) - 1

        for i in range(steps):
            t = i / (steps - 1)
            seg = min(int(t * segments), segments - 1)
            local_t = t * segments - seg
            c1 = rgb_stops[seg]
            c2 = rgb_stops[seg + 1]
            r = int(c1[0] * (1 - local_t) + c2[0] * local_t)
            g = int(c1[1] * (1 - local_t) + c2[1] * local_t)
            b = int(c1[2] * (1 - local_t) + c2[2] * local_t)
            y1 = int(self.H * i / steps)
            y2 = int(self.H * (i + 1) / steps) + 1
            canvas.create_rectangle(
                0, y1, self.W, y2,
                fill="#{:02x}{:02x}{:02x}".format(r, g, b),
                outline=""
            )

        self._bg_canvas = canvas

    def on_escape(self, event=None):
        self.destroy()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _title_label(self, parent, text, size=42, color=None):
        return ctk.CTkLabel(
            parent, text=text,
            font=("Segoe UI", self.fs(size), "bold"),
            text_color=color or PALETTE["white"]
        )

    def _subtitle_label(self, parent, text, size=15, color=None):
        return ctk.CTkLabel(
            parent, text=text,
            font=("Segoe UI", self.fs(size)),
            text_color=color or PALETTE["text_dim"]
        )

    def _entry(self, parent, placeholder, width=340, height=48, show=None):
        return ctk.CTkEntry(
            parent,
            width=self.s(width), height=self.s(height),
            placeholder_text=placeholder,
            placeholder_text_color=PALETTE["text_dim"],
            font=("Segoe UI", self.fs(15)),
            show=show,
            fg_color=PALETTE["surface_alt"],
            border_color=PALETTE["border"],
            border_width=self.s(1),
            text_color=PALETTE["text"],
            corner_radius=self.s(10),
        )

    def _button(self, parent, text, command, width=320, height=50,
                base="accent", font_size=16, bold=True):
        fg = PALETTE.get(base, PALETTE["accent"])
        hover = PALETTE.get(base + "_dark", PALETTE["accent_dark"])
        return ctk.CTkButton(
            parent,
            text=text, command=command,
            width=self.s(width), height=self.s(height),
            corner_radius=self.s(12),
            font=("Segoe UI", self.fs(font_size), "bold" if bold else "normal"),
            fg_color=fg, hover_color=hover,
            text_color=PALETTE["white"],
            border_width=0,
        )

    def _centered_card(self, w, h):
        card = ctk.CTkFrame(
            self.container,
            width=self.s(w), height=self.s(h),
            fg_color=PALETTE["surface"],
            border_color=PALETTE["border"],
            border_width=self.s(2),
            corner_radius=self.s(22),
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)
        return card

    # ---------- экраны ----------

    def show_login(self):
        self.clear()
        self.container.configure(fg_color="transparent")

        card = self._centered_card(440, 580)

        icon = ctk.CTkLabel(
            card, text="🎮",
            font=("Segoe UI Emoji", self.fs(64)),
        )
        icon.pack(pady=(self.s(35), self.s(5)))

        self._title_label(card, "Аркадный Автомат", 28).pack()
        self._subtitle_label(card, "Вход в аккаунт", 15).pack(pady=(self.s(4), self.s(24)))

        self.login_entry = self._entry(card, "👤  Логин")
        self.login_entry.pack(pady=self.s(6))

        self.pass_entry = self._entry(card, "🔒  Пароль", show="●")
        self.pass_entry.pack(pady=self.s(6))

        self._button(card, "Войти", self.do_login,
                     width=340, height=52, base="success").pack(pady=(self.s(24), self.s(8)))

        self._button(card, "Регистрация", self.show_register,
                     width=340, height=44, base="accent", font_size=15).pack(pady=self.s(6))

        self._button(card, "Выход", self.destroy,
                     width=340, height=40, base="danger", font_size=14, bold=False).pack(pady=(self.s(6), self.s(20)))

        self.pass_entry.bind("<Return>", lambda e: self.do_login())
        self.login_entry.bind("<Return>", lambda e: self.pass_entry.focus())

    def do_login(self):
        username = self.login_entry.get().strip()
        password = self.pass_entry.get().strip()
        if not username or not password:
            messagebox.showerror("Ошибка", "Заполните все поля")
            return
        uid = login_user(username, password)
        if uid:
            self.current_user_id = uid
            self.current_username = username
            self.show_menu()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def show_register(self):
        self.clear()
        self.container.configure(fg_color="transparent")

        card = self._centered_card(440, 620)

        icon = ctk.CTkLabel(card, text="✨", font=("Segoe UI Emoji", self.fs(56)))
        icon.pack(pady=(self.s(30), self.s(5)))

        self._title_label(card, "Регистрация", 28).pack()
        self._subtitle_label(card, "Создайте новый аккаунт", 15).pack(pady=(self.s(4), self.s(24)))

        self.reg_login = self._entry(card, "👤  Логин")
        self.reg_login.pack(pady=self.s(6))

        self.reg_pass = self._entry(card, "🔒  Пароль", show="●")
        self.reg_pass.pack(pady=self.s(6))

        self.reg_pass2 = self._entry(card, "🔒  Повтор пароля", show="●")
        self.reg_pass2.pack(pady=self.s(6))

        self._button(card, "Создать аккаунт", self.do_register,
                     width=340, height=52, base="success").pack(pady=(self.s(24), self.s(8)))

        self._button(card, "Назад", self.show_login,
                     width=340, height=42, base="accent", font_size=15, bold=False).pack(pady=self.s(6))

    def do_register(self):
        username = self.reg_login.get().strip()
        password = self.reg_pass.get().strip()
        password2 = self.reg_pass2.get().strip()

        if not username or not password:
            messagebox.showerror("Ошибка", "Заполните все поля")
            return
        if password != password2:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return
        if len(password) < 4:
            messagebox.showerror("Ошибка", "Пароль должен быть не короче 4 символов")
            return

        uid = register_user(username, password)
        if uid:
            messagebox.showinfo("Успех", "Аккаунт создан")
            self.show_login()
        else:
            messagebox.showerror("Ошибка", "Такой логин уже существует")

    def show_menu(self):
        self.clear()
        self.container.configure(fg_color="transparent")

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.place(relx=0.5, rely=0.09, anchor="center")

        ctk.CTkLabel(header, text="🕹️",
                     font=("Segoe UI Emoji", self.fs(46))).pack()

        self._title_label(header, "Аркадный Автомат", 40).pack(pady=(self.s(2), 0))

        user_row = ctk.CTkFrame(header, fg_color="transparent")
        user_row.pack(pady=(self.s(10), 0))

        ctk.CTkLabel(
            user_row, text="👤",
            font=("Segoe UI Emoji", self.fs(18)),
        ).pack(side="left", padx=(0, self.s(6)))

        ctk.CTkLabel(
            user_row, text=self.current_username,
            font=("Segoe UI", self.fs(18), "bold"),
            text_color=PALETTE["accent"],
        ).pack(side="left")

        grid = ctk.CTkFrame(self.container, fg_color="transparent")
        grid.place(relx=0.5, rely=0.47, anchor="center")

        cols = 4
        btn_w = 210
        btn_h = 96
        pad = 12

        for idx, game in enumerate(GAMES):
            row = idx // cols
            col = idx % cols

            fg = PALETTE.get(game["color"], PALETTE["accent"])
            hover = PALETTE.get(game["color"] + "_dark", PALETTE["accent_dark"])

            btn = ctk.CTkButton(
                grid,
                text=f"{game['emoji']}\n{game['name']}",
                command=lambda k=game["key"]: self._on_game(k),
                width=self.s(btn_w), height=self.s(btn_h),
                corner_radius=self.s(16),
                font=("Segoe UI", self.fs(15), "bold"),
                fg_color=fg, hover_color=hover,
                text_color=PALETTE["white"],
                border_width=0,
            )
            btn.grid(row=row, column=col,
                     padx=self.s(pad), pady=self.s(pad), sticky="nsew")

        services = ctk.CTkFrame(self.container, fg_color="transparent")
        services.place(relx=0.5, rely=0.82, anchor="center")

        self._button(services, "🏆  Таблица результатов", self.show_scores,
                     width=280, height=50, base="scores").pack(side="left", padx=self.s(8))

        self._button(services, "📊  GTA 2 — статистика", self.show_gta2_stats,
                     width=280, height=50, base="stats").pack(side="left", padx=self.s(8))

        bottom = ctk.CTkFrame(self.container, fg_color="transparent")
        bottom.place(relx=0.5, rely=0.93, anchor="center")

        self._button(bottom, "🚪  Сменить аккаунт", self.logout,
                     width=280, height=42, base="logout", font_size=14).pack(side="left", padx=self.s(8))

        self._button(bottom, "❌  Выход", self.destroy,
                     width=280, height=42, base="exit", font_size=14).pack(side="left", padx=self.s(8))

    def _on_game(self, key):
        if key == "gta2":
            self.launch_gta2()
        else:
            self.launch_game(key)

    def logout(self):
        if self.watcher and self.watcher.is_alive():
            self.watcher.stop_flag.set()
        self.watcher = None
        self.current_user_id = None
        self.current_username = None
        self.show_login()

    def launch_game(self, game):
        script_map = {
            "snake": os.path.join(SRC_DIR, "snake.py"),
            "flappybird": os.path.join(SRC_DIR, "flappybird.py"),
            "tetris": os.path.join(SRC_DIR, "tetris.py"),
            "pacmen": os.path.join(SRC_DIR, "pacmen.py"),
            "mc": os.path.join(SRC_DIR, "mc.py"),
            "tanks": os.path.join(SRC_DIR, "tanks.py"),
        }
        path = script_map.get(game)
        if not path or not os.path.exists(path):
            messagebox.showerror("Ошибка", f"Файл не найден: {path}")
            return

        score_file = os.path.join(BASE_DIR, "last_score.json")
        if os.path.exists(score_file):
            try:
                os.remove(score_file)
            except OSError:
                pass

        env = os.environ.copy()
        env["ARCADE_USER"] = self.current_username or ""
        env["ARCADE_USER_ID"] = str(self.current_user_id or 0)
        env["ARCADE_SCORE_FILE"] = score_file

        try:
            subprocess.Popen([sys.executable, path], env=env)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить: {e}")
            return

        self.after(2000, lambda: self.check_score(score_file, game))

    def check_score(self, score_file, game):
        if os.path.exists(score_file):
            try:
                with open(score_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                score = int(data.get("score", 0))
                if score > 0 and self.current_user_id:
                    add_score(self.current_user_id, game, score)
            except (OSError, ValueError, json.JSONDecodeError):
                pass
            try:
                os.remove(score_file)
            except OSError:
                pass
            return
        self.after(3000, lambda: self.check_score(score_file, game))

    def launch_gta2(self):
        path = fd.askopenfilename(
            title="Выберите gta2.exe",
            filetypes=[("Исполняемые", "*.exe"), ("Все файлы", "*.*")]
        )
        if not path:
            return

        if self.watcher and self.watcher.is_alive():
            messagebox.showinfo("GTA 2", "Сбор статистики уже запущен")
            return

        try:
            process = subprocess.Popen([path], cwd=os.path.dirname(path))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить GTA 2: {e}")
            return

        self.watcher = GTA2Watcher(self.current_user_id, process, interval=60)
        self.watcher.start()

        messagebox.showinfo(
            "GTA 2",
            "Игра запущена.\nСтатистика собирается каждую минуту."
        )

    def _make_table(self, parent, columns, rows, header_color_key, row_renderer=None):
        table_frame = ctk.CTkFrame(
            parent, fg_color=PALETTE["surface_alt"],
            corner_radius=self.s(12),
        )
        table_frame.pack(fill="both", expand=True, padx=self.s(12), pady=self.s(12))

        header_color = PALETTE.get(header_color_key, PALETTE["accent"])

        header = ctk.CTkFrame(
            table_frame, fg_color=header_color,
            corner_radius=self.s(8), height=self.s(44),
        )
        header.pack(fill="x", padx=self.s(8), pady=(self.s(8), self.s(4)))
        header.pack_propagate(False)

        for i, (name, weight) in enumerate(columns):
            header.grid_columnconfigure(i, weight=weight, uniform="col")
        header.grid_rowconfigure(0, weight=1)

        for i, (name, _) in enumerate(columns):
            ctk.CTkLabel(
                header, text=name,
                font=("Segoe UI", self.fs(14), "bold"),
                text_color=PALETTE["white"],
            ).grid(row=0, column=i, sticky="nsew", padx=self.s(4))

        if not rows:
            ctk.CTkLabel(
                table_frame, text="Пока нет данных 🎯",
                font=("Segoe UI", self.fs(16)),
                text_color=PALETTE["text_dim"],
            ).pack(pady=self.s(40))
            return

        scroll = ctk.CTkScrollableFrame(
            table_frame, fg_color="transparent",
            scrollbar_button_color=header_color,
            scrollbar_button_hover_color=PALETTE["border"],
        )
        scroll.pack(fill="both", expand=True, padx=self.s(8), pady=(0, self.s(8)))

        for idx, row in enumerate(rows):
            bg = PALETTE["surface"] if idx % 2 == 0 else PALETTE["surface_alt"]

            row_frame = ctk.CTkFrame(
                scroll, fg_color=bg,
                corner_radius=self.s(6), height=self.s(38),
            )
            row_frame.pack(fill="x", pady=self.s(2))
            row_frame.pack_propagate(False)

            for i, (_, weight) in enumerate(columns):
                row_frame.grid_columnconfigure(i, weight=weight, uniform="col")
            row_frame.grid_rowconfigure(0, weight=1)

            values = row_renderer(row, idx) if row_renderer else row

            for i, val in enumerate(values):
                text, color, is_bold = val if isinstance(val, tuple) else (val, PALETTE["text"], False)

                ctk.CTkLabel(
                    row_frame, text=str(text),
                    font=("Segoe UI", self.fs(13), "bold" if is_bold else "normal"),
                    text_color=color,
                ).grid(row=0, column=i, sticky="nsew", padx=self.s(4))

    def show_scores(self):
        self.clear()
        self.container.configure(fg_color="transparent")

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.place(relx=0.5, rely=0.06, anchor="center")

        ctk.CTkLabel(header, text="🏆",
                     font=("Segoe UI Emoji", self.fs(34))).pack(side="left", padx=self.s(10))
        self._title_label(header, "Таблица результатов", 30).pack(side="left")

        tab = ctk.CTkTabview(
            self.container,
            width=int(self.W * 0.92),
            height=int(self.H * 0.76),
            fg_color=PALETTE["surface"],
            segmented_button_fg_color=PALETTE["surface_alt"],
            segmented_button_selected_color=PALETTE["scores"],
            segmented_button_selected_hover_color=PALETTE["scores_dark"],
            segmented_button_unselected_color=PALETTE["surface_alt"],
            segmented_button_unselected_hover_color=PALETTE["surface_hover"],
            text_color=PALETTE["text"],
            border_width=self.s(2),
            border_color=PALETTE["border"],
            corner_radius=self.s(16),
        )
        tab.place(relx=0.5, rely=0.53, anchor="center")

        tab_games = [("Общий", None, "accent")]
        for g in GAMES:
            if g["key"] == "gta2":
                continue
            tab_games.append((g["name"], g["key"], g["color"]))

        columns = [
            ("Место", 1),
            ("Игрок", 4),
            ("Игра", 3),
            ("Счёт", 2),
            ("Дата", 4),
        ]

        for label, key, color_key in tab_games:
            page = tab.add(label)
            rows = get_top_scores(key, limit=30)

            def renderer(row, idx, ck=color_key):
                username, game_name, score, played_at = row
                try:
                    dt = datetime.fromisoformat(played_at).strftime("%d.%m.%Y %H:%M")
                except ValueError:
                    dt = played_at

                if idx == 0:
                    place = "🥇"
                elif idx == 1:
                    place = "🥈"
                elif idx == 2:
                    place = "🥉"
                else:
                    place = f"#{idx + 1}"

                return [
                    (place, PALETTE["white"], True),
                    (username, PALETTE["text"], False),
                    (game_name, PALETTE.get(ck, PALETTE["accent"]), True),
                    (str(score), PALETTE["white"], True),
                    (dt, PALETTE["text_dim"], False),
                ]

            self._make_table(page, columns, rows, color_key, renderer)

        self._button(self.container, "⬅  Назад", self.show_menu,
                     width=240, height=46, base="accent").place(
            relx=0.5, rely=0.95, anchor="center"
        )

    def show_gta2_stats(self):
        self.clear()
        self.container.configure(fg_color="transparent")

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.place(relx=0.5, rely=0.06, anchor="center")

        ctk.CTkLabel(header, text="📊",
                     font=("Segoe UI Emoji", self.fs(34))).pack(side="left", padx=self.s(10))
        self._title_label(header, "GTA 2 — статистика", 30).pack(side="left")

        wrapper = ctk.CTkFrame(
            self.container,
            width=int(self.W * 0.92),
            height=int(self.H * 0.76),
            fg_color=PALETTE["surface"],
            border_color=PALETTE["border"],
            border_width=self.s(2),
            corner_radius=self.s(16),
        )
        wrapper.place(relx=0.5, rely=0.53, anchor="center")
        wrapper.pack_propagate(False)

        rows = get_gta2_stats(self.current_user_id, limit=100)

        columns = [
            ("Имя", 3),
            ("Деньги", 3),
            ("Район", 2),
            ("День", 2),
            ("Убийства", 3),
            ("Полиция", 3),
            ("Машины", 3),
            ("Миссии", 3),
            ("Дата", 4),
        ]

        def renderer(row, idx):
            values = list(row)
            try:
                values[-1] = datetime.fromisoformat(values[-1]).strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError):
                pass
            result = []
            for i, v in enumerate(values):
                if i == 0:
                    result.append((v, PALETTE["gta"], True))
                elif i == len(values) - 1:
                    result.append((v, PALETTE["text_dim"], False))
                elif i in (1, 2, 3):
                    result.append((v, PALETTE["accent"], True))
                else:
                    result.append((v, PALETTE["text"], False))
            return result

        self._make_table(wrapper, columns, rows, "stats", renderer)

        self._button(self.container, "⬅  Назад", self.show_menu,
                     width=240, height=46, base="accent").place(
            relx=0.5, rely=0.95, anchor="center"
        )


def main():
    init_db()
    app = ArcadeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
