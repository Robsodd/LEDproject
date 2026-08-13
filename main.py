import machine
import time

# 1. Initialize the I2C bus on your standard pins
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=100000)

# 2. Give the OLED a tiny fraction of a second to power up
time.sleep(0.1)

# 3. Scan the bus for connected devices
devices = i2c.scan()

# 4. Route the logic based on the scan results
if devices:
    print("OLED Detected! Booting Control Box...")
    import control_box
    # Assuming you wrap your UI code in a main() function:
    control_box.start() 
else:
    print("No OLED Detected. Booting Speaker Stand...")
    import speaker_stand
    speaker_stand.start()