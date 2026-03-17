import time
import board
import adafruit_dht

# Tell the Pi to look for the DHT22 on GPIO 4 (Physical Pin 7)
dht_sensor = adafruit_dht.DHT22(board.D4)

print("Starting DHT22 Test... (Press Ctrl+C to quit)")

while True:
    try:
        # Ask the sensor for the data
        temperature_c = dht_sensor.temperature
        humidity = dht_sensor.humidity
        
        # Print it to the screen
        print(f"Temperature: {temperature_c:.1f}°C   |   Humidity: {humidity:.1f}%")

    except RuntimeError as error:
        # THE CHECKSUM TRAP: 
        # Linux is a busy operating system. Sometimes it gets distracted for a 
        # microsecond and misses a 1 or a 0 from the sensor. The library will 
        # throw a RuntimeError. This is completely normal! We just tell it to try again.
        print(f"Missed a reading, trying again... ({error.args[0]})")
        time.sleep(2.0)
        continue
        
    except Exception as error:
        # If something completely breaks, safely close the sensor
        dht_sensor.exit()
        raise error

    # The DHT22 is a slow sensor. It needs exactly 2 seconds between readings to reset.
    time.sleep(2.0)