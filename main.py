import tkinter as tk
import tkinter.font as tkFont
import requests

def find_nodes_by_id(obj, ids, found=None):
    """
    Recursively search `obj` (which can be a dict or list)
    for nodes whose 'id' is in `ids`.
    Returns a dict mapping {id_value: node_with_that_id}.
    """
    if found is None:
        found = {}

    if isinstance(obj, dict):
        # If this object has an 'id' that's in our target set, store it
        if obj.get("id") in ids:
            found[obj["id"]] = obj
        
        # Recurse into any children
        for child in obj.get("Children", []):
            find_nodes_by_id(child, ids, found)

    elif isinstance(obj, list):
        # If it's a list, recurse for each item
        for item in obj:
            find_nodes_by_id(item, ids, found)

    return found

class HWOverlay:
    def __init__(self, master):
        self.master = master

        # Remove the window frame
        self.master.overrideredirect(True)

        # Make the window always on top
        self.master.attributes("-topmost", True)

        # Set the entire window to be 50% opaque (0.0 = fully transparent, 1.0 = fully opaque)
        self.master.attributes("-alpha", 0.5)

        # Use a black background
        self.master.configure(bg="black")

        # Position the overlay in the top-right corner
        screen_width = self.master.winfo_screenwidth()
        window_width = 180
        window_height = 60
        x_position = screen_width - window_width - 10
        y_position = 10
        geometry_string = f"{window_width}x{window_height}+{x_position}+{y_position}"
        self.master.geometry(geometry_string)

        # Create a frame (so we can arrange labels side by side)
        self.frame = tk.Frame(self.master, bg="black")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Define the Outfit font (must be installed system-wide)
        self.outfit_bold = tkFont.Font(family="Outfit", size=10, weight="bold")

        # Create labels for CPU and GPU (side by side)
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

        # The URL to fetch data from
        self.url = "http://localhost:8085/data.json"

        # The IDs we are interested in
        self.target_ids = {19, 61}

        # Start updating
        self.update_data()

    def update_data(self):
        """
        Fetch the data from the JSON endpoint, parse the CPU/GPU values,
        and update the overlay labels.
        Then schedule this to run again after 5 seconds.
        """
        try:
            response = requests.get(self.url, timeout=5)
            data = response.json()

            results = find_nodes_by_id(data, self.target_ids)
            cpu = results.get(19, {})
            gpu = results.get(61, {})

            cpu_temp = cpu.get("Value", "N/A")
            gpu_temp = gpu.get("Value", "N/A")

            # Update labels (side by side)
            self.cpu_label.config(text=f"CPU: {cpu_temp}")
            self.gpu_label.config(text=f"GPU: {gpu_temp}")

        except requests.exceptions.RequestException as e:
            # If there's a network issue, show an error
            self.cpu_label.config(text="CPU: Error")
            self.gpu_label.config(text="GPU: Error")

        # Schedule the next update in 5000 ms (5 seconds)
        self.master.after(2500, self.update_data)

def main():
    root = tk.Tk()
    app = HWOverlay(root)
    root.mainloop()

if __name__ == "__main__":
    main()
