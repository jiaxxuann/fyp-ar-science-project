import cv2
import math
import random
from collections import deque

import numpy as np

class UIManager:
    def __init__(self):
        self.sidebars = {}
        try:
            self.sidebars['MAIN'] = cv2.imread('assets/sidebar-main.png', cv2.IMREAD_UNCHANGED)
            self.sidebars['MICRO'] = cv2.imread('assets/sidebar-micro.png', cv2.IMREAD_UNCHANGED)
            self.sidebars['GROWTH'] = cv2.imread('assets/sidebar-growth.png', cv2.IMREAD_UNCHANGED)
            self.sidebars['SIMULATION'] = cv2.imread('assets/sidebar-climate.png', cv2.IMREAD_UNCHANGED)
            self.hud_bg = cv2.imread('assets/hud.png', cv2.IMREAD_UNCHANGED)
            print("Successfully loaded Figma pngs!")
        except Exception as e:
            print("Error loading Figma sidebars: {e}")

        # Calculate and save the exact position of the sidebar
        self.sidebar_h = self.sidebars['MAIN'].shape[0] # height of sidebar
        self.sidebar_w = self.sidebars['MAIN'].shape[1] # width of sidebar

        # DEBUGGING
        main_shape = self.sidebars['MAIN'].shape
        print(f"DEBUG: The true exported size of MAIN is Height: {main_shape[0]}, Width: {main_shape[1]}")

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
        """Draws the pre-designed Figma sidebar based on the active mode."""
        
        # 1. Grab the correct pre-designed PNG from our dictionary
        # If for some reason the mode isn't found, default to 'MAIN'
        active_img = self.sidebars.get(current_mode, self.sidebars.get('MAIN'))

        # 2. Paste it onto the left side of the screen (x=0, y=0)
        if active_img is not None:
            img_height = active_img.shape[0]

            bg_height = frame.shape[0] # 960
            bg_width = frame.shape[1] # 1280

            sidebar_x = bg_width - 180
            sidebar_y = int((bg_height - img_height) / 2)

            # We must return the frame so the main loop gets the updated image!
            frame = self.overlay_transparent(frame, active_img, sidebar_x, sidebar_y)
            
            # ==========================================
            # --- DEBUG MODE: DRAW VISUAL HITBOXES ---
            # ==========================================
            # cv2.rectangle(frame, 
            #   (sidebar_x, sidebar_y), 
            #   (sidebar_x + self.sidebar_w, sidebar_y + self.sidebar_h), 
            #   (255, 255, 0), 2)

            # # Button 1: MAIN (Red Box)
            # cv2.rectangle(frame, (sidebar_x + 42, sidebar_y + 47), (sidebar_x + self.sidebar_w - 42, sidebar_y + 139), (0, 0, 255), 2)
            
            # # Button 2: MICRO (Green Box)
            # cv2.rectangle(frame, (sidebar_x, sidebar_y + 157), (sidebar_x + self.sidebar_w, sidebar_y + 249), (0, 255, 0), 2)
            
            # # Button 3: GROWTH (Blue Box)
            # cv2.rectangle(frame, (sidebar_x, sidebar_y + 267), (sidebar_x + self.sidebar_w, sidebar_y + 359), (255, 0, 0), 2)
            
            # # Button 4: SIMULATION (Yellow Box)
            # cv2.rectangle(frame, (sidebar_x, sidebar_y + 377), (sidebar_x + self.sidebar_w, sidebar_y + 469), (0, 255, 255), 2)
            # ==========================================
        return frame

    def handle_click(self, x, y, frame_width, frame_height):
        """Checks if a mouse click hit any of our invisible Figma buttons."""
        
        sidebar_x = frame_width - 180
        sidebar_y = int((frame_height - self.sidebar_h) / 2)

        if sidebar_x + 42 <= x <= (sidebar_x + self.sidebar_w - 42):
            
            # Convert screen click to Figma 'Local' click
            local_y = y - sidebar_y
            
            # Use the exact Y coordinates measured in Figma + 20 invisible padding
            if 47 <= local_y <= 139:
                print("Main Particles Mode Clicked!")
                return "MAIN"
                
            elif 157 <= local_y <= 249:
                print("Microscope Mode Clicked!")
                return "MICRO"
                
            elif 267 <= local_y <= 359:
                print("Growth Mode Clicked!")
                return "GROWTH"
                
            elif 377 <= local_y <= 469:
                print("Simulation Mode Clicked!")
                return "SIMULATION"

        # If clicked somewhere else on the screen, do nothing
        return None

    # ==========================================
    # BLOCK 2: ENVIRONMENTAL HUD
    # ==========================================    
    def draw_hud(self, frame, sensor_data, predictor):
        h, w = frame.shape[:2]

        # 1. Calculate HUD placement (Bottom Left corner)
        if hasattr(self, 'hud_bg') and self.hud_bg is not None:
            hud_h, hud_w = self.hud_bg.shape[:2]
        else:
            hud_h, hud_w = 130, 260 # Fallback sizes
        
        # hud coordinates (bottom-left)
        hud_x = 20 # 20px from left edge
        hud_y = h - hud_h - 20 # start at bottom (960), step up by image height, and 20px for padding

        # 2. Draw the Figma Background first
        if hasattr(self, 'hud_bg') and self.hud_bg is not None:
            frame = self.overlay_transparent(frame, self.hud_bg, hud_x, hud_y)

        # Bar configuration
        bar_w = 270
        row_spacing = 56 # vertical gap between bars

        # bar coordinates (in hud)
        start_x = hud_x + 20
        start_y = hud_y + 40 #h - hud_h + 25 # vertical position for the bars
        
        hw = predictor.hardware_limits
        th = predictor.thresholds

        # Sensor values: Use a list to iterate through them easily
        sensors = [
            ("Water", sensor_data['water'], hw['water'][0], hw['water'][1], hw['water'][2], th['water_min'], th['water_max']),
            ("Light", sensor_data['light'], hw['light'][0], hw['light'][1], hw['light'][2], th['light_min'], th['light_max']),
            ("Temp", sensor_data['temp'], hw['temp'][0], hw['temp'][1], hw['temp'][2], th['temp_min'], th['temp_max']),
            ("Humid", sensor_data['humid'], hw['humid'][0], hw['humid'][1], hw['humid'][2], th['humid_min'], th['humid_max']) # standard min max
        ]

        # Sensor bars
        for i, (label, val, min_v, max_v, unit, safe_min, safe_max) in enumerate(sensors):
            y_pos = start_y + (i * row_spacing)
            self.draw_bar(frame, start_x, y_pos, val, min_v, max_v, unit, bar_w, safe_min, safe_max)

        return frame

    def draw_bar(self, frame, x, y, value, min_v, max_v, unit, width, safe_min, safe_max):
        height = 20 # thickness of colored bar
        label_spacing = 150

        # Calculate percentage
        percent = (value - min_v) / (max_v - min_v)
        percent = max(0, min(1, percent))
        
        # Draw Background Track
        bar_x = x + label_spacing
        # cv2.rectangle(frame, (bar_x, y), (bar_x + width, y + height), (80, 80, 80), -1)

        # Make it transparernt
        # Define the exact box coordinates
        x1, y1 = bar_x, y
        x2, y2 = bar_x + width, y + height
        
        # Safety check to ensure we don't draw off-screen
        if x1 >= 0 and y1 >= 0 and x2 <= frame.shape[1] and y2 <= frame.shape[0]:
            
            # Extract just the tiny slice of the image where the bar goes (ROI)
            roi = frame[y1:y2, x1:x2]
            
            # Create a solid grey block the exact same size as the ROI
            import numpy as np # Make sure this is imported at the top of your file!
            track_color = np.full(roi.shape, (80, 80, 80), dtype=np.uint8)
            
            # Blend them together (alpha = 0.4 means 40% opacity)
            alpha = 0.4
            cv2.addWeighted(track_color, alpha, roi, 1.0 - alpha, 0, roi)
        
        # Color logic: Changes accordingly
        if value < safe_min or value > safe_max: 
            color = (0, 0, 255) # Red for alert
        else: 
            color = (0, 255, 0) # Green for healthy
        
        # Draw Fill
        fill_w = int(width * percent)
        cv2.rectangle(frame, (bar_x, y), (bar_x + fill_w, y + height), color, -1)

        # Draw Value Text: On the RIGHT of the bar
        cv2.putText(frame, f"{value}{unit}", (bar_x + width + 10, y + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2) # size, color, thickness
    
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

            # ==========================================
            # DEBUG MODE: DRAW THE INVISIBLE HITBOXES
            # ==========================================
            # # Drawing a thin, bright magenta circle to represent the "fat finger" zone
            # cv2.circle(frame, self.current_leaf_btn, hitbox_radius, (255, 0, 255), 1) 
            # cv2.circle(frame, self.current_stem_btn, hitbox_radius, (255, 0, 255), 1) 

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

    # ==========================================
    # BLOCK 4: GROWTH PREDICTION LOGIC
    # ==========================================
    def overlay_transparent(self, background, overlay, x, y):
        """
        Overlays a transparent PNG (4 channels) onto a BGR background (3 channels)
        using optimized NumPy array broadcasting for Raspberry Pi performance.
        """
        bg_h, bg_w = background.shape[:2]
        ol_h, ol_w = overlay.shape[:2]

        # 1. Ignore if the overlay is completely off-screen
        if x >= bg_w or y >= bg_h or x + ol_w <= 0 or y + ol_h <= 0:
            return background

        # 2. Calculate safe bounding box coordinates for the background
        x1 = max(0, x)
        x2 = min(bg_w, x + ol_w)
        y1 = max(0, y)
        y2 = min(bg_h, y + ol_h)

        # 3. Calculate safe bounding box coordinates for the overlay image
        ol_x1 = max(0, -x)
        ol_x2 = min(ol_w, bg_w - x)
        ol_y1 = max(0, -y)
        ol_y2 = min(ol_h, bg_h - y)

        # 4. Extract the RGB channels and the Alpha channel
        overlay_crop = overlay[ol_y1:ol_y2, ol_x1:ol_x2]
        overlay_rgb = overlay_crop[:, :, :3]
        
        # Expand dims keeps the alpha mask in 3D shape (h, w, 1) for broadcasting
        alpha = overlay_crop[:, :, 3:4] / 255.0 

        # 5. Vectorized alpha blending math
        background_crop = background[y1:y2, x1:x2]
        background[y1:y2, x1:x2] = (alpha * overlay_rgb + (1.0 - alpha) * background_crop).astype(np.uint8)

        return background
    
    def draw_growth_overlay(self, frame, bbox, overlay_img, anim_progress):
        """
        Handles the math for animating, resizing, and anchoring the AR leaves.
        """
        # Safety check: ensure we have an image and a valid bounding box
        if overlay_img is None or len(bbox) != 4:
            return frame

        x, y, bw, bh = bbox

        # 1. Easing Math (Cubic ease-out)
        ease_p = 1.0 - (1.0 - anim_progress) ** 3

        # 2. Target Sizes
        orig_h, orig_w = overlay_img.shape[:2]
        aspect_ratio = orig_h / orig_w
        target_w = int(bw * 1.5)
        target_h = int(target_w * aspect_ratio)

        # 3. Apply animation progress (prevent 0-pixel crash)
        current_w = max(1, int(target_w * ease_p))
        current_h = max(1, int(target_h * ease_p))

        # 4. Resize
        resized_overlay = cv2.resize(overlay_img, (current_w, current_h), interpolation=cv2.INTER_AREA)

        # 5. Anchor Math (Align bottom-center)
        paste_x = int(x + (bw / 2) - (current_w / 2))
        paste_y = int(y + bh - current_h)

        # 6. Paint and return the frame
        return self.overlay_transparent(frame, resized_overlay, paste_x, paste_y)
    
    # ==========================================
    # BLOCK 5: CLIMATE STRESS SIMULATION LOGIC
    # ==========================================
    def apply_environment_filter(self, frame, mode):
        """Applies a fast, full-screen color tint based on the simulation mode."""
        overlay = np.zeros_like(frame, dtype=np.uint8)
        alpha = 0.25  # Opacity of the tint

        if mode == "TROPICAL":
            overlay[:] = (40, 200, 40)   # Green tint
            alpha = 0.15
        elif mode == "DESERT":
            overlay[:] = (0, 100, 255)   # Orange/Sand tint
        elif mode == "ARCTIC":
            overlay[:] = (255, 180, 100) # Ice Blue tint
        elif mode == "ACID_RAIN":
            overlay[:] = (100, 150, 150) # Murky Grey/Yellow
            alpha = 0.3

        # Blend the tint over the camera feed
        return cv2.addWeighted(frame, 1.0 - alpha, overlay, alpha, 0)