import time
import board
import busio
import digitalio
import adafruit_dht
import adafruit_bh1750
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

class SensorManager:
    def __init__(self, mock_mode=False):
        self.mock_mode = mock_mode
        print("Initializing Hardware Sensors...")
        
        if not self.mock_mode:
            # 1. Light Sensor (I2C)
            self.i2c = board.I2C()
            self.light_sensor = adafruit_bh1750.BH1750(self.i2c)

            # 2. Temp/Humidity Sensor (DHT22 on GPIO 4 / Pin 7)
            self.dht_sensor = adafruit_dht.DHT22(board.D4)

            # 3. Soil Moisture (SPI on GPIO 25 / Pin 22)
            self.spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
            self.cs = digitalio.DigitalInOut(board.D25)
            self.mcp = MCP.MCP3008(self.spi, self.cs)
            self.soil_sensor = AnalogIn(self.mcp, MCP.P0)

            # Soil Calibration Constants
            self.dry_voltage = 2.33  # Voltage when sensor is bone dry in the air
            self.wet_voltage = 1.50  # Voltage when sensor is submerged in water

            # Store last known good values to prevent AR crashes
            self.last_temp = 25.0
            self.last_hum = 50.0

    def read_all(self):
        """Reads all sensors and returns a dictionary of the current environment."""
        
        # Mock Mode is ON, return a fake dictionary
        if self.mock_mode:
            return{
                "temperature": 26.0,
                "humidity": 60,
                "light": 800,
                "soil_voltage": 1.5,
                "soil_percent": 80
            }

        # Read Light
        try:
            light_lux = self.light_sensor.lux
        except Exception:
            light_lux = 0.0

        # Read & Convery Soil Voltage
        try:
            soil_volt = self.soil_sensor.voltage

            # Simple math to get a percentage
            moisture_pct = ((self.dry_voltage - soil_volt) / (self.dry_voltage - self.wet_voltage)) * 100
            
            # Clamp it between 0 and 100 as an integer
            soil_percent = max(0, min(100, int(moisture_pct)))
        except Exception:
            soil_volt = 0.0
            soil_percent = 0

        # Read DHT22 (It frequently drops readings, so we catch the error)
        try:
            self.last_temp = self.dht_sensor.temperature
            self.last_hum = self.dht_sensor.humidity
        except RuntimeError:
            pass # Ignore the dropped reading and keep using the last known value
            
        return {
            "temperature": self.last_temp,
            "humidity": self.last_hum,
            "light": light_lux,
            "soil_voltage": soil_volt,
            "soil_percent": soil_percent
        }