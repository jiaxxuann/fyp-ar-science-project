import cv2
import numpy as np
from picamera2 import Picamera2
import time

# --- 1. Load Calibration ---
with np.load('assets/camera_params.npz') as data:
    mtx, dist = data['mtx'], data['dist']

# --- 2. Setup ArUco (Legacy) ---
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()
MARKER_SIZE = 0.01  # 1cm

def draw_cube(img, rvec, tvec, mtx, dist):
    """Draws a 3D wireframe cube on the marker."""
    s = MARKER_SIZE / 2
    # Define 8 corners of a cube (X, Y, Z)
    # The base is at Z=0, the top is at Z=-MARKER_SIZE
    axis_points = np.float32([
        [-s,  s, 0], [ s,  s, 0], [ s, -s, 0], [-s, -s, 0], # Base
        [-s,  s, MARKER_SIZE], [ s,  s, MARKER_SIZE],     # Top
        [ s, -s, MARKER_SIZE], [-s, -s, MARKER_SIZE]
    ])

    # Project 3D points to 2D image pixels
    imgpts, _ = cv2.projectPoints(axis_points, rvec, tvec, mtx, dist)
    imgpts = np.int32(imgpts).reshape(-1, 2)

    # Draw bottom layer (Green)
    img = cv2.drawContours(img, [imgpts[:4]], -1, (0, 255, 0), 2)
    # Draw pillars (Blue)
    for i, j in zip(range(4), range(4, 8)):
        img = cv2.line(img, tuple(imgpts[i]), tuple(imgpts[j]), (255, 0, 0), 2)
    # Draw top layer (Red)
    img = cv2.drawContours(img, [imgpts[4:]], -1, (0, 0, 255), 2)
    return img

# --- 3. Main Loop ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

try:
    while True:
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        corners, ids, _ = cv2.aruco.detectMarkers(frame_bgr, aruco_dict, parameters=parameters)

        if ids is not None:
            s = MARKER_SIZE / 2
            obj_points = np.array([[-s, s, 0], [s, s, 0], [s, -s, 0], [-s, -s, 0]], dtype=np.float32)
            for i in range(len(ids)):
                _, rvec, tvec = cv2.solvePnP(obj_points, corners[i], mtx, dist)
                frame_bgr = draw_cube(frame_bgr, rvec, tvec, mtx, dist)

        cv2.imshow("Science AR - 3D Cube", frame_bgr)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
finally:
    picam2.stop()
    cv2.destroyAllWindows()