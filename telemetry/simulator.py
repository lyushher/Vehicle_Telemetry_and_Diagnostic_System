import random
import asyncio

def generate_rpm():
    return random.randint(700, 7000)

def generate_speed():
    return round(random.uniform(0, 180), 2)

class VehicleSimulator:
    def __init__(self):
        self.rpm = 800
        self.speed = 0.0
        self.temp = 70.0
        self.fuel = 100.0
        self.voltage = 13.2

        self.gas_pressed = False
        self.brake_pressed = False

    def press_gas(self):
        self.gas_pressed = True
        self.brake_pressed = False

    def press_brake(self):
        self.brake_pressed = True
        self.gas_pressed = False

    def release_pedals(self):
        self.gas_pressed = False
        self.brake_pressed = False

    def update(self, dt: float = 1.0):
        if self.gas_pressed:
            self.rpm = min(self.rpm + 400 * dt, 6000)
            self.speed = min(self.speed + 3.0 * dt, 220)
        elif self.brake_pressed:
            self.rpm = max(self.rpm - 600 * dt, 700)
            self.speed = max(self.speed - 6.0 * dt, 0.0)
        else:
            self.rpm = max(self.rpm - 150 * dt, 700)
            self.speed = max(self.speed - 1.2 * dt, 0.0)

        self.temp = max(20.0, min(self.temp + (self.rpm - 800) / 8000 * 5.0 * dt, 120.0))

        self.fuel = max(0.0, self.fuel - (self.rpm / 8000.0) * 0.05 * dt)

        self.voltage = 12.5 if self.rpm < 1000 else 13.8

    def get_state(self):
        return {
            "rpm": round(self.rpm),
            "speed": round(self.speed, 1),
            "engine_temp": round(self.temp, 1),
            "fuel_level": round(self.fuel, 2),
            "battery_voltage": round(self.voltage, 2),
        }

    async def run(self):
        while True:
            self.update()
            await asyncio.sleep(1.0)
