import tkinter as tk
import tkinter.font as tkFont
import requests
import threading
import sys
import os
from PIL import Image, ImageDraw, ImageFont
import pystray

def find_nodes_by_id(obj, ids, found=None):
    """
    Recursively search `obj` (which can be a dict or list)
    for nodes whose 'id' is in `ids`.
    Returns a dict mapping {id_value: node_with_that_id}.
    """
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

        self.outfit_bold = tkFont.Font(family="Outfit", size=10, weight="bold")

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

        self.update_data()

    def update_data(self):
        """
        Fetch the data from the JSON endpoint, parse the CPU/GPU values,
        and update the overlay labels.
        Then schedule this to run again after 2.5 seconds.
        """
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

def create_celsius_icon():
    """
    Creates a simple '°C' icon for the system tray using Pillow.
    """
    return Image.open("icon.ico")

def start_tray(app):
    """
    Initializes and runs the system tray icon.
    """
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
        icon.stop()
        app.master.destroy()
        sys.exit()

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

def exit_app(icon, app):
    """
    Exits the application gracefully.
    """
    icon.stop()
    app.master.destroy()
    sys.exit()

def main():
    root = tk.Tk()
    app = HWOverlay(root)

    tray_thread = threading.Thread(target=start_tray, args=(app,), daemon=True)
    tray_thread.start()

    root.mainloop()

if __name__ == "__main__":
        main()
