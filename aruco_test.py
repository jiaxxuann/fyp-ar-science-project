import cv2
import numpy as np
from picamera2 import Picamera2
import time
import config

# --- 1. Load Calibration Data ---
try:
    with np.load('assets/camera_params.npz') as data:
        mtx = data['mtx']
        dist = data['dist']
    print("Calibration data loaded successfully.")
except:
    print("Error: 'camera_params.npz' not found. Run calibration first!")
    exit()

# --- 2. Setup ArUco ---
# We use the 4x4 dictionary (matches most printed markers)
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()

# --- 3. Setup Camera (Picamera2 Backend) ---
picam2 = Picamera2()
cam_config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(cam_config)
picam2.start()
time.sleep(2)

print("AR Detection Started. Press 'q' to quit.")

# Estimate pose for each marker
# This calculates where the marker is in 3D space
MARKER_SIZE = config.ARUCO_MARKER_SIZE
obj_points = np.array([[-MARKER_SIZE/2,  MARKER_SIZE/2, 0],
                        [ MARKER_SIZE/2,  MARKER_SIZE/2, 0],
                        [ MARKER_SIZE/2, -MARKER_SIZE/2, 0],
                        [-MARKER_SIZE/2, -MARKER_SIZE/2, 0]], 
                        dtype=np.float32)

try:
    while True:
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Detect markers
        corners, ids, rejected = cv2.aruco.detectMarkers(frame_bgr, aruco_dict, parameters=parameters)
        
        if ids is not None:
            for i in range(len(ids)):
                # SolvePnP finds the Rotation and Translation vectors
                _, rvec, tvec = cv2.solvePnP(obj_points, corners[i], mtx, dist)
                
                # Draw the markers and the 3D axes
                cv2.aruco.drawDetectedMarkers(frame_bgr, corners)
                cv2.drawFrameAxes(frame_bgr, mtx, dist, rvec, tvec, 0.03) 
                
                # Calculate distance (Z-axis in tvec)
                # tvec is (x, y, z) coordinates of the marker center
                distance_m = tvec[2][0] 
                
                # Display the distance on screen
                text = f"ID: {ids[i][0]} Dist: {distance_m:.2f}m"
                cv2.putText(frame_bgr, text, (int(corners[i][0][0][0]), int(corners[i][0][0][1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("AR Science Tool - Test", frame_bgr)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()