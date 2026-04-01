import time
import cv2
import numpy as np
from picamera2 import Picamera2

import config
import plant_measure
from core import vision
from ui_manager import UIManager
from core.particles import ParticleSystem
from core.growth import GrowthPredictor
from hardware import SensorManager

# ==========================================
# 1. HARDWARE & SYSTEM INITIALIZATION
# ==========================================

# Initialize the sensors
print("Waking up sensors...")
sensor = SensorManager(mock_mode=False) # <--- TOGGLE: True-mock, False-actual

# Initial reading - Grab the raw hardware dictionary
raw_initial_data = sensor.read_all()
# Give the DHT22 two seconds to warm up
time.sleep(2) 

# Map initial data so the UI doesn't crash on frame 1
sensor_values = {
    'temp': raw_initial_data['temperature'],
    'humid': raw_initial_data['humidity'],
    'light': int(raw_initial_data['light']),
    'water': raw_initial_data['soil_percent']
}

# Sensor polling setup
last_sensor_update = time.time()
sensor_interval = 2.0 # poll every 2 seconds

print(sensor_values)

# Turns on camera and loads calibration matrix
picam2 = Picamera2()
cam_config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(cam_config)
picam2.start()

# Loads camera calibration
with np.load('assets/camera_params.npz') as data:
    mtx, dist = data['mtx'], data['dist']

# Graphics tools & ArUco API setup
ps = ParticleSystem()
ui = UIManager()
predictor = GrowthPredictor()

# Load the AR assets with the IMREAD_UNCHANGED flag to preserve the Alpha channel
# Make sure to create an 'assets' folder in your project directory and put your PNGs there!
try:
    flower_img = cv2.imread('assets/flower.png', cv2.IMREAD_UNCHANGED)
    healthy_img = cv2.imread('assets/healthy-plant.png', cv2.IMREAD_UNCHANGED)
    wilting_img = cv2.imread('assets/wilted-plant.png', cv2.IMREAD_UNCHANGED)
    if healthy_img is None or wilting_img is None or flower_img is None:
        print("WARNING: Could not find PNG assets. Check your file paths.")
except Exception as e:
    print(f"Error loading assets: {e}")

detector = cv2.aruco.ArucoDetector(
    cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), 
    cv2.aruco.DetectorParameters()
)

current_mode = "MAIN"
DISPLAY_W = 1280 # global fallback for initial mouse clicks
DISPLAY_H = 960
growth_anim_progress = 0.0

# Simulation & Swipe State ---
sim_modes = ["TROPICAL", "DESERT", "ARCTIC", "ACID_RAIN"]
current_sim_idx = 0
is_simulating = False 
swipe_start_x = 0
swipe_threshold = 60 # Minimum pixels dragged to count as a swipe

# ==========================================
# 2. EVENT LISTENERS
# ==========================================

def on_mouse(event, x, y, flags, param):
    global current_mode, DISPLAY_W, DISPLAY_H, growth_anim_progress, swipe_start_x, current_sim_idx, sim_modes
    
    # ==========================================
    # THE TRANSLATION FIX
    # ==========================================
    # Shrink the 1280x960 mouse click down to the 640x480 original resolution
    original_frame_x = int(x / 2)
    original_frame_y = int(y / 2)

    # Handle mouse press
    if event == cv2.EVENT_LBUTTONDOWN:
        swipe_start_x = x

        # Check sidebar
        new_mode = ui.handle_click(x, y, DISPLAY_W, DISPLAY_H)
        if new_mode:
            if current_mode != new_mode:
                ps.particles = []

                if new_mode == "GROWTH" or new_mode == "SIMULATION":
                    growth_anim_progress = 0.0
            
            current_mode = new_mode
            if current_mode != "MICRO":
                ui.active_zoom_state = None 
            return # exit the function so users don't trigger AR buttons accidentally

        # Check AR buttons (only in MICRO mode)
        if current_mode == "MICRO":
            old_state = ui.active_zoom_state

            ui.check_ar_button_click(original_frame_x, original_frame_y)

            # If the user clicked a different button (e.g., changed from WATER to GAS)
            if ui.active_zoom_state != old_state:
                # Instantly clear the physics engine's memory!
                ps.particles = [] 

    # Handle mouse release
    elif event == cv2.EVENT_LBUTTONUP:
        # Only calculate swipes if we are currently in the simulation screen
        if current_mode == "SIMULATION":
            delta_x = x - swipe_start_x
            swipe_threshold = 60 # Pixels moved to trigger a swipe
            
            if abs(delta_x) > swipe_threshold:
                if delta_x > 0:
                    # Swiped Right -> Previous
                    current_sim_idx = (current_sim_idx - 1) % len(sim_modes)
                else:
                    # Swiped Left -> Next
                    current_sim_idx = (current_sim_idx + 1) % len(sim_modes)
                
                # Reset animation and particles for the new environment transition
                growth_anim_progress = 0.0 
                ps.particles = [] 
                
                print(f"Swiped! New Environment: {sim_modes[current_sim_idx]}")


