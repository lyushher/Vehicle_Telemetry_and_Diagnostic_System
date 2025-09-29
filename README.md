
# Real-Time Vehicle Telemetry and Diagnostic System

A Python-based system that simulates core functionalities of an Electronic Control Unit (ECU) used in modern vehicles.  
This project provides a real-time visual and interactive environment to observe how engine data behaves during acceleration and braking events.

-  **Tkinter** GUI replicates a simple dashboard interface  
-  **Matplotlib** graphs display live RPM and speed updates  
-  **Multithreaded engine** keeps the UI responsive while physics ticks at 60 Hz.
- **Periodic CSV logging** of coolant temperature, fuel level, and battery voltage

> Ideal for educational use, experimentation, and testing embedded logic before working with real hardware.


---

## ⚙️ Tech Stack

| Technology   | Purpose             |
|--------------|---------------------|
| Python 3     | Core programming language |
| Tkinter      | Desktop GUI interface     |
| Matplotlib   | Real-time graph plotting  |
| Threading    | Concurrent data updates   |
| CSV          | Periodic sensor data logging |

---

## ✨ Features

- **Threaded 60 Hz simulator** with simple longitudinal physics (throttle, brake, drag, gears).
- **Tkinter UI** with press-and-hold **Gas/Brake**, engine toggle, gear control.
- **Live Matplotlib plot** of **Speed** and **RPM/100** with autoscaling.
- **CSV logging** every **2 seconds** to `logs/telemetry_log.csv`.
- **Resilient design**: optional sensors/logger modules auto-fallback so the app still runs.

---

## 📁 Project Structure

```
Vehicle_Telemetry_and_Diagnostic_System/
├── main.py                  # Main GUI simulator
├── telemetry/               # Vehicle data logic
│   ├── __init__.py
│   ├── simulator.py         # (planned)
│   ├── controller.py        # (planned)
│   └── sensors.py           # Randomized temp, fuel, battery voltage
├── telemetry_logger.py      # Logs sensor data to CSV
├── gui/                     # (optional UI modules)
├── tests/                   # (unit tests - planned)
├── logs/                    # Log output directory (auto-created)
└── README.md                # Project documentation
```

---

## 🚀 Getting Started

### 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/lyushher/Vehicle_Telemetry_and_Diagnostic_System.git
cd Vehicle_Telemetry_and_Diagnostic_System
```

2. (Optional) Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
```

3. Install dependencies:
```bash
pip install matplotlib
```

### ▶️ Run the Simulator
```bash
python main.py
```

---

## 📊 Logs

Sensor data is logged every 2 seconds to `logs/telemetry_log.csv`. Each entry includes:

- Timestamp
- RPM
- Speed (km/h)
- Engine Temperature (°C)
- Fuel Level (%)
- Battery Voltage (V)

---

## 🧪 Testing (Planned)

- Unit tests using `pytest`
- Coverage reports via `pytest-cov`

---

## 🔧 CI/CD (Planned)

- GitHub Actions for automated testing
- Linting and code quality checks

---

## ☁️ Deployment (Planned)

- Docker containerization
- EC2 / Streamlit / FastAPI-based deployment

---

## 📬 API Endpoints (Planned)

This project will include a REST API using FastAPI to expose real-time telemetry data. Example endpoints:

```http
GET /telemetry        # Latest sensor readings
GET /logs             # Access logged data
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

> **Note:** This project is under active development and will progressively include API endpoints, tests, and cloud deployment support.
