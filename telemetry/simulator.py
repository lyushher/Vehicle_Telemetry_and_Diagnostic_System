import random

def generate_rpm():
    return random.randint(700, 7000)

def generate_speed():
    return round(random.uniform(0, 180), 2)
