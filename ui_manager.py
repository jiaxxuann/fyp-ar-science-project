import cv2
import math
import random
from collections import deque

import numpy as np

class UIManager:
    def __init__(self):
        # Sidebar config
        self.menu_width = 220
        # Define button areas: [y_start, y_end, label, mode_name]
        self.buttons = [
            (20, 80, "Main: Particles", "MAIN"),
            (100, 160, "Microscope", "MICRO"),
            (180, 240, "Growth Predict", "GROWTH"),
            (260, 320, "Climate Stress", "CLIMATE")]

        # AR microscope config
        self.current_leaf_btn = (0, 0)
        self.current_stem_btn = (0, 0)
        self.btn_radius = 25
        self.active_zoom_state = None  # "GAS", "WATER", or None

        self.micro_particles_gas = deque(maxlen=150)
        self.micro_particles_water = deque(maxlen=150)

    # ==========================================
    # BLOCK 1: GLOBAL UI & MENUS
    # ==========================================
    def draw_notification(self, frame, text, position=(10, 50), color=(0, 0, 255)):
        # Optional: Draw a subtle black background rectangle so text is always readable
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        bg_rect = ((position[0] - 5, position[1] + 5), 
                   (position[0] + text_size[0] + 5, position[1] - text_size[1] - 5))
        
        cv2.rectangle(frame, bg_rect[0], bg_rect[1], (0, 0, 0), -1)
        cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2) # draw text
        
    def draw_sidebar(self, frame, current_mode):
        h, w, _ = frame.shape
        start_x = w - self.menu_width
        overlay = frame.copy() # Draw sidebar background

        # Background
        cv2.rectangle(overlay, (start_x, 0), (w, h), (40, 40, 40), -1)

        # Buttons
        for y1, y2, label, mode in self.buttons:
            # Highlight active button
            color = (0, 200, 0) if mode == current_mode else (100, 100, 100)
            # Draw button rect
            cv2.rectangle(overlay, (start_x + 10, y1), (w - 10, y2), color, -1)
            # Draw white border for better visibility
            cv2.rectangle(overlay, (start_x + 10, y1), (w - 10, y2), (255, 255, 255), 1)
            # Draw text
            cv2.putText(overlay, label, (start_x + 20, y1 + 35), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
        # Blend the overlay onto the original frame
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

    def handle_click(self, x, y, frame_width):
        # Checks if the click is within the sidebar menu
        if x > frame_width - self.menu_width:
            for y1, y2, label, mode in self.buttons:
                if y1 <= y <= y2:
                    return mode
        return None

    # ==========================================
    # BLOCK 2: ENVIRONMENTAL HUD
    # ==========================================    
    def draw_hud(self, frame, sensor_data):
        h, w, _ = frame.shape
    
        # HUD dimensions: Background box that fits 4 bars
        hud_w = 260
        hud_h = 130
        
        # Background: Draw a semi-transparent background box at the bottom left
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - hud_h), (hud_w, h), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # Bar configuration
        bar_w = 140
        start_x = 20
        start_y = h - hud_h + 25 # vertical position for the bars
        row_spacing = 25 # vertical gap between bars

        # Sensor values: Use a list to iterate through them easily
        sensors = [
            ("Water", sensor_data['water'], 0, 1023, "%"),
            ("Light", sensor_data['light'], 0, 1000, "lx"),
            ("Temp", sensor_data['temp'], 0, 50, "C"),
            ("Humid", sensor_data['hum'], 0, 100, "%") # standard min max
        ]

        # Sensor bars
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
        
        # Draw Background Track
        bar_x = x + label_spacing
        cv2.rectangle(frame, (bar_x, y), (bar_x + width, y + height), (80, 80, 80), -1)
        
        # Color logic: Changes accordingly
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

        # Draw Value Text: On the RIGHT of the bar
        cv2.putText(frame, f"{value}{unit}", (bar_x + width + 5, y + 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
    
    # ==========================================
    # BLOCK 3: AR MICROSCOPE LOGIC
    # ==========================================
    # Modify drawing function to update 'self' variables
    def draw_ar_buttons(self, frame, bbox):
            x, y, w, h = bbox
            
            # Anchor UI based on bounding box proportions: Update the class attributes directly
            self.current_stem_btn = (x + (w // 2), y + int(h * 0.85))
            self.current_leaf_btn = (x + (w // 2), y + int(h * 0.25))
            
            # Draw Leaf Button (Gas)
            cv2.circle(frame, self.current_leaf_btn, self.btn_radius + 5, (0, 255, 0), 2)
            cv2.circle(frame, self.current_leaf_btn, self.btn_radius, (0, 200, 0), -1)
            
            # Draw Stem Button (Water)
            cv2.circle(frame, self.current_stem_btn, self.btn_radius + 5, (255, 0, 0), 2)
            cv2.circle(frame, self.current_stem_btn, self.btn_radius, (200, 0, 0), -1)

    def check_ar_button_click(self, x, y):
            # Checks if a floating AR node was clicked on the plant
            dist_to_leaf = math.hypot(x - self.current_leaf_btn[0], y - self.current_leaf_btn[1])
            if dist_to_leaf <= self.btn_radius:
                self.active_zoom_state = "GAS"
                print("UI Manager: GAS selected")
                return # Exit the function early if clicked
                
            dist_to_stem = math.hypot(x - self.current_stem_btn[0], y - self.current_stem_btn[1])
            if dist_to_stem <= self.btn_radius:
                self.active_zoom_state = "WATER"
                print("UI Manager: WATER selected")
                return
                
            # Clicked empty space on plant frame -> Close the window
            if self.active_zoom_state is not None:
                self.active_zoom_state = None
                print("UI Manager: Window Closed")
    
    def draw_zoom_window(self, frame, bbox, zoom_state, source_frame=None):
        # Get plant coordinates
        x, y, bw, bh = bbox  # bbox = [x, y, w, h]
        src = source_frame if source_frame is not None else frame
        frame_h, frame_w = src.shape[:2]

        # Add some padding so the zoom isn't too tight
        pad = 15

        # Focus on different plant regions based on zoom state
        if zoom_state == "GAS":
            # Leaves: crop top ~50% of plant (leaf area)
            y1 = max(0, y - pad)
            y2 = min(frame_h, y + int(bh * 0.55) + pad)
        elif zoom_state == "WATER":
            # Stem: crop bottom ~55% of plant (stem area)
            y1 = max(0, y + int(bh * 0.45) - pad)
            y2 = min(frame_h, y + bh + pad)
        else:
            # Fallback: full plant
            y1 = max(0, y - pad)
            y2 = min(frame_h, y + bh + pad)

        x1 = max(0, x - pad)
        x2 = min(frame_w, x + bw + pad)

        # Crop from the source frame (clean camera image)
        crop = src[y1:y2, x1:x2]
        
        if crop.size > 0:
            # Resize without distortion (preserve aspect ratio, fill window via center-crop)
            zoom_size = 200
            crop_h, crop_w = crop.shape[:2]
            if crop_h == 0 or crop_w == 0:
                return

            # Cover scaling: ensure the resized image fully covers the square,
            # then center-crop down to (zoom_size x zoom_size)
            scale = max(zoom_size / crop_w, zoom_size / crop_h)
            new_w = max(zoom_size, int(crop_w * scale))
            new_h = max(zoom_size, int(crop_h * scale))

            resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            x0 = max(0, (new_w - zoom_size) // 2)
            y0 = max(0, (new_h - zoom_size) // 2)
            zoomed_part = resized[y0:y0 + zoom_size, x0:x0 + zoom_size]
            
            # Draw window frame + title, then overlay zoomed_part back to frame
            off_y, off_x = 30, 30
            cv2.rectangle(frame, (off_x-5, off_y-5), (off_x+zoom_size+5, off_y+zoom_size+5), (255, 255, 255), -1)

            if zoom_state == "GAS":
                title_text = "O2 / CO2 EXCHANGE"
                title_color = (0, 255, 0)
            elif zoom_state == "WATER":
                title_text = "WATER TRANSPORT"
                title_color = (0, 0, 255)
            else:
                title_text = "MICROSCOPE VIEW"
                title_color = (255, 255, 255)

            cv2.putText(frame, title_text, (off_x, off_y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, title_color, 1)

            # Overlay the zoomed part back onto the main frame
            frame[off_y:off_y+zoom_size, off_x:off_x+zoom_size] = zoomed_part