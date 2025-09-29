from __future__ import annotations

import csv
import time
import math
import os
import queue
import threading
from typing import Deque, Dict, Optional, Tuple
from collections import deque
from datetime import datetime
from dataclasses import dataclass, field

import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


TelemetryLogger = None
Sensors = None
try:  # use if available
    from telemetry_logger import TelemetryLogger as _TL
    TelemetryLogger = _TL
except Exception:
    TelemetryLogger = None

try:
    # Expecting something like: class Sensors: get_coolant_temp(), get_fuel_level(), get_battery_voltage()
    from telemetry.sensors import Sensors as _Sensors
    Sensors = _Sensors
except Exception:
    Sensors = None

# constants
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "telemetry_log.csv")
LOG_INTERVAL_S = 2.0  # keep parity with README

# domain model
@dataclass
class VehicleState:
    t: float = 0.0           # seconds since start
    speed_kph: float = 0.0
    rpm: float = 800.0
    throttle: float = 0.0    # 0..1
    brake: float = 0.0       # 0..1
    gear: int = 1
    engine_on: bool = True
    coolant_temp_c: float = 70.0
    fuel_level_pct: float = 80.0
    battery_v: float = 12.5


class VehicleModel:
    def __init__(self) -> None:
        self.state = VehicleState()
        # Tunables
        self.max_accel = 3.5       # m/s^2 at full throttle
        self.max_brake = 7.0       # m/s^2
        self.drag_coeff = 0.015    # proportional to speed (m/s)
        self.idle_rpm = 800.0
        self.redline_rpm = 6500.0
        self.wheel_radius_m = 0.31
        self.final_drive = 3.42
        self.gear_ratios = {1: 3.8, 2: 2.2, 3: 1.5, 4: 1.0, 5: 0.8, 6: 0.68}
        self.mass_kg = 1500.0
        self.shift_up_rpm = 3000.0
        self.shift_down_rpm = 1100.0

        # Optional sensors instance
        self.sensors = Sensors() if Sensors else None

    def update(self, dt: float) -> None:
        s = self.state
        if not s.engine_on:
            s.throttle = 0.0

        # Convert speed to m/s for physics
        v_ms = s.speed_kph / 3.6

        # Forces
        a_throttle = s.throttle * self.max_accel
        a_brake = s.brake * self.max_brake
        a_drag = self.drag_coeff * v_ms
        a_net = a_throttle - a_brake - a_drag

        # Integrate speed
        v_ms = max(0.0, v_ms + a_net * dt)
        s.speed_kph = v_ms * 3.6

        # Engine RPM via wheel speed & gearing; idle when nearly stopped
        gear_ratio = self.gear_ratios.get(s.gear, 1.0)
        if v_ms < 0.1:
            s.rpm = self.idle_rpm if s.engine_on else 0.0
        else:
            wheel_rps = v_ms / (2 * math.pi * self.wheel_radius_m)
            engine_rpm = wheel_rps * 60 * self.final_drive * gear_ratio
            s.rpm = max(self.idle_rpm if s.engine_on else 0.0, min(engine_rpm, self.redline_rpm))

        # Auto shift (toy)
        if s.engine_on and s.rpm > self.shift_up_rpm and s.gear < max(self.gear_ratios):
            s.gear += 1
        elif s.engine_on and s.rpm < self.shift_down_rpm and s.gear > 1:
            s.gear -= 1

        # Sensor updates (coolant/fuel/battery)
        if self.sensors:
            try:
                s.coolant_temp_c = self.sensors.get_coolant_temp(s.coolant_temp_c, s.engine_on, dt)
                s.fuel_level_pct = self.sensors.get_fuel_level(s.fuel_level_pct, s.throttle, dt)
                s.battery_v = self.sensors.get_battery_voltage(s.battery_v, s.engine_on, dt)
            except Exception:
                self._fallback_sensors(dt)
        else:
            self._fallback_sensors(dt)

        s.t += dt

    def _fallback_sensors(self, dt: float) -> None:
        s = self.state
        # Warm to ~92°C when on, cool toward 20°C when off
        target = 92.0 if s.engine_on else 20.0
        s.coolant_temp_c += (target - s.coolant_temp_c) * min(1.0, dt * 0.02)
        # Crude fuel burn
        s.fuel_level_pct = max(0.0, s.fuel_level_pct - (0.00002 + 0.0004 * s.throttle) * dt)
        # Battery hover around 12–14 V
        drift = (0.05 if s.engine_on else -0.02) * dt
        s.battery_v = max(11.5, min(14.2, s.battery_v + drift))

