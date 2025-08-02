
rpm = 0

def accelerate():
    global rpm
    rpm = min(rpm + 500, 7000)
    return rpm

def brake():
    global rpm
    rpm = max(rpm - 800, 0)
    return rpm

