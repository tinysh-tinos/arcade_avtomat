import sys
import subprocess

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

install_and_import('customtkinter')
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

from gta2_reader import get_stats_if_changed, latest_save


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "arcade.db")
SRC_DIR = os.path.join(BASE_DIR, "src")


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
        user_id = c.lastrowid
        conn.close()
        return user_id
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
            FROM scores s
            JOIN users u ON u.id = s.user_id
            WHERE s.game = ?
            ORDER BY s.score DESC
            LIMIT ?
        """, (game, limit))
    else:
        c.execute("""
            SELECT u.username, s.game, s.score, s.played_at
            FROM scores s
            JOIN users u ON u.id = s.user_id
            ORDER BY s.score DESC
            LIMIT ?
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
        WHERE user_id = ?
        ORDER BY played_at DESC LIMIT 1
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
                print(f"[GTA2] импортирована статистика: {stats['file']}")
        except Exception as e:
            print(f"[GTA2] ошибка чтения сейва: {e}")


class ArcadeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.current_user_id = None
        self.current_username = None
        self.watcher = None

        ctk.set_appearance_mode("dark")
        self.attributes("-fullscreen", True)
        self.title("Arcade")
        self.configure(fg_color="#48a3db")
        self.bind("<Escape>", self.on_escape)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.show_login()

    def on_escape(self, event=None):
        self.destroy()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def show_login(self):
        self.clear()
        self.container.configure(fg_color="#48a3db")

        title = ctk.CTkLabel(self.container, text="Аркадный Автомат",
                             font=("Segoe UI", 40, "bold"), text_color="white")
        title.place(relx=0.5, rely=0.18, anchor="center")

        sub = ctk.CTkLabel(self.container, text="Вход в аккаунт",
                           font=("Segoe UI", 22), text_color="white")
        sub.place(relx=0.5, rely=0.28, anchor="center")

        self.login_entry = ctk.CTkEntry(self.container, width=320, height=48,
                                        placeholder_text="Логин", font=("Segoe UI", 16))
        self.login_entry.place(relx=0.5, rely=0.40, anchor="center")

        self.pass_entry = ctk.CTkEntry(self.container, width=320, height=48,
                                       placeholder_text="Пароль", show="*",
                                       font=("Segoe UI", 16))
        self.pass_entry.place(relx=0.5, rely=0.49, anchor="center")

        btn_login = ctk.CTkButton(self.container, text="Войти", command=self.do_login,
                                  width=320, height=54, corner_radius=15,
                                  font=("Segoe UI", 18, "bold"),
                                  fg_color="#1f538d", hover_color="#14375e")
        btn_login.place(relx=0.5, rely=0.60, anchor="center")

        btn_register = ctk.CTkButton(self.container, text="Регистрация",
                                     command=self.show_register,
                                     width=320, height=54, corner_radius=15,
                                     font=("Segoe UI", 18),
                                     fg_color="#2f6f2f", hover_color="#1f4f1f")
        btn_register.place(relx=0.5, rely=0.69, anchor="center")

        btn_exit = ctk.CTkButton(self.container, text="Выход", command=self.destroy,
                                 width=320, height=44, corner_radius=15,
                                 font=("Segoe UI", 16),
                                 fg_color="#7a1f1f", hover_color="#5a1010")
        btn_exit.place(relx=0.5, rely=0.78, anchor="center")

        self.pass_entry.bind("<Return>", lambda e: self.do_login())

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
        self.container.configure(fg_color="#48a3db")

        title = ctk.CTkLabel(self.container, text="Регистрация",
                             font=("Segoe UI", 36, "bold"), text_color="white")
        title.place(relx=0.5, rely=0.20, anchor="center")

        self.reg_login = ctk.CTkEntry(self.container, width=320, height=48,
                                      placeholder_text="Логин", font=("Segoe UI", 16))
        self.reg_login.place(relx=0.5, rely=0.35, anchor="center")

        self.reg_pass = ctk.CTkEntry(self.container, width=320, height=48,
                                     placeholder_text="Пароль", show="*",
                                     font=("Segoe UI", 16))
        self.reg_pass.place(relx=0.5, rely=0.44, anchor="center")

        self.reg_pass2 = ctk.CTkEntry(self.container, width=320, height=48,
                                      placeholder_text="Повтор пароля", show="*",
                                      font=("Segoe UI", 16))
        self.reg_pass2.place(relx=0.5, rely=0.53, anchor="center")

        btn_create = ctk.CTkButton(self.container, text="Создать",
                                   command=self.do_register,
                                   width=320, height=54, corner_radius=15,
                                   font=("Segoe UI", 18, "bold"),
                                   fg_color="#2f6f2f", hover_color="#1f4f1f")
        btn_create.place(relx=0.5, rely=0.65, anchor="center")

        btn_back = ctk.CTkButton(self.container, text="Назад", command=self.show_login,
                                 width=320, height=44, corner_radius=15,
                                 font=("Segoe UI", 16),
                                 fg_color="#1f538d", hover_color="#14375e")
        btn_back.place(relx=0.5, rely=0.75, anchor="center")

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
        self.container.configure(fg_color="#48a3db")

        top = ctk.CTkFrame(self.container, fg_color="transparent")
        top.place(relx=0.5, rely=0.08, anchor="center")

        title = ctk.CTkLabel(top, text="Аркадный Автомат",
                             font=("Segoe UI", 40, "bold"), text_color="white")
        title.pack()

        user_label = ctk.CTkLabel(top, text=f"Игрок: {self.current_username}",
                                  font=("Segoe UI", 20), text_color="white")
        user_label.pack(pady=(10, 0))

        btn_snake = ctk.CTkButton(self.container, text="Змейка",
                                  command=lambda: self.launch_game("snake"),
                                  width=220, height=54, corner_radius=15,
                                  font=("Segoe UI", 18),
                                  fg_color="#1f538d", hover_color="#14375e")
        btn_snake.place(relx=0.42, rely=0.42, anchor="center")

        btn_fb = ctk.CTkButton(self.container, text="Flappy Bird",
                               command=lambda: self.launch_game("flappybird"),
                               width=220, height=54, corner_radius=15,
                               font=("Segoe UI", 18),
                               fg_color="#1f538d", hover_color="#14375e")
        btn_fb.place(relx=0.58, rely=0.42, anchor="center")

        btn_ttr = ctk.CTkButton(self.container, text="Tetris",
                                command=lambda: self.launch_game("tetris"),
                                width=220, height=54, corner_radius=15,
                                font=("Segoe UI", 18),
                                fg_color="#1f538d", hover_color="#14375e")
        btn_ttr.place(relx=0.42, rely=0.52, anchor="center")

        btn_pm = ctk.CTkButton(self.container, text="Pac-Man",
                               command=lambda: self.launch_game("pacmen"),
                               width=220, height=54, corner_radius=15,
                               font=("Segoe UI", 18),
                               fg_color="#1f538d", hover_color="#14375e")
        btn_pm.place(relx=0.58, rely=0.52, anchor="center")

        btn_mc = ctk.CTkButton(self.container, text="Mortal Kombat",
                               command=lambda: self.launch_game("mc"),
                               width=220, height=54, corner_radius=15,
                               font=("Segoe UI", 18),
                               fg_color="#1f538d", hover_color="#14375e")
        btn_mc.place(relx=0.42, rely=0.62, anchor="center")

        btn_gta = ctk.CTkButton(self.container, text="GTA 2",
                                command=self.launch_gta2,
                                width=220, height=54, corner_radius=15,
                                font=("Segoe UI", 18),
                                fg_color="#4a4a4a", hover_color="#333333")
        btn_gta.place(relx=0.58, rely=0.62, anchor="center")

        btn_scores = ctk.CTkButton(self.container, text="Таблица результатов",
                                   command=self.show_scores,
                                   width=220, height=54, corner_radius=15,
                                   font=("Segoe UI", 18),
                                   fg_color="#6f4f1f", hover_color="#4f3a12")
        btn_scores.place(relx=0.42, rely=0.72, anchor="center")

        btn_gta_stats = ctk.CTkButton(self.container, text="GTA 2 — статистика",
                                      command=self.show_gta2_stats,
                                      width=220, height=54, corner_radius=15,
                                      font=("Segoe UI", 18),
                                      fg_color="#6f4f1f", hover_color="#4f3a12")
        btn_gta_stats.place(relx=0.58, rely=0.72, anchor="center")

        btn_logout = ctk.CTkButton(self.container, text="Сменить аккаунт",
                                   command=self.logout,
                                   width=460, height=44, corner_radius=15,
                                   font=("Segoe UI", 16),
                                   fg_color="#7a1f1f", hover_color="#5a1010")
        btn_logout.place(relx=0.5, rely=0.82, anchor="center")

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
        env["ARCADE_USER"] = self.current_username
        env["ARCADE_USER_ID"] = str(self.current_user_id)
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
                if score > 0:
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
            "Игра запущена.\n\nСтатистика будет автоматически "
            "собираться каждую минуту,\nпока GTA 2 открыта."
        )

    def show_scores(self):
        self.clear()
        self.container.configure(fg_color="#48a3db")

        title = ctk.CTkLabel(self.container, text="Таблица результатов",
                             font=("Segoe UI", 34, "bold"), text_color="white")
        title.place(relx=0.5, rely=0.08, anchor="center")

        tab_view = ctk.CTkTabview(self.container,
                                  width=int(self.winfo_screenwidth() * 0.7),
                                  height=int(self.winfo_screenheight() * 0.7),
                                  fg_color="#2a3a4a")
        tab_view.place(relx=0.5, rely=0.55, anchor="center")

        games = [
            ("Общий", None),
            ("Змейка", "snake"),
            ("Flappy Bird", "flappybird"),
            ("Tetris", "tetris"),
            ("Pac-Man", "pacmen"),
            ("Mortal Kombat", "mc"),
        ]

        for label, key in games:
            tab = tab_view.add(label)
            rows = get_top_scores(key, limit=15)

            header = ctk.CTkFrame(tab, fg_color="#1f538d", corner_radius=8)
            header.pack(fill="x", padx=10, pady=(10, 5))

            ctk.CTkLabel(header, text="Место", width=80,
                         font=("Segoe UI", 16, "bold")).pack(side="left", padx=8, pady=8)
            ctk.CTkLabel(header, text="Игрок", width=200,
                         font=("Segoe UI", 16, "bold")).pack(side="left", padx=8, pady=8)
            ctk.CTkLabel(header, text="Игра", width=180,
                         font=("Segoe UI", 16, "bold")).pack(side="left", padx=8, pady=8)
            ctk.CTkLabel(header, text="Счёт", width=120,
                         font=("Segoe UI", 16, "bold")).pack(side="left", padx=8, pady=8)
            ctk.CTkLabel(header, text="Дата", width=200,
                         font=("Segoe UI", 16, "bold")).pack(side="left", padx=8, pady=8)

            if not rows:
                ctk.CTkLabel(tab, text="Пока нет результатов",
                             font=("Segoe UI", 18)).pack(pady=30)
                continue

            scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=10, pady=5)

            for i, (username, game_name, score, played_at) in enumerate(rows, start=1):
                bg = "#34495e" if i % 2 == 0 else "#2c3e50"
                row_frame = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=6)
                row_frame.pack(fill="x", pady=2)

                try:
                    dt = datetime.fromisoformat(played_at).strftime("%d.%m.%Y %H:%M")
                except ValueError:
                    dt = played_at

                ctk.CTkLabel(row_frame, text=str(i), width=80,
                             font=("Segoe UI", 15)).pack(side="left", padx=8, pady=6)
                ctk.CTkLabel(row_frame, text=username, width=200,
                             font=("Segoe UI", 15)).pack(side="left", padx=8, pady=6)
                ctk.CTkLabel(row_frame, text=game_name, width=180,
                             font=("Segoe UI", 15)).pack(side="left", padx=8, pady=6)
                ctk.CTkLabel(row_frame, text=str(score), width=120,
                             font=("Segoe UI", 15, "bold")).pack(side="left", padx=8, pady=6)
                ctk.CTkLabel(row_frame, text=dt, width=200,
                             font=("Segoe UI", 15)).pack(side="left", padx=8, pady=6)

        btn_back = ctk.CTkButton(self.container, text="Назад", command=self.show_menu,
                                 width=220, height=48, corner_radius=15,
                                 font=("Segoe UI", 18),
                                 fg_color="#1f538d", hover_color="#14375e")
        btn_back.place(relx=0.5, rely=0.94, anchor="center")

    def show_gta2_stats(self):
        self.clear()
        self.container.configure(fg_color="#48a3db")

        title = ctk.CTkLabel(self.container, text="GTA 2 — статистика",
                             font=("Segoe UI", 34, "bold"), text_color="white")
        title.place(relx=0.5, rely=0.08, anchor="center")

        rows = get_gta2_stats(self.current_user_id, limit=50)

        scroll = ctk.CTkScrollableFrame(
            self.container,
            width=int(self.winfo_screenwidth() * 0.85),
            height=int(self.winfo_screenheight() * 0.65),
            fg_color="#2a3a4a"
        )
        scroll.place(relx=0.5, rely=0.55, anchor="center")

        headers = ["Имя", "Деньги", "Район", "День",
                   "Убийства", "Полиция", "Машины", "Миссии", "Дата"]
        header = ctk.CTkFrame(scroll, fg_color="#1f538d", corner_radius=8)
        header.pack(fill="x", pady=(0, 4))
        for h in headers:
            ctk.CTkLabel(header, text=h, width=130,
                         font=("Segoe UI", 15, "bold")).pack(side="left", padx=4, pady=6)

        if not rows:
            ctk.CTkLabel(scroll, text="Пока нет данных GTA 2",
                         font=("Segoe UI", 18)).pack(pady=30)

        for i, row in enumerate(rows):
            bg = "#34495e" if i % 2 == 0 else "#2c3e50"
            rf = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=6)
            rf.pack(fill="x", pady=1)
            for val in row:
                ctk.CTkLabel(rf, text=str(val), width=130,
                             font=("Segoe UI", 14)).pack(side="left", padx=4, pady=5)

        btn_back = ctk.CTkButton(self.container, text="Назад", command=self.show_menu,
                                 width=220, height=48, corner_radius=15,
                                 font=("Segoe UI", 18),
                                 fg_color="#1f538d", hover_color="#14375e")
        btn_back.place(relx=0.5, rely=0.94, anchor="center")


def main():
    init_db()
    app = ArcadeApp()
    app.mainloop()


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
