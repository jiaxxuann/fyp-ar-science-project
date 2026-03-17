import time
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

print("Starting Soil Moisture Test... (Press Ctrl+C to quit)")

# 1. Initialize the SPI bus
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# 2. Set up the Chip Select (CS) pin on GPIO 25 (Physical Pin 22)
cs = digitalio.DigitalInOut(board.D25)

# 3. Create the MCP3008 object
mcp = MCP.MCP3008(spi, cs)

# 4. Tell it we plugged the sensor into Channel 0 (Pin 1)
soil_channel = AnalogIn(mcp, MCP.P0)

while True:
    # The raw value is a number between 0 and 65535
    raw_value = soil_channel.value
    voltage = soil_channel.voltage
    
    print(f"Raw Value: {raw_value} | Voltage: {voltage:.2f}V")
    time.sleep(0.5)