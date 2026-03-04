import cv2
import numpy as np
import math

class UIManager:
    def __init__(self):
        self.menu_width = 220

        # Define button areas: [y_start, y_end, label, mode_name]
        self.buttons = [
            (20, 80, "Main: Particles", "MAIN"),
            (100, 160, "Microscope", "MICRO"),
            (180, 240, "Growth Predict", "GROWTH"),
            (260, 320, "Climate Stress", "CLIMATE")]

        # Define button areas in Microsope function
        self.current_leaf_btn = (0, 0)
        self.current_stem_btn = (0, 0)
        self.btn_radius = 25
        self.active_zoom_state = None  # "GAS", "WATER", or None
        
    def draw_sidebar(self, frame, current_mode):
        h, w, _ = frame.shape
        start_x = w - self.menu_width

        # 1. Draw Sidebar Background
        overlay = frame.copy()

        cv2.rectangle(overlay, (start_x, 0), (w, h), (40, 40, 40), -1)

        # 2. Draw Buttons
        for y1, y2, label, mode in self.buttons:
            # Highlight the active button
            color = (0, 200, 0) if mode == current_mode else (100, 100, 100)
            
            # Draw button rect
            cv2.rectangle(overlay, (start_x + 10, y1), (w - 10, y2), color, -1)
            # Draw white border for better visibility
            cv2.rectangle(overlay, (start_x + 10, y1), (w - 10, y2), (255, 255, 255), 1)
            
            # Draw text
            cv2.putText(overlay, label, (start_x + 20, y1 + 35), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
        # 3. Blend the overlay onto the original frame
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

    def draw_hud(self, frame, sensor_data):
        h, w, _ = frame.shape
    
        # 1. Define HUD dimensions
        # background box that fits 4 bars
        hud_w = 260
        hud_h = 130
        
        # 2. Draw a semi-transparent background box at the bottom left
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - hud_h), (hud_w, h), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # 3. Bar configuration
        bar_w = 140
        start_x = 20
        start_y = h - hud_h + 25 # Vertical position for the bars
        row_spacing = 25 # vertical gap between bars

        # 4. Draw each sensor bar
        # Use a list to iterate through them easily
        sensors = [
            ("Water", sensor_data['water'], 0, 1023, "%"),
            ("Light", sensor_data['light'], 0, 1000, "lx"),
            ("Temp", sensor_data['temp'], 0, 50, "C"),
            ("Humid", sensor_data['hum'], 0, 100, "%") # standard min max
        ]

        for i, (label, val, min_v, max_v, unit) in enumerate(sensors):
            y_pos = start_y + (i * row_spacing)
            self.draw_bar(frame, start_x, y_pos, label, val, min_v, max_v, unit, bar_w)

    def draw_bar(self, frame, x, y, label, value, min_v, max_v, unit, width):
        height = 10
        label_spacing = 45

        # Calculate percentage
        percent = (value - min_v) / (max_v - min_v)
        percent = max(0, min(1, percent))
        
        # Draw Label
        cv2.putText(frame, f"{label}", (x, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
        
        # Draw Background
        bar_x = x + label_spacing
        cv2.rectangle(frame, (bar_x, y), (bar_x + width, y + height), (80, 80, 80), -1)
        
        # Color logic (CHANGE ACCORDINGLY!)
        if label == "Water":
            if percent < 0.2 or percent > 0.8: 
                color = (0, 0, 255) # Red for alert
            else: 
                color = (0, 255, 0) # Default Green
        if label == "Light":
            if percent < 0.2 or percent > 0.8: 
                color = (0, 0, 255) # Red for alert
            else:
                color = (0, 255, 0) # Default Green
        if label == "Temp":
            if percent < 0.2 or percent > 0.8: 
                color = (0, 0, 255) # Red for alert
            else:
                color = (0, 255, 0) # Default Green
        if label == "Humid":
            if percent < 0.2 or percent > 0.8: 
                color = (0, 0, 255) # Red for alert
            else: color = (0, 255, 0) # Default Green
        
        # Draw Fill
        fill_w = int(width * percent)
        cv2.rectangle(frame, (bar_x, y), (bar_x + fill_w, y + height), color, -1)

        # Draw Value on the RIGHT of the bar
        cv2.putText(frame, f"{value}{unit}", (bar_x + width + 5, y + 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)

    def handle_click(self, x, y, frame_width):
        # Check if the click was within the sidebar area
        if x > frame_width - self.menu_width:
            for y1, y2, label, mode in self.buttons:
                if y1 <= y <= y2:
                    return mode
        return None
    
    # Microscope Functions
    def check_ar_button_click(self, x, y):
            
            # Check Leaf Button
            dist_to_leaf = math.hypot(x - self.current_leaf_btn[0], y - self.current_leaf_btn[1])
            if dist_to_leaf <= self.btn_radius:
                self.active_zoom_state = "GAS"
                print("UI Manager: GAS selected")
                return # Exit the function early if clicked
                
            # Check Stem Button
            dist_to_stem = math.hypot(x - self.current_stem_btn[0], y - self.current_stem_btn[1])
            if dist_to_stem <= self.btn_radius:
                self.active_zoom_state = "WATER"
                print("UI Manager: WATER selected")
                return
                
            # Clicked somewhere else -> Close the window
            if self.active_zoom_state is not None:
                self.active_zoom_state = None
                print("UI Manager: Window Closed")
    
    def draw_zoom_window(self, frame, bbox):
        # 1. Get plant coordinates
        # bbox = [x, y, w, h]
        x, y, bw, bh = bbox 
        
        # 2. Add some 'padding' so the zoom isn't too tight
        pad = 20
        y1, y2 = max(0, y - pad), min(frame.shape[0], y + bh + pad)
        x1, x2 = max(0, x - pad), min(frame.shape[1], x + bw + pad)
        
        # 3. CROP the image
        crop = frame[y1:y2, x1:x2]
        
        if crop.size > 0:
            # 4. RESIZE to a fixed window size (e.g., 200x200)
            zoom_size = 200
            zoomed_part = cv2.resize(crop, (zoom_size, zoom_size), interpolation=cv2.INTER_LINEAR)
            
            # 5. DEFINE WHERE TO SHOW IT (e.g., Top Left corner)
            # Position: y_offset:y_offset+height, x_offset:x_offset+width
            off_y, off_x = 30, 30 
            
            # 6. DRAW A BORDER & BACKGROUND for the zoom window
            cv2.rectangle(frame, (off_x-5, off_y-5), (off_x+zoom_size+5, off_y+zoom_size+5), (255, 255, 255), -1)
            cv2.putText(frame, "MICROSCOPE VIEW", (off_x, off_y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 7. OVERLAY the zoomed part back onto the main frame
            frame[off_y:off_y+zoom_size, off_x:off_x+zoom_size] = zoomed_part

            import cv2

    # modify drawing function to update 'self' variables
    def draw_ar_buttons(self, frame, bbox):
            x, y, w, h = bbox
            
            # Update the class attributes directly
            self.current_stem_btn = (x + (w // 2), y + int(h * 0.85))
            self.current_leaf_btn = (x + (w // 2), y + int(h * 0.25))
            
            # Draw Leaf Button
            cv2.circle(frame, self.current_leaf_btn, self.btn_radius + 5, (0, 255, 0), 2)
            cv2.circle(frame, self.current_leaf_btn, self.btn_radius, (0, 200, 0), -1)
            
            # Draw Stem Button
            cv2.circle(frame, self.current_stem_btn, self.btn_radius + 5, (255, 0, 0), 2)
            cv2.circle(frame, self.current_stem_btn, self.btn_radius, (200, 0, 0), -1)