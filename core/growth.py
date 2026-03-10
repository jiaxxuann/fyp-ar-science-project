class GrowthPredictor:
    def __init__(self):
        # Thresholds for a standard house plant (e.g., a bean or pothos)
        # TODO: change thresholds to more accurate values!
        self.thresholds = {
            'water_min': 300,   'water_max': 850, # min: <20%, max: >80%
            'light_min': 150,   'light_max': 800,
            'temp_min': 15.0,   'temp_max': 32.0,
            'humid_min': 20,    'humid_max': 80
        }

        # Hardware UI scales (Min, Max, Unit) for drawing the bars
        self.hardware_limits = {
            'water': (0, 1023, " %"),
            'light': (0, 1000, " lx"),
            'temp': (0, 50, " C"),
            'humid': (0, 100, " %")
        }

    def predict_health(self, sensor_data):
        """
        Evaluates real-time sensor data against biological thresholds.
        Returns a tuple: (State, Diagnostic_Message)
        """

        # 1. Check Soil Moisture
        if sensor_data['water'] < self.thresholds['water_min']:
            return "WILT", "Needs Water!"
        if sensor_data['water'] > self.thresholds['water_max']:
            return "WILT", "Too Much Water!"

        # 2. Check Light
        if sensor_data['light'] < self.thresholds['light_min']:
            return "WILT", "Needs Sunlight!"
        
        # 3. Check Temperature
        if sensor_data['temp'] < self.thresholds['temp_min']:
            return "WILT", "Too Cold!"
        if sensor_data['temp'] > self.thresholds['temp_max']:
            return "WILT", "Too Hot!"
        
        # 4. Check Humidity
        if sensor_data['humid'] < self.thresholds['humid_min']:
            return "WILT", "Not Humid!"
        if sensor_data['humid'] > self.thresholds['humid_max']:
            return "WILT", "Too Humid!"

        # 5. If all conditions are within safe ranges
        return "HEALTHY", "Conditions Optimal"