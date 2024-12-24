import tkinter as tk
import tkinter.font as tkFont
import requests
import threading
import sys
import os
from PIL import Image
import pystray
import ctypes
import subprocess
import psutil
import atexit
import logging
import signal

logging.basicConfig(
    filename=os.path.join(os.getcwd(), "SimpleHWMonitor.log"),
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(message)s'
)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_another_instance_running():
    lock_file = os.path.join(os.getcwd(), "SimpleHWMonitor.lock")
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                pid = int(f.read())
            if psutil.pid_exists(pid):
                return True
            else:
                os.remove(lock_file)
                return False
        except:
            return False
    else:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        return False

if is_another_instance_running():
    print("Another instance of SimpleHWMonitor is already running.")
    sys.exit(0)

def run_as_admin(exe_path, working_dir):
    try:
        SW_SHOW = 1
        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        class SHELLEXECUTEINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("fMask", ctypes.c_ulong),
                ("hwnd", ctypes.c_void_p),
                ("lpVerb", ctypes.c_wchar_p),
                ("lpFile", ctypes.c_wchar_p),
                ("lpParameters", ctypes.c_wchar_p),
                ("lpDirectory", ctypes.c_wchar_p),
                ("nShow", ctypes.c_int),
                ("hInstApp", ctypes.c_void_p),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", ctypes.c_wchar_p),
                ("hkeyClass", ctypes.c_void_p),
                ("dwHotKey", ctypes.c_ulong),
                ("hIcon", ctypes.c_void_p),
                ("hProcess", ctypes.c_void_p),
            ]
        execute_info = SHELLEXECUTEINFO()
        execute_info.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
        execute_info.fMask = SEE_MASK_NOCLOSEPROCESS
        execute_info.hwnd = None
        execute_info.lpVerb = "runas"
        execute_info.lpFile = exe_path
        execute_info.lpParameters = None
        execute_info.lpDirectory = working_dir
        execute_info.nShow = SW_SHOW
        execute_info.hInstApp = None
        if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(execute_info)):
            raise ctypes.WinError()
        pid = ctypes.windll.kernel32.GetProcessId(execute_info.hProcess)
        logging.info(f"Launched {exe_path} with PID {pid}")
        return pid
    except Exception as e:
        logging.error(f"Failed to launch {exe_path} as admin: {e}")
        sys.exit(1)

def terminate_process(pid):
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)
        logging.info(f"Terminated process with PID {pid}")
    except psutil.NoSuchProcess:
        logging.warning(f"No process found with PID {pid}")
    except psutil.TimeoutExpired:
        proc.kill()
        logging.info(f"Killed process with PID {pid} after timeout")
    except Exception as e:
        logging.error(f"Error terminating process {pid}: {e}")

def load_custom_font():
        FR_PRIVATE = 0x10
        font_path = resource_path("Outfit-Bold.ttf")
        ctypes.windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
        return tkFont.Font(family="Outfit Bold", size=10)