cv2.namedWindow("AR Science Lab", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("AR Science Lab", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("AR Science Lab", on_mouse)

print("AR Science Project: SYSTEM LIVE")

# ==========================================
# 3. MAIN EXECUTION LOOP
# ==========================================

marker_last_seen_time = time.time()
SEARCH_TIMEOUT = 0.5 # Wait half a second before showing the "Searching" text

try:
    while True:
        # A. INPUT: Grab frame from camera
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame_h, frame_w, frame_c = frame_bgr.shape
        w = frame_w # use a global w for the mouse callback

        # B. REST FRAME VARIABLES: Clears out data once plant moved away
        bbox = None
        height = None
        success = None

        # C. SENSOR POLLING: Ensures hardware data is read every 2 seconds
        current_time = time.time()
        
        if (current_time - last_sensor_update) >= sensor_interval:
            
            # Grab the live dictionary of raw environmental data
            raw_data = sensor.read_all()
        
            # 2. Map the new keys to your old predictor keys
            sensor_values['temp'] = raw_data['temperature']
            sensor_values['humid'] = raw_data['humidity']
            sensor_values['light'] = int(raw_data['light'])
            sensor_values['water'] = raw_data['soil_percent']

            # Reset timer
            last_sensor_update = current_time

        # D. COMPUTER VISION PROCESSING: Get ratio and height
        corners, ids, rejected = detector.detectMarkers(frame_bgr)

        if ids is not None: # if marker is present
            # Update stopwatch when plant is seen
            marker_last_seen_time = time.time()
            
            # Runs green mask to find plant's shape
            mask = vision.get_green_mask(frame_bgr, config.LOWER_GREEN, config.UPPER_GREEN)
            ratio = plant_measure.calculate_ratio(corners, config.ARUCO_MARKER_SIZE)
            height, bbox = plant_measure.calculate_plant_height(mask, ratio) 

            ui.update_stable_bbox(bbox)          
            
            # 3D pose for particles
            success, rvec, tvec = plant_measure.get_pose(
                corners, 
                mtx, 
                dist,
                config.ARUCO_MARKER_SIZE)

            if height and bbox is not None:
                # Use the bbox to draw the rectangle
                bbox_x, bbox_y, bbox_w, bbox_h = bbox
                #cv2.rectangle(frame_bgr, (bbox_x, bbox_y), (bbox_x + bbox_w, bbox_y + bbox_h), (0, 255, 0), 2)
                real_height = plant_measure.calculate_height_from_marker(corners, bbox_y, ratio)
                
                # print(f"Plant is {height:.2f} cm tall")
                # print(f"Height from ground is {real_height:.2f} cm")
            
                # E. STATE MACHINE LOGIC
                # Uses 3D coordinates to emit and render animated physics particles for water and gas
                if current_mode == "MAIN":
                    
                    print("--- DEBUG: Inside Main Photosynthesis Mode ---")
                        
                    if success:
                        # Animation emit based on height/state 
                        right_edge = (w / 2) * ratio
                        left_edge = -right_edge

                        # Grab all current environment data
                        current_water = sensor_values['water']
                        current_light = sensor_values['light']
                        current_temp = sensor_values['temp']
                        current_humid = sensor_values['humid']
                        
                        # Grab the safe thresholds from your predictor
                        water_min = predictor.thresholds['water_min']
                        water_max = predictor.thresholds['water_max']
                        light_min = predictor.thresholds['light_min']
                        light_max = predictor.thresholds['light_max']
                        temp_min = predictor.thresholds['temp_min']
                        temp_max = predictor.thresholds['temp_max']
                        humid_min = predictor.thresholds['humid_min']
                        humid_max = predictor.thresholds['humid_max']

                        # Advance the animation state
                        if growth_anim_progress < 1.0:
                            growth_anim_progress += 0.05 
                        else:
                            growth_anim_progress = 1.0

                        if water_min <= current_water <= water_max:
                            # water flows up
                            ps.emit(origin_3d=[0, config.ARUCO_MARKER_SIZE/2, 3], p_type="water", target_height=real_height-6, count=1)
                        
                        is_photosynthesizing = (
                            (water_min <= current_water <= water_max) and 
                            (light_min <= current_light <= light_max) and 
                            (temp_min <= current_temp <= temp_max) and 
                            (humid_min <= current_humid <= humid_max)
                        )
                        
                        if is_photosynthesizing:
                            # oxygen out
                            ps.emit(origin_3d=[right_edge/2, config.ARUCO_MARKER_SIZE/2, real_height], p_type="oxygen", target_height=0, count=1)
                            # co2 in
                            ps.emit(origin_3d=[left_edge/2, config.ARUCO_MARKER_SIZE/2, real_height], p_type="co2", target_height=0, count=1)
                           
                            # produce flower
                            if flower_img is not None and ui.stable_bbox is not None:
                                # A. Unpack the original plant bounding box
                                bx, by, bw, bh = ui.stable_bbox
                                
                                # B. Set your scale multiplier (0.4 = 40% of plant width)
                                scale_multiplier = 0.4
                                
                                # C. Calculate the new width and proportional height
                                flower_w = int(bw * scale_multiplier)
                                aspect_ratio = flower_img.shape[0] / flower_img.shape[1]
                                flower_h = int(flower_w * aspect_ratio)
                                
                                # D. Calculate the perfect top-center position
                                flower_x = int(bx + (bw / 2) - (flower_w / 2))
                                
                                # Position it right at the top of the plant (by), 
                                # and nudge it up slightly by subtracting a little height
                                flower_y = int(by) #  by - (flower_h / 4) to nudge flower up
                                
                                # E. Pack it into a new tuple
                                flower_bbox = (flower_x, flower_y, flower_w, flower_h)

                                frame_bgr = ui.draw_growth_overlay(frame_bgr, flower_bbox, flower_img, growth_anim_progress)

                        else:
                            # Optional: what if photosynthesis stops?
                            pass

                        # Draw AR elements
                        ps.update_and_draw(frame_bgr, mtx, dist, rvec, tvec)
                        cv2.drawFrameAxes(frame_bgr, mtx, dist, rvec, tvec, 0.03)

                        # print(f"Frame size: {frame_bgr.shape[1]}x{frame_bgr.shape[0]}, Menu Width: {ui.menu_width}")

                # Projects interactive AR nodes onto bbox coordinates
                elif current_mode == "MICRO":
                    print("--- DEBUG: Inside Microscope Mode ---")

                    # Only call the zoom function if a plant (bbox) is actually seen
                    if len(bbox) == 4:
                        # Keep a clean copy for the zoom crop (avoid capturing UI overlays)
                        clean_frame = frame_bgr.copy()
                        ui.draw_ar_buttons(frame_bgr, bbox)
                    
                        # Emit particles based on button click
                        if ui.active_zoom_state == "WATER":
                            # Start at ArUco marker (0, y_offset, 3) and flow up to real_height
                            ps.emit(origin_3d=[0, config.ARUCO_MARKER_SIZE/2, 3], p_type="water", target_height=real_height, count=1)
                            
                        elif ui.active_zoom_state == "GAS":
                            # Target the center of the upper canopy
                            canopy_center_x = 0  # Centered directly above the ArUco marker
                            canopy_center_z = real_height * 0.95  # 95% up the plant's height
                            
                            # Emit MICRO Oxygen (Spawns at center, flows OUT)
                            ps.emit(origin_3d=[canopy_center_x, config.ARUCO_MARKER_SIZE/2, canopy_center_z], p_type="micro_o2", count=1)
                            
                            # Emit MICRO CO2 (Spawns away from center, flows IN)
                            ps.emit(origin_3d=[canopy_center_x, config.ARUCO_MARKER_SIZE/2, canopy_center_z], p_type="micro_co2", count=1)

                        # Draw the 3d particles onto main frame
                        if ui.active_zoom_state is not None:
                            # Updates the physics and paints the particles onto the clean_frame
                            ps.update_and_draw(clean_frame, mtx, dist, rvec, tvec)

                            # Crop and magnify (This will now capture the particles just drawn)
                            ui.draw_zoom_window(frame_bgr, ui.stable_bbox, ui.active_zoom_state, source_frame=clean_frame)

                elif current_mode == "GROWTH":
                    print("--- DEBUG: Inside Growth Mode ---")

                    if len(bbox) == 4:
                        x, y, bw, bh = map(int, ui.stable_bbox)
                        
                        # 1. Ask the expert system for the prediction
                        health_state, diagnosis = predictor.predict_health(sensor_values)
                        
                        # 2. Select the correct asset and text color
                        if health_state == "HEALTHY":
                            overlay_img = healthy_img
                            text_color = (0, 255, 0)
                        else:
                            overlay_img = wilting_img
                            text_color = (0, 0, 255)

                        # 3. Advance the animation state
                        if growth_anim_progress < 1.0:
                            growth_anim_progress += 0.05 
                        else:
                            growth_anim_progress = 1.0

                        # 4. Paint the AR overlay onto the main frame
                        frame_bgr = ui.draw_growth_overlay(frame_bgr, ui.stable_bbox, overlay_img, growth_anim_progress)

                        # # 3. Dynamic Scaling 
                        # # Only proceed if the image loaded successfully
                        # if overlay_img is not None:
                        #     orig_h, orig_w = overlay_img.shape[:2]
                        #     aspect_ratio = orig_h / orig_w
                            
                        #     # Make the canopy slightly wider than the plant's bounding box
                        #     new_w = int(bw * 1.5) 
                        #     new_h = int(new_w * aspect_ratio)
                            
                        #     # Resize the PNG
                        #     resized_overlay = cv2.resize(overlay_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

                        #     # 4. Anchor Point Math (Align bottom-center)
                        #     # Center it horizontally over the plant
                        #     paste_x = int(x + (bw / 2) - (new_w / 2))
                        #     # Align the bottom of the PNG with the bottom of the bounding box
                        #     paste_y = int(y + bh - new_h)

                            # # 5. Paint the AR overlay onto the main frame
                            # frame_bgr = ui.overlay_transparent(frame_bgr, resized_overlay, paste_x, paste_y)

                        # 5. Draw the educational diagnosis text right above the plant
                        cv2.putText(frame_bgr, f"Prediction: {health_state}", (x, max(20, y - 40)), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
                        cv2.putText(frame_bgr, f"Cause: {diagnosis}", (x, max(45, y - 15)), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

                elif current_mode == "SIMULATION":
                    print("--- DEBUG: Inside Climate Simulation Mode ---")

                    active_env = sim_modes[current_sim_idx]
                    
                    # 1. Apply the visual atmosphere
                    frame_bgr = ui.apply_environment_filter(frame_bgr, active_env)
                    
                    # 2. Draw the environment title
                    cv2.putText(frame_bgr, f"ENVIRONMENT: {active_env}", (20, 50), 
                                cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(frame_bgr, "< SWIPE TO EXPLORE >", (20, 80), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

                    # 3. Simulate the Plant's Reaction
                    if ui.stable_bbox is not None:
                        leaf_asset = healthy_img if active_env == "TROPICAL" else wilting_img
                            
                        # Advance the animation state
                        if growth_anim_progress < 1.0:
                            growth_anim_progress += 0.05 
                        else:
                            growth_anim_progress = 1.0
                        
                        # Draw the actual plant overlay
                        frame_bgr = ui.draw_growth_overlay(frame_bgr, ui.stable_bbox, leaf_asset, growth_anim_progress)

                    # 4. Trigger the wheather particles
                    ps.spawn_weather(w, active_env)
                        
                    # Draw the AR overlay using the function we built earlier
                    frame_bgr = ps.update_and_draw(frame_bgr, mtx, dist, rvec, tvec)

        else: # if marker is missing
            # Check the stopwatch to see if it has been missing for more than 0.5 seconds
            if time.time() - marker_last_seen_time > SEARCH_TIMEOUT:
                print("--- DEBUG: No plant detected! ---")
                ui.draw_notification(frame_bgr, "Point camera at pot to see the plant!")
                ui.stable_bbox = None

        # F. RENDER UI LAYERS: drawn last to stay on top
        
        frame_hd = cv2.resize(frame_bgr, (1280, 960), interpolation=cv2.INTER_LINEAR)
        frame_hd = ui.draw_hud(frame_hd, sensor_values, predictor)
        frame_hd = ui.draw_sidebar(frame_hd, current_mode)
        cv2.imshow("AR Science Lab", frame_hd)

        # This line is REQUIRED for the window to actually refresh
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()