import cv2
import numpy as np
from picamera2 import Picamera2
import time

# --- 1. Load Calibration Data ---
try:
    with np.load('camera_params.npz') as data:
        mtx = data['mtx']
        dist = data['dist']
    print("Calibration data loaded successfully.")
except:
    print("Error: 'camera_params.npz' not found. Run calibration first!")
    exit()

# --- 2. Setup ArUco ---
# We use the 4x4 dictionary (matches most printed markers)
aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters_create()

# The physical size of your marker in meters (e.g., 5cm = 0.05)
MARKER_SIZE = 0.01

# --- 3. Setup Camera (Picamera2 Backend) ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()
time.sleep(2)

print("AR Detection Started. Press 'q' to quit.")

try:
    while True:
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Detect markers
        corners, ids, rejected = cv2.aruco.detectMarkers(frame_bgr, aruco_dict, parameters=parameters)
        
        if ids is not None:
            # Estimate pose for each marker
            # This calculates where the marker is in 3D space
            obj_points = np.array([[-MARKER_SIZE/2,  MARKER_SIZE/2, 0],
                                   [ MARKER_SIZE/2,  MARKER_SIZE/2, 0],
                                   [ MARKER_SIZE/2, -MARKER_SIZE/2, 0],
                                   [-MARKER_SIZE/2, -MARKER_SIZE/2, 0]], dtype=np.float32)

            for i in range(len(ids)):
                # SolvePnP finds the Rotation and Translation vectors
                _, rvec, tvec = cv2.solvePnP(obj_points, corners[i], mtx, dist)
                
                # Draw the markers and the 3D axes
                cv2.aruco.drawDetectedMarkers(frame_bgr, corners)
                cv2.drawFrameAxes(frame_bgr, mtx, dist, rvec, tvec, 0.03) 
                
                # Print distance (tvec[2] is the Z-axis / distance from camera)
                distance = tvec[2][0]
                cv2.putText(frame_bgr, f"Dist: {distance:.2f}m", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("AR Science Tool - Test", frame_bgr)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()