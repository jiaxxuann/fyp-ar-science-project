import cv2
import numpy as np
from picamera2 import Picamera2

import config
import plant_measure
from core import vision
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

print("AR Science Project: SYSTEM LIVE")

try:
    while True:
        # A. INPUT: Grab frame
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # B. VISION LOGIC: Find the plant
        mask = vision.get_green_mask(frame_bgr, config.LOWER_GREEN, config.UPPER_GREEN)

        # C. MEASUREMENT: Get ratio and height
        corners, ids, rejected = detector.detectMarkers(frame_bgr)
        
        if ids is not None:
            # Calculate real-world scale
            ratio = plant_measure.calculate_ratio(corners, config.ARUCO_MARKER_SIZE)
            height, bbox = plant_measure.calculate_plant_height(mask, ratio)            
            
            if height:
                # Use the bbox to draw the rectangle
                x, y, w, h = bbox
                cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), (0, 255, 0), 2)
                           
                print(f"Plant is {height:.2f} cm tall")

                real_height = plant_measure.calculate_height_from_marker(corners, y, ratio)
                print(f"Height from ground is {real_height:.2f} cm")

            # 3D pose for particles
            success, rvec, tvec = plant_measure.get_pose(
                corners, 
                mtx, 
                dist,
                config.ARUCO_MARKER_SIZE)
            
            if success:
                if height:
                    right_edge = (w / 2) * ratio
                    left_edge = -right_edge
                
                    #D. ANIMATION: Emit based on height/state 
                    ps.emit(origin_3d=[0, config.ARUCO_MARKER_SIZE/2, 3], p_type="water", target_height=real_height-6, count=1)
                    ps.emit(origin_3d=[right_edge/2, config.ARUCO_MARKER_SIZE/2, real_height], p_type="oxygen", target_height=0, count=1)
                    ps.emit(origin_3d=[left_edge/2, config.ARUCO_MARKER_SIZE/2, real_height], p_type="co2", target_height=0, count=1)

                    #E. DRAW AR ELEMENTS
                    ps.update_and_draw(frame_bgr, mtx, dist, rvec, tvec)
                    cv2.drawFrameAxes(frame_bgr, mtx, dist, rvec, tvec, 0.03)

        # F. DISPLAY
        cv2.imshow("Bio-AR Growth Monitor", frame_bgr)

        # This line is REQUIRED for the window to actually refresh
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()