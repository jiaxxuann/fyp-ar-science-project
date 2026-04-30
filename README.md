# AR Educational Science Tool for Primary Plant Biology

## Description
This repository contains the source code for an Augmented Reality (AR) Educational Science Tool, developed as a final-year project for the BSc Computer Science with Artificial Intelligence program at the University of Nottingham Malaysia. 

Powered by a Raspberry Pi 5, this system utilizes a Tangible User Interface (TUI) to bridge the gap between physical environmental interactions and digital biological visualization. It utilizes asynchronous real-time sensor polling (light, moisture, temperature, humidity) combined with an OpenCV-based computer vision pipeline to project dynamic, marker-based AR graphics over a live plant.

## Key Features (Educational Modules)
1. **AR Particles:** Translates real-time sensor data into animated H2O and CO2/O2 particle flows. The system evaluates data against predefined biological thresholds, rendering a surprise flower bloom when optimal balance is achieved.
2. **Microscope View:** Features interactive AR hotspots dynamically anchored to the physical plant's stem and leaves (calculating 6-DOF pose estimation). Tapping these regions generates a magnified picture-in-picture (PiP) window of internal vascular transports.
3. **Growth Prediction:** A heuristic predictive logic engine that simulates future health trajectories (thriving vs. wilting) based on the continuous combination of multi-sensor inputs.
4. **Climate Stress Simulation:** A gesture-controlled module that cycles through extreme biomes (Tropical, Desert, Arctic, Acid Rain) using touchscreen swipes. It dynamically alters global screen filters, weather particle effects, and the plant's structural health to teach cause-and-effect.

## Hardware Requirements
The project relies on a decoupled physical architecture to accommodate camera Field of View (FOV) constraints while maintaining an ergonomic workspace for young students.

* **Core Processing:** Raspberry Pi 5 (running 64-bit Raspberry Pi OS)
* **Vision Tracking:** PiCamera2 Module
* **Hardware Bridge:** MCP3008 ADC (Analog-to-Digital Converter)
* **Sensors:**
  * Capacitive Soil Moisture Sensor (Analog -> SPI via MCP3008)
  * BH1750 Ambient Light Sensor (I2C Protocol)
  * DHT22 Temperature & Humidity Sensor (1-Wire GPIO Protocol)
* **Output:** LCD Touchscreen Display
* **AR Anchor:** Physical ArUco marker printed and affixed to the plant's placed directly center-front.

## Software Dependencies & Installation
The system is built on Python 3 and runs within an isolated virtual environment to prevent dependency conflicts with global Raspberry Pi system tools.

### 1. Enable Hardware Interfaces
Ensure that both I2C and SPI protocols are enabled on your Raspberry Pi:
```bash
sudo raspi-config
# Navigate to Interface Options -> Enable I2C
# Navigate to Interface Options -> Enable SPI
# Reboot the system
```
### 2. Setup Virtual Environment
```bash
python3 -m venv ar_project_env
source ar_project_env/bin/activate
```

### 3. Install Required Packages
Install the required OpenCV (with contrib for ArUco) and hardware abstraction libraries:
```bash
pip install opencv-contrib-python
pip install PyQt5
pip install adafruit-circuitpython-bh1750
pip install adafruit-circuitpython-dht
pip install adafruit-circuitpython-mcp3xxx
```

## Running the Application
1. Ensure the Raspberry Pi, PiCamera2, and LCD display are securely connected.
2. Verify your hardware wiring against the breadboard schematic (MCP3008 to SPI pins, BH1750 to I2C pins, DHT22 to standard GPIO).
3. Ensure the camera has a clear, well-lit view of both the physical plant and the ArUco tracking marker.
4. Activate the virtual environment and execute the main application:
```bash
source ar_project_env/bin/activate
python main.py
```

## Project Architecture
To ensure maintainability and prevent blocking operations (e.g., hardware polling freezing the video feed), the system is architected into three primary concurrent threads:
* **Hardware Abstraction Layer (HAL)**: Implemented via a SensorManager class executing a non-blocking polling loop every 2.0 seconds.
* **Computer Vision (CV) Render Loop**: Uses OpenCV to calculate rotation (rvec) and translation (tvec) vectors for stable AR spatial anchoring.
* **UI Event Listener**: Asynchronously tracks user touchscreen inputs and handles modular navigation.

## Author
**Siow Jia Xuan**  
BSc Computer Science with Artificial Intelligence (Hons)  
University of Nottingham Malaysia
