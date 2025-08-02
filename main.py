import random
import time
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import threading
from telemetry_logger import log_data
from telemetry.sensors import get_engine_temp, get_fuel_level, get_battery_voltage

# set global dark theme for matplotlib
plt.style.use("dark_background")

def generate_rpm():
    return random.randint(700, 3000)    # returns a random RPM value between 700 and 3000

def generate_speed():
    return random.randint(0, 120)   # returns a random speed value between 0 and 120 km/h

class ECUSimulator:
    def __init__(self, root):
        # initialize the ECU simulator GUI and state variables
        self.root = root
        self.root.title("Vehicle Telemetry System")
        self.last_graph_time = time.time()
        self.last_log_time = time.time()
        self.root.configure(bg="#1e1e1e")

        self.running = True
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.counter = 0

        self.rpm = 800
        self.speed = 0
        self.accelerating = False
        self.braking = False

        # data lists for plotting
        self.rpm_data = []
        self.speed_data = []
        self.time_data = []

        # time tracking for graph and logging
        self.start_time = time.time()
        self.last_graph_time = time.time()

        # control buttons
        btn_frame = tk.Frame(self.root, bg="#1e1e1e")
        btn_frame.pack()

        btn_frame = tk.Frame(self.root, pady=10, bg="#1e1e1e")
        btn_frame.pack()

        self.accelerate_btn = tk.Button(
            btn_frame,
            text="Accelerate",
            width=15,
            font=("Helvetica", 14, "bold"),
            bg="#2e7d32",
            fg="black",
            activebackground="#388e3c",
            relief=tk.RAISED,
            command=self.toggle_acceleration
        )
        self.accelerate_btn.pack(side=tk.LEFT, padx=20)

        self.brake_btn = tk.Button(
            btn_frame,
            text="Brake",
            width=15,
            font=("Helvetica", 14, "bold"),
            bg="#c62828",
            fg="black",
            activebackground="#e53935",
            relief=tk.RAISED,
            command=self.toggle_brake
        )
        self.brake_btn.pack(side=tk.LEFT, padx=20)

        # initialize matplotlib graphs
        self.fig, (self.ax_rpm, self.ax_speed) = plt.subplots(2, 1, figsize=(6, 5))
        self.fig.patch.set_facecolor("#121212")

        self.ax_rpm.set_facecolor("#1e1e1e")
        self.ax_speed.set_facecolor("#1e1e1e")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack()

        # start background thread to update telemetry
        self.update_thread = threading.Thread(target=self.update_data)
        self.update_thread.daemon = True
        self.update_thread.start()

    def toggle_acceleration(self):
        # toggle the acceleration state and update button UI
        self.accelerating = not self.accelerating
        if self.accelerating:
            self.accelerate_btn.config(relief=tk.SUNKEN, text="Accelerating")
        else:
            self.accelerate_btn.config(relief=tk.RAISED, text="Accelerate")

    def toggle_brake(self):
        # toggle the braking state and update button UI
        self.braking = not self.braking
        if self.braking:
            self.brake_btn.config(relief=tk.SUNKEN, text="Braking")
        else:
            self.brake_btn.config(relief=tk.RAISED, text="Brake")

    def update_data(self):
        # continuously update telemetry and refresh plots
        while self.running:
            # time since start
            current_time = time.time() - self.start_time

            # physics simulation: acceleration, braking and coasting
            if self.accelerating:
                self.speed = min(self.speed + 5, 250)
                self.rpm = min(self.rpm + 200, 6000)
            elif self.braking:
                self.speed = max(self.speed - 5, 0)
                self.rpm = max(self.rpm - 300, 800)
            else:
                if self.speed > 0:
                    self.speed = max(self.speed - 1, 0)
                self.rpm = max(self.rpm - 100, 800)

            # append data for plotting
            self.time_data.append(round(current_time, 1))
            self.rpm_data.append(self.rpm)
            self.speed_data.append(self.speed)

            # limit to last 20 data points
            self.time_data = self.time_data[-20:]
            self.rpm_data = self.rpm_data[-20:]
            self.speed_data = self.speed_data[-20:]

            # update matplotlib plots
            self.ax_rpm.clear()
            self.ax_speed.clear()

            self.ax_rpm.plot(self.time_data, self.rpm_data, label="RPM", color="red")
            self.ax_speed.plot(self.time_data, self.speed_data, label="Speed", color="blue")

            self.ax_rpm.set_ylabel("RPM")
            self.ax_speed.set_ylabel("Speed (km/h)")
            self.ax_speed.set_xlabel("Time (s)")

            self.ax_rpm.legend()
            self.ax_speed.legend()
            self.canvas.draw()

            # log telemetry every 2 seconds
            if time.time() - self.last_log_time >= 2.0:
                temp = get_engine_temp()
                fuel = get_fuel_level()
                volt = get_battery_voltage()
                log_data(self.rpm, self.speed, temp, fuel, volt)
                self.last_log_time = time.time()

            time.sleep(0.1)

    def on_closing(self):
        # stop background thread and close the GUI
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ECUSimulator(root)
    root.mainloop()