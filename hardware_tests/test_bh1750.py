import time
import board
import adafruit_bh1750

# 1. Initialize the I2C bus using the standard Pi pins (SCL=Pin 5, SDA=Pin 3)
i2c = board.I2C()

# 2. Tell the library to look for the sensor on that bus
sensor = adafruit_bh1750.BH1750(i2c)

print("Starting BH1750 Light Sensor Test... (Press Ctrl+C to quit)")

while True:
    try:
        # Read the light level in Lux
        light_level = sensor.lux
        
        # Print the formatted output
        print(f"Current Light Level: {light_level:.2f} Lux")
        
    except Exception as error:
        print(f"Error reading sensor: {error}")
        
    # The BH1750 updates fast, but half a second is perfect for reading it
    time.sleep(0.5)