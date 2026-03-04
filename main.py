import cv2
import numpy as np
from picamera2 import Picamera2

import config
import plant_measure
from core import vision
from ui_manager import UIManager
from core.particles import ParticleSystem  # Our new parameterized system

# 1. INITIALIZATION
picam2 = Picamera2()
cam_config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(cam_config)
picam2.start()

# Load Camera Calibration
with np.load('assets/camera_params.npz') as data:
    mtx, dist = data['mtx'], data['dist']

# Setup Graphics Tools & ArUco API
ps = ParticleSystem()
detector = cv2.aruco.ArucoDetector(
    cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), 
    cv2.aruco.DetectorParameters()
)

ui = UIManager()
current_mode = "MAIN"

def on_mouse(event, x, y, flags, param):
    global current_mode
    if event == cv2.EVENT_LBUTTONDOWN:
        new_mode = ui.handle_click(x, y, w)
        if new_mode:
            current_mode = new_mode

cv2.namedWindow("AR Science Lab", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("AR Science Lab", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("AR Science Lab", on_mouse)

print("AR Science Project: SYSTEM LIVE")

try:
    while True:
        # A. INPUT: Grab frame
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        h, w, c = frame_bgr.shape
        #print(frame_bgr.shape)
        
        # B. VISION LOGIC: Find the plant
        mask = vision.get_green_mask(frame_bgr, config.LOWER_GREEN, config.UPPER_GREEN)

        # C. MEASUREMENT: Get ratio and height
        corners, ids, rejected = detector.detectMarkers(frame_bgr)

        # D. SENSOR: Update sensor readings
        sensor_values = {
            'water': 800, #hardware.get_moisture(),
            'light': 500, #hardware.get_lux(),
            'temp': 15, #hardware.get_temp(),
            'hum': 2 #hardware.get_humidity()
        }

        if ids is None:
            # Marker and bbox are missing
            print("--- DEBUG: No plant detected! ---")
            cv2.putText(frame_bgr, "Point camera at pot to see the plant!", (10, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        if ids is not None:
            # Calculate real-world scale
            ratio = plant_measure.calculate_ratio(corners, config.ARUCO_MARKER_SIZE)
            height, bbox = plant_measure.calculate_plant_height(mask, ratio)            
            # 3D pose for particles
            success, rvec, tvec = plant_measure.get_pose(
                corners, 
                mtx, 
                dist,
                config.ARUCO_MARKER_SIZE)
            
            # find camera width in cm
            # frame_width_cm = 680 * ratio
            # print(f"The camera is currently seeing an area {frame_width_cm:.2f} cm wide")

            if height:
                # Use the bbox to draw the rectangle
                bbox_x, bbox_y, bbox_w, bbox_h = bbox
                cv2.rectangle(frame_bgr, (bbox_x, bbox_y), (bbox_x + bbox_w, bbox_y + bbox_h), (0, 255, 0), 2)
                        
                print(f"Plant is {height:.2f} cm tall")

                real_height = plant_measure.calculate_height_from_marker(corners, bbox_y, ratio)
                print(f"Height from ground is {real_height:.2f} cm")
            
            if current_mode == "MAIN":
                
                print("--- DEBUG: Inside Main Photosynthesis Mode ---")
                    
                if success and height:
                    #E. ANIMATION: Emit based on height/state 
                    right_edge = (w / 2) * ratio
                    left_edge = -right_edge

                    ps.emit(origin_3d=[0, config.ARUCO_MARKER_SIZE/2, 3], p_type="water", target_height=real_height-6, count=1)
                    ps.emit(origin_3d=[right_edge/2, config.ARUCO_MARKER_SIZE/2, real_height], p_type="oxygen", target_height=0, count=1)
                    ps.emit(origin_3d=[left_edge/2, config.ARUCO_MARKER_SIZE/2, real_height], p_type="co2", target_height=0, count=1)

                    #F. DRAW AR ELEMENTS
                    ps.update_and_draw(frame_bgr, mtx, dist, rvec, tvec)
                    cv2.drawFrameAxes(frame_bgr, mtx, dist, rvec, tvec, 0.03)

                    print(f"Frame size: {frame_bgr.shape[1]}x{frame_bgr.shape[0]}, Menu Width: {ui.menu_width}")

            elif current_mode == "MICRO":
                print("--- DEBUG: Inside Microscope Mode ---")
            elif current_mode == "GROWTH":
                print("--- DEBUG: Inside Growth Mode ---")

            elif current_mode == "CLIMATE":
                print("--- DEBUG: Inside CLimate Simulation Mode ---")

        # G. DISPLAY
        # UI drawn last to ensure its on top of everything else
        ui.draw_hud(frame_bgr, sensor_values)

        ui.draw_sidebar(frame_bgr, current_mode) 

        cv2.imshow("AR Science Lab", frame_bgr)

        # This line is REQUIRED for the window to actually refresh
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()