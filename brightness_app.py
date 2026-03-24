import screen_brightness_control as sbc
import tkinter as tk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw
import threading
import os
import sys
import winshell
import json
from win32com.client import Dispatch
import win32event
import win32api
import winerror

CONFIG_FILE = "brightness_config.json"
SIGNAL_FILE = "app_signal.tmp"

# =================== CONFIG ===================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except:
        pass

config = load_config()
# =================== SINGLE INSTANCE ===================
mutex = win32event.CreateMutex(None, False, "BrightnessAppMutex")

if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    # Gửi tín hiệu cho instance đang chạy
    with open(SIGNAL_FILE, "w") as f:
        f.write("show")
    sys.exit(0)

tray_icon = None 

# =================== BRIGHTNESS FUNCTIONS ===================
def get_monitors():
    try:
        return sbc.list_monitors()
    except:
        return []

def get_brightness(monitor_name):
    try:
        val = sbc.get_brightness(display=monitor_name)
        return val[0] if isinstance(val, list) else val
    except:
        return 50

def set_brightness(monitor_name, idx, value):
    try:
        sbc.set_brightness(int(value), display=monitor_name)
    except Exception as e:
        messagebox.showerror(f"Error monitor {idx+1}", str(e))

# =================== MAIN GUI ===================
root = tk.Tk()
root.title("Brightness App")
root.overrideredirect(True)
root.attributes("-topmost", True)

monitors = get_monitors()
if not monitors:
    tk.Label(root, text="No monitors detected.").pack(padx=10, pady=10)

# Vị trí cửa sổ
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
win_w = 430
win_h = len(monitors) * 115 + 70
root.geometry(f"{win_w}x{win_h}+{screen_w - win_w - 10}+{screen_h - win_h - 100}")
root.resizable(False, False)

sliders = []
refresh_vars = []

def make_monitor_row(monitor_name, idx):
    frame = tk.Frame(root)
    frame.pack(fill='x', padx=10, pady=6)

    tk.Label(frame, text=f"Monitor {idx+1}: {monitor_name}", font=("Arial", 10, "bold")).pack(anchor='w')

    slider = tk.Scale(frame, from_=0, to=100, orient=tk.HORIZONTAL,
                      command=lambda v, m=monitor_name, i=idx: set_brightness(m, i, v),
                      length=360, sliderlength=12, cursor='hand2', width=10)
    slider.pack(fill='x', pady=2)

    # Load giá trị ban đầu
    current = get_brightness(monitor_name)
    saved = config.get(f"brightness_{idx}")

    if not config.get(f"refresh_{idx}", True) and current == 0 and saved is not None:
        slider.set(saved)
    else:
        slider.set(current)

    sliders.append(slider)

    # Checkbox
    var = tk.BooleanVar(value=config.get(f"refresh_{idx}", True))
    refresh_vars.append(var)
    var.trace("w", lambda *args: save_all_config())

    tk.Checkbutton(frame, text="Always Refresh", variable=var, font=("Arial", 9)).pack(anchor='w')

for idx, mon in enumerate(monitors):
    make_monitor_row(mon, idx)

# =================== SAVE CONFIG ===================
tray_var = tk.BooleanVar(value=config.get("minimize_to_tray", True))   # dùng cho nút X
auto_minimize_var = tk.BooleanVar(value=config.get("auto_minimize", True))  # click ra ngoài
startup_var = tk.BooleanVar(value=config.get("run_on_startup", False))
start_minimized_var = tk.BooleanVar(value=config.get("start_minimized", False))

def save_all_config():
    cfg = {}
    for i, var in enumerate(refresh_vars):
        refresh = var.get()
        cfg[f"refresh_{i}"] = refresh
        if not refresh:
            cfg[f"brightness_{i}"] = sliders[i].get()

    cfg["minimize_to_tray"] = tray_var.get()
    cfg["auto_minimize"] = auto_minimize_var.get()
    cfg["start_minimized"] = start_minimized_var.get()
    cfg["run_on_startup"] = startup_var.get()

    save_config(cfg)
    global config
    config = cfg.copy()          # Cập nhật config trong RAM

