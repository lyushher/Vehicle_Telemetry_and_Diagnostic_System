import csv
from datetime import datetime
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log_data(rpm, speed, temp, fuel, voltage):
    filename = f"{LOG_DIR}/telemetry_log.csv"
    with open(filename, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            rpm, speed, temp, fuel, voltage])

