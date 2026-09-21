import sys
import subprocess

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

install_and_import('customtkinter')

import os
import customtkinter as ctk

def close_app(event=None):
    root.destroy()

def open_snake():
    os.startfile(r"C:\arcade\src\snake.py")

def open_fb():
    os.startfile(r"C:\arcade\src\flappybird.py")

def open_ttr():
    os.startfile(r"C:\arcade\src\tetris.py")

def open_pm():
    os.startfile(r"C:\arcade\src\pacmen.py")

ctk.set_appearance_mode("dark") 

root = ctk.CTk()
root.attributes('-fullscreen', True)
root.title("Arcade")
root.configure(fg_color="#48a3db")
root.bind('<Escape>', close_app)

main_label = ctk.CTkLabel(root, text="Аркадный Автомат", font=("Segoe UI", 28, "bold"), text_color="white")
main_label.place(x=430, y=280)

button_snake = ctk.CTkButton(root, text="Змейка", command=open_snake, width=220, height=54, corner_radius=15, font=("Segoe UI", 18), fg_color="#1f538d", hover_color="#14375e")
button_snake.place(x=320, y=400)

button_fp = ctk.CTkButton(root, text="Flappy Bird", command=open_fb, width=220, height=54, corner_radius=15, font=("Segoe UI", 18), fg_color="#1f538d", hover_color="#14375e")
button_fp.place(x=560, y=400)

button_tr = ctk.CTkButton(root, text="Tetris", command=open_ttr, width=220, height=54, corner_radius=15, font=("Segoe UI", 18), fg_color="#1f538d", hover_color="#14375e")
button_tr.place(x=320, y=470)

button_pm = ctk.CTkButton(root, text="Pac-Men", command=open_pm, width=220, height=54, corner_radius=15, font=("Segoe UI", 18), fg_color="#1f538d", hover_color="#14375e")
button_pm.place(x=560, y=470)

root.mainloop()
