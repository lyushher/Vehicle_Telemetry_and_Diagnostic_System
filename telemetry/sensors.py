import random

def get_engine_temp():
    return round(random.uniform(70.0, 120.0), 2)

def get_fuel_level():
    return round(random.uniform(0.0, 100.0), 2)

def get_battery_voltage():
    return round(random.uniform(12.0, 14.8), 2)


