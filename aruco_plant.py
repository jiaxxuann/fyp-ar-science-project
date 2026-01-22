import cv2
import numpy as np
from picamera2 import Picamera2
import time
import math
from core.entities import WaterSystem

# --- 1. Load Calibration ---
with np.load('assets/camera_params.npz') as data:
    mtx, dist = data['mtx'], data['dist']

# --- 2. Setup ArUco (Legacy) ---
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()
MARKER_SIZE = 0.01  # 1cm

def draw_plant(img, rvec, tvec, mtx, dist):
    """Draws a 3D wireframe cube on the marker."""
    s = MARKER_SIZE / 2
    # Define 3D points of plant skeleton
    plant_skeleton = np.float32([
        [0, 0, 0],          # Point 0: The Root (Center of marker)
        [0, 0, 0.01],        # Point 1: Top of Stem (10 units up)
        [-0.003, 0, 0.005],        # Point 2: Left Leaf tip
        [0.003, 0, 0.007]          # Point 3: Right Leaf tip
    ]).reshape(-1, 3)

    # 1. Project points
    imgpts, _ = cv2.projectPoints(plant_skeleton, rvec, tvec, mtx, dist)
    
    # 2. Extract and cast to INT immediately
    # We use .ravel() to flatten and int() to be 100% sure of the type
    try:
        # Root
        rx, ry = imgpts[0].ravel()
        root = (int(rx), int(ry))
        
        # Tip
        tx, ty = imgpts[1].ravel()
        tip = (int(tx), int(ty))
        
        # Left Leaf
        llx, lly = imgpts[2].ravel()
        leaf_l = (int(llx), int(lly))
        
        # Right Leaf
        lrx, lry = imgpts[3].ravel()
        leaf_r = (int(lrx), int(lry))

        # 4. Calculate Midpoint
        mid_stem = (int((root[0] + tip[0]) / 2), int((root[1] + tip[1]) / 2))

        # 5. Draw
        cv2.line(img, root, tip, (0, 255, 0), 3)
        cv2.line(img, mid_stem, leaf_l, (0, 200, 0), 2)
        cv2.line(img, mid_stem, leaf_r, (0, 200, 0), 2)
        
    except Exception as e:
        print(f"Drawing error: {e}")
    
    # Draw small circles at the leaf tips
    #cv2.circle(img, leaf_l, 5, (0, 255, 0), -1)
    #cv2.circle(img, leaf_r, 5, (0, 255, 0), -1)
    
    return img

def draw_cylindrical_stem(img, rvec, tvec, mtx, dist, radius=0.005, height=0.1):
    num_segments = 10  # 8 points makes a hexagonal-looking tube
    points_3d = []
    
    # 1. Create the base and top circles
    for i in range(num_segments + 1):
        angle = 2 * math.pi * i / num_segments
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        
        points_3d.append([x, y, 0])      # Base point
        points_3d.append([x, y, height]) # Corresponding Top point

    points_3d = np.array(points_3d, dtype=np.float32)

    # 2. Project all points
    imgpts, _ = cv2.projectPoints(points_3d, rvec, tvec, mtx, dist)
    imgpts = imgpts.astype(int)

    # 3. Draw the cylinder
    for i in range(0, (num_segments * 2), 2):
        # Define the 4 corners of the panel
        # We use .reshape(-1, 2) to ensure the shape is correct for OpenCV
        panel = np.array([
            imgpts[i],      # Current Base
            imgpts[i+1],    # Current Top
            imgpts[i+3],    # Next Top
            imgpts[i+2]     # Next Base
        ], dtype=np.int32)

        # LIGHTING TRICK: Change color slightly per panel
        # This makes it look 3D instead of a flat green block
        green_val = 100 + (i * 5) % 100 
        color = (0, green_val, 0)

        # Fill the shape
        #cv2.fillConvexPoly(img, panel, color)
        
        # Optional: Add a subtle outline to define the edges
        cv2.polylines(img, [panel], True, (0, 60, 0), 1)

    return img

water_system = WaterSystem(num_particles=12)

# --- 3. Main Loop ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

current_height = 0.01
try:
    while True:
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        corners, ids, _ = cv2.aruco.detectMarkers(frame_bgr, aruco_dict, parameters=parameters)
        
        # update height
        key = cv2.waitKey(1) & 0xFF
        if key == ord('u'): # 'u' for Up (Taller)
            current_height += 0.005
        elif key == ord('d'): # 'd' for Down (Shorter)
            current_height -= 0.005
        elif key == ord('q'):
            break

        if ids is not None:
            s = MARKER_SIZE / 2
            obj_points = np.array([[-s, s, 0], [s, s, 0], [s, -s, 0], [-s, -s, 0]], dtype=np.float32)
        
            for i in range(len(ids)):
                _, rvec, tvec = cv2.solvePnP(obj_points, corners[i], mtx, dist)
                frame_bgr = draw_cylindrical_stem(frame_bgr, rvec, tvec, mtx, dist, radius=0.005, height=current_height)
                
                water_system.update(current_height)
                water_system.draw(frame_bgr, rvec, tvec, mtx, dist)
            
        cv2.imshow("Science AR - 3D Plant", frame_bgr)
        
        # Check for 'q' key AND don't let the window hang
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        
except KeyboardInterrupt:
    print("\nSession interrupted by user (Ctrl+C)")
    
finally:
    print("Cleaning up...")
    picam2.stop()
    cv2.destroyAllWindows()
    # Adding a small sleep helps the OS release the window
    for i in range(5):
        cv2.waitKey(1)