# =================== MENU & BUTTONS ===================
menu_frame = tk.Frame(root)
menu_frame.pack(fill='x', padx=8, pady=4)

menu_btn = tk.Menubutton(menu_frame, text="⚙", bg="#b10eb6", fg="white",
                         relief=tk.RAISED, font=("Arial", 12))
menu_btn.pack(side='right', padx=4)

menu = tk.Menu(menu_btn, tearoff=0)
menu_btn.config(menu=menu)
menu.add_checkbutton(label="Minimize to tray on close", variable=tray_var, command=save_all_config)
menu.add_checkbutton(
    label="Auto minimize when losing focus",
    variable=auto_minimize_var,
    command=save_all_config
)
menu.add_checkbutton(label="Run on Windows startup", variable=startup_var,
                     command=lambda: (toggle_startup(startup_var.get()), save_all_config()))
menu.add_checkbutton(
    label="Start minimized",
    variable=start_minimized_var,
    command=save_all_config
)

def on_close():
    save_all_config()
    if tray_var.get():
        minimize_to_tray_func()
    else:
        root.destroy()

tk.Button(menu_frame, text="Exit", width=5, bg="#ff4444", fg="white",
          font=("Arial", 9, "bold"), command = on_close).pack(side='right', padx=4)

# =================== STARTUP ===================
def toggle_startup(enabled: bool):
    try:
        startup = winshell.startup()
        sc_path = os.path.join(startup, "BrightnessApp.lnk")
        shell = Dispatch('WScript.Shell')
        if enabled:
            sc = shell.CreateShortCut(sc_path)
            sc.Targetpath = sys.executable
            sc.WorkingDirectory = os.getcwd()
            sc.IconLocation = sys.executable
            sc.save()
        else:
            if os.path.exists(sc_path):
                os.remove(sc_path)
    except:
        pass

# =================== SYSTEM TRAY ===================
def create_image():
    img = Image.new('RGB', (64, 64), color='#1e90ff')
    draw = ImageDraw.Draw(img)
    draw.text((18, 12), "☀", fill="white", size=38)
    return img

def show_window(icon=None, item=None):
    global tray_icon

    if tray_icon:
        tray_icon.stop()
        tray_icon = None

    def refresh_and_show():
        for i, var in enumerate(refresh_vars):
            if i >= len(sliders):
                continue
            if var.get():
                sliders[i].set(get_brightness(monitors[i]))

        root.deiconify()
        root.lift()
        root.focus_force()

    root.after(0, refresh_and_show)

def create_tray_if_not_exists():
    global tray_icon
    if tray_icon:
        return  # đã có rồi thì thôi

    tray_icon = pystray.Icon(
        "brightness_app",
        create_image(),
        "Brightness App",
        menu=pystray.Menu(
            pystray.MenuItem("Open", show_window, default=True),
            pystray.MenuItem("Exit", on_exit)
        )
    )
    threading.Thread(target=tray_icon.run, daemon=True).start()

def minimize_to_tray_func():
    save_all_config()
    root.withdraw()
    create_tray_if_not_exists()

def on_exit(icon=None, item=None):
    if icon:
        icon.stop()
    root.destroy()

def check_focus_and_hide():
    if not root.focus_displayof():
        root.withdraw()
        create_tray_if_not_exists()

# =================== Ẩn khi click ra ngoài ===================
def minimize_on_focus_out(event):
    # Không auto minimize nếu user không bật
    if not auto_minimize_var.get():
        return
    root.after(150, check_focus_and_hide)


# Bind sự kiện mất focus
root.bind("<FocusOut>", minimize_on_focus_out)

root.protocol("WM_DELETE_WINDOW", on_close)

# =================== Xử lý startup ẩn UI ===================
start_hidden = config.get("start_minimized", False)

if start_hidden:
    minimize_to_tray_func()
else:
    root.deiconify()

def check_signal():
    if os.path.exists(SIGNAL_FILE):
        os.remove(SIGNAL_FILE)
        show_window()
    root.after(500, check_signal)

check_signal()

root.mainloop()