class HWOverlay:
    def __init__(self, master):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.master.overrideredirect(True)
        self.master.attributes("-topmost", True)
        self.master.attributes("-alpha", 0.5)
        self.master.configure(bg="black")
        screen_width = self.master.winfo_screenwidth()
        window_width = 180
        window_height = 60
        x_position = screen_width - window_width - 10
        y_position = 10
        geometry_string = f"{window_width}x{window_height}+{x_position}+{y_position}"
        self.master.geometry(geometry_string)
        self.frame = tk.Frame(self.master, bg="black")
        self.frame.pack(fill=tk.BOTH, expand=True)
        # font_path = resource_path("Outfit-Bold.ttf")
        # self.outfit_bold = tkFont.Font(file=font_path, size=10, weight="bold")
        self.outfit_bold = load_custom_font()
        self.cpu_label = tk.Label(
            self.frame,
            text="CPU: ...",
            font=self.outfit_bold,
            fg="white",
            bg="black"
        )
        self.cpu_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.gpu_label = tk.Label(
            self.frame,
            text="GPU: ...",
            font=self.outfit_bold,
            fg="white",
            bg="black"
        )
        self.gpu_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.url = "http://localhost:8085/data.json"
        self.target_ids = {19, 61}
        self.ohm_pid = self.start_openhardwaremonitor()
        atexit.register(self.cleanup)
        self.update_data()

    def start_openhardwaremonitor(self):
        ohm_path = resource_path("OpenHardwareMonitor/OpenHardwareMonitor.exe")
        working_dir = resource_path("OpenHardwareMonitor")
        if not os.path.exists(ohm_path):
            logging.error(f"OpenHardwareMonitor.exe not found at {ohm_path}")
            sys.exit(1)
        pid = run_as_admin(ohm_path, working_dir)
        return pid

    def update_data(self):
        try:
            response = requests.get(self.url, timeout=5)
            data = response.json()
            results = find_nodes_by_id(data, self.target_ids)
            cpu = results.get(19, {})
            gpu = results.get(61, {})
            cpu_temp = cpu.get("Value", "N/A")
            gpu_temp = gpu.get("Value", "N/A")
            self.cpu_label.config(text=f"CPU: {cpu_temp}")
            self.gpu_label.config(text=f"GPU: {gpu_temp}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data: {e}")
            self.cpu_label.config(text="CPU: Error")
            self.gpu_label.config(text="GPU: Error")
        self.master.after(2500, self.update_data)

    def hide_window(self):
        self.master.withdraw()
        if self.icon:
            self.icon.update_menu()

    def show_window(self):
        self.master.deiconify()
        if self.icon:
            self.icon.update_menu()

    def set_tray_icon(self, icon):
        self.icon = icon

    def cleanup(self):
        logging.info("Cleaning up: Terminating OpenHardwareMonitor.exe")
        terminate_process(self.ohm_pid)
        lock_file = os.path.join(os.getcwd(), "SimpleHWMonitor.lock")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                logging.info("Removed lock file.")
            except Exception as e:
                logging.error(f"Failed to remove lock file: {e}")

def find_nodes_by_id(obj, ids, found=None):
    if found is None:
        found = {}
    if isinstance(obj, dict):
        if obj.get("id") in ids:
            found[obj["id"]] = obj
        for child in obj.get("Children", []):
            find_nodes_by_id(child, ids, found)
    elif isinstance(obj, list):
        for item in obj:
            find_nodes_by_id(item, ids, found)
    return found

def create_celsius_icon():
    try:
        icon_path = resource_path("icon.ico")
        return Image.open(icon_path)
    except Exception as e:
        # logging.error(f"Failed to load icon.ico: {e}")
        # sys.exit(1)
        size = (64, 64)  # Define the size of the icon
        white_square = Image.new('RGB', size, 'white')  # Create a white square
        return white_square

def start_tray(app):
    icon = pystray.Icon("HWOverlay")
    icon.icon = create_celsius_icon()
    icon.title = "HW Monitor Overlay"

    def toggle_overlay(icon, item):
        if app.master.state() == 'withdrawn':
            app.show_window()
        else:
            app.hide_window()
        icon.menu = get_menu()

    def exit_app(icon, item):
        logging.info("Exiting application via system tray.")
        icon.stop()
        app.master.destroy()
        sys.exit(0)

    def get_menu():
        if app.master.state() == 'withdrawn':
            toggle_text = "Show"
        else:
            toggle_text = "Hide"
        return pystray.Menu(
            pystray.MenuItem(toggle_text, toggle_overlay),
            pystray.MenuItem("Exit", exit_app)
        )

    icon.menu = get_menu()
    app.set_tray_icon(icon)
    icon.run()

def signal_handler(sig, frame):
    logging.info(f"Received signal {sig}, exiting application.")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    root = tk.Tk()
    app = HWOverlay(root)
    tray_thread = threading.Thread(target=start_tray, args=(app,), daemon=True)
    tray_thread.start()
    root.mainloop()

if __name__ == "__main__":
    main()