class Simulator(threading.Thread):
    def __init__(self, model: VehicleModel, state_out: queue.Queue, cmd_in: queue.Queue, hz: int = 60):
        super().__init__(daemon=True)
        self.model = model
        self.state_out = state_out
        self.cmd_in = cmd_in
        self.hz = hz
        self.dt = 1.0 / hz
        self._running = threading.Event()
        self._running.set()

    def run(self) -> None:
        last = time.perf_counter()
        accum = 0.0
        while self._running.is_set():
            self._drain_commands()
            now = time.perf_counter()
            accum += now - last
            last = now
            while accum >= self.dt:
                self.model.update(self.dt)
                accum -= self.dt
                # publish latest state (drop if queue full)
                try:
                    self.state_out.put_nowait(self.model.state)
                except queue.Full:
                    try:
                        _ = self.state_out.get_nowait()
                        self.state_out.put_nowait(self.model.state)
                    except queue.Empty:
                        pass
            time.sleep(0.001)

    def _drain_commands(self) -> None:
        try:
            while True:
                cmd, payload = self.cmd_in.get_nowait()
                s = self.model.state
                if cmd == "throttle":
                    s.throttle = float(payload)
                elif cmd == "brake":
                    s.brake = float(payload)
                elif cmd == "engine_on":
                    s.engine_on = bool(payload)
                elif cmd == "gear":
                    s.gear = max(1, min(6, int(payload)))
                elif cmd == "reset":
                    self.model.state = VehicleState()
        except queue.Empty:
            pass

    def stop(self):
        self._running.clear()

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Vehicle Telemetry & Diagnostic System")
        self.geometry("1060x720")
        self.minsize(960, 640)

# queues for thread comms
        self.state_q: queue.Queue[VehicleState] = queue.Queue(maxsize=5)
        self.cmd_q: queue.Queue[Tuple[str, object]] = queue.Queue()

# core
        self.model = VehicleModel()
        self.sim = Simulator(self.model, self.state_q, self.cmd_q)
        self.sim.start()

# logging
        self._csv_writer = None
        self._csv_fp = None
        self._last_log_t = 0.0
        self._telemetry_logger = TelemetryLogger(LOG_PATH) if TelemetryLogger else None

# build UI
        self._build_controls()
        self._build_gauges()
        self._build_plot()
        self._bind_keys()

# plot buffers
        self.buf_len = 600  # ~10s at 60 Hz / sampled ~10 Hz
        self.t_buf: Deque[float] = deque(maxlen=self.buf_len)
        self.speed_buf: Deque[float] = deque(maxlen=self.buf_len)
        self.rpm_buf: Deque[float] = deque(maxlen=self.buf_len)

# UI update loop
        self.sample_interval_ms = 100  # 10 Hz UI refresh
        self.after(self.sample_interval_ms, self._on_timer)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_controls(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(side=tk.TOP, fill=tk.X, padx=12, pady=8)

#engine toggle
        self.engine_btn = ttk.Checkbutton(frm, text="Engine ON", command=self._toggle_engine)
        self.engine_btn.state(["!alternate"])  # no tristate
        self.engine_btn.state(["selected"])  # default on
        self.engine_btn.pack(side=tk.LEFT, padx=(0, 12))

# gear selector
        ttk.Label(frm, text="Gear:").pack(side=tk.LEFT)
        self.gear_var = tk.IntVar(value=1)
        gear_spin = ttk.Spinbox(frm, from_=1, to=6, width=3, textvariable=self.gear_var, command=self._set_gear)
        gear_spin.pack(side=tk.LEFT, padx=(4, 16))

# gas and brake
        self.gas_btn = ttk.Button(frm, text="Gas (Hold)")
        self.gas_btn.bind("<ButtonPress-1>", lambda e: self._set_throttle(1.0))
        self.gas_btn.bind("<ButtonRelease-1>", lambda e: self._set_throttle(0.0))
        self.gas_btn.pack(side=tk.LEFT, padx=6)

        self.brake_btn = ttk.Button(frm, text="Brake (Hold)")
        self.brake_btn.bind("<ButtonPress-1>", lambda e: self._set_brake(1.0))
        self.brake_btn.bind("<ButtonRelease-1>", lambda e: self._set_brake(0.0))
        self.brake_btn.pack(side=tk.LEFT, padx=6)

# Reset
        ttk.Button(frm, text="Reset", command=self._reset).pack(side=tk.LEFT, padx=(16, 0))

    def _build_gauges(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(side=tk.TOP, fill=tk.X, padx=12)

        self.speed_lbl = ttk.Label(frm, text="Speed: 0.0 km/h", font=("Segoe UI", 12, "bold"))
        self.speed_lbl.pack(side=tk.LEFT, padx=8)

        self.rpm_lbl = ttk.Label(frm, text="RPM: 800", font=("Segoe UI", 12, "bold"))
        self.rpm_lbl.pack(side=tk.LEFT, padx=8)

        self.gear_lbl = ttk.Label(frm, text="Gear: 1", font=("Segoe UI", 12))
        self.gear_lbl.pack(side=tk.LEFT, padx=8)

        self.temp_lbl = ttk.Label(frm, text="Coolant: 70.0 °C", font=("Segoe UI", 12))
        self.temp_lbl.pack(side=tk.LEFT, padx=8)

        self.fuel_lbl = ttk.Label(frm, text="Fuel: 80%", font=("Segoe UI", 12))
        self.fuel_lbl.pack(side=tk.LEFT, padx=8)

        self.batt_lbl = ttk.Label(frm, text="Battery: 12.5 V", font=("Segoe UI", 12))
        self.batt_lbl.pack(side=tk.LEFT, padx=8)

    def _build_plot(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=8)

        fig = Figure(figsize=(8, 4), dpi=100)
        self.ax = fig.add_subplot(111)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Speed (km/h) / RPM (x100)")
        self.ax.grid(True, alpha=0.3)

        (self.speed_line,) = self.ax.plot([], [], label="Speed (km/h)")
        (self.rpm_line,) = self.ax.plot([], [], label="RPM/100")
        self.ax.legend(loc="upper right")

        self.canvas = FigureCanvasTkAgg(fig, master=frm)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _bind_keys(self) -> None:
        self.bind("<KeyPress-Up>", lambda e: self._set_throttle(1.0))
        self.bind("<KeyRelease-Up>", lambda e: self._set_throttle(0.0))
        self.bind("<KeyPress-Down>", lambda e: self._set_brake(1.0))
        self.bind("<KeyRelease-Down>", lambda e: self._set_brake(0.0))
        self.bind("<KeyPress-e>", lambda e: self._toggle_engine(True))

    def _send_cmd(self, cmd: str, payload: object) -> None:
        try:
            self.cmd_q.put_nowait((cmd, payload))
        except queue.Full:
            pass

    def _set_throttle(self, val: float) -> None:
        self._send_cmd("throttle", max(0.0, min(1.0, val)))

    def _set_brake(self, val: float) -> None:
        self._send_cmd("brake", max(0.0, min(1.0, val)))

    def _toggle_engine(self, from_key=False) -> None:
        if from_key:
            on = not self.model.state.engine_on
            self.engine_btn.state(["selected"] if on else ["!selected"])
        else:
            on = self.engine_btn.instate(["selected"])  # current state after user toggle
        self._send_cmd("engine_on", on)

    def _set_gear(self) -> None:
        self._send_cmd("gear", self.gear_var.get())

    def _reset(self) -> None:
        self._send_cmd("reset", True)
        self.t_buf.clear(); self.speed_buf.clear(); self.rpm_buf.clear()
        self._redraw()


    def _ensure_csv(self) -> None:
        if self._csv_writer or self._telemetry_logger:
            return
        try:
            fresh = not os.path.exists(LOG_PATH)
            self._csv_fp = open(LOG_PATH, "a", newline="", encoding="utf-8")
            self._csv_writer = csv.writer(self._csv_fp)
            if fresh:
                self._csv_writer.writerow(["timestamp","rpm","speed_kph","coolant_c","fuel_pct","battery_v"])  # parity w/ README wording
        except Exception as e:
            messagebox.showerror("Logging error", str(e))
            self._csv_writer = None

    def _log_if_due(self, s: VehicleState) -> None:
        if (s.t - self._last_log_t) < LOG_INTERVAL_S:
            return
        self._last_log_t = s.t
        payload = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "rpm": int(s.rpm),
            "speed_kph": round(s.speed_kph, 2),
            "coolant_c": round(s.coolant_temp_c, 1),
            "fuel_pct": round(s.fuel_level_pct, 1),
            "battery_v": round(s.battery_v, 2),
        }
        if self._telemetry_logger:
            try:
                self._telemetry_logger.log(payload)
                return
            except Exception:
                pass  # fallback to CSV
        self._ensure_csv()
        if self._csv_writer:
            self._csv_writer.writerow(list(payload.values()))
            if self._csv_fp:
                self._csv_fp.flush()

    def _on_timer(self) -> None:
        latest: Optional[VehicleState] = None
        try:
            while True:
                latest = self.state_q.get_nowait()
        except queue.Empty:
            pass

        if latest:
            self.speed_lbl.configure(text=f"Speed: {latest.speed_kph:.1f} km/h")
            self.rpm_lbl.configure(text=f"RPM: {latest.rpm:.0f}")
            self.gear_lbl.configure(text=f"Gear: {latest.gear}")
            self.temp_lbl.configure(text=f"Coolant: {latest.coolant_temp_c:.1f} °C")
            self.fuel_lbl.configure(text=f"Fuel: {latest.fuel_level_pct:.1f} %")
            self.batt_lbl.configure(text=f"Battery: {latest.battery_v:.2f} V")

            # append to buffers
            self.t_buf.append(latest.t)
            self.speed_buf.append(latest.speed_kph)
            self.rpm_buf.append(latest.rpm / 100.0)

            # periodic logging (default 2s)
            self._log_if_due(latest)

            self._redraw()

        self.after(self.sample_interval_ms, self._on_timer)

    def _redraw(self) -> None:
        self.speed_line.set_data(self.t_buf, self.speed_buf)
        self.rpm_line.set_data(self.t_buf, self.rpm_buf)
        if self.t_buf:
            t0, t1 = self.t_buf[0], self.t_buf[-1]
            self.ax.set_xlim(t0, max(t1, t0 + 1.0))
            all_y = list(self.speed_buf) + list(self.rpm_buf)
            if all_y:
                ymin, ymax = min(all_y), max(all_y)
                pad = max(5.0, (ymax - ymin) * 0.1)
                self.ax.set_ylim(max(0.0, ymin - pad), ymax + pad)
        self.canvas.draw_idle()

    def _on_close(self) -> None:
        try:
            self.sim.stop()
        finally:
            try:
                if self._csv_fp:
                    self._csv_fp.close()
            finally:
                self.destroy()


if __name__ == "__main__":
    App().mainloop()