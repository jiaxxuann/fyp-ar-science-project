import cv2
import numpy as np

def calculate_ratio(corners, real_marker_size):
    """
    Calculates the pixel-to-cm ratio based on the ArUco marker width.
    """
    # Distance between top-left (0) and top-right (1) corners
    marker_px_width = np.linalg.norm(corners[0][0][0] - corners[0][0][1])
    
    if marker_px_width > 0:
        return real_marker_size / marker_px_width
    return None

def calculate_plant_height(mask, ratio):
    """
    Finds the largest green object and converts its pixel height to cm.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        largest_cnt = max(contours, key=cv2.contourArea)
        # Filter for noise (only process if the object is significant)
        if cv2.contourArea(largest_cnt) > 500:
            x, y, w, h_px = cv2.boundingRect(largest_cnt)
            actual_height = h_px * ratio
            return actual_height, (x, y, w, h_px)
            
    return None, None

def calculate_height_from_marker(corners, bbox_top_y, pixel_to_cm_ratio):
    """
    Calculates height from the ArUco marker surface to the top of the plant.
    """
    # 1. Find the center Y coordinate of the ArUco marker
    # We average the Y coordinates of all 4 corners
    marker_y_center = np.mean([c[1] for c in corners[0]])
    
    # 2. Calculate pixel distance from marker center to plant top
    # In OpenCV, Y increases downwards, so (Marker Y - Top Y) = Height
    height_px = marker_y_center - bbox_top_y
    
    # 3. Convert to cm
    actual_height_cm = height_px * pixel_to_cm_ratio
    
    return max(0, actual_height_cm) # Ensure we don't return negative height

def get_pose(corners, mtx, dist, marker_size):
    """
    Performs 3D Pose Estimation to find where the marker is in space.
    Needed for the 3D particle system and axes.
    """
    # Define the 3D coordinates of the marker corners in the real world
    L = marker_size
    obj_points = np.array([
        [-L/2,  L/2, 0],
        [ L/2,  L/2, 0],
        [ L/2, -L/2, 0],
        [-L/2, -L/2, 0]
    ], dtype=np.float32)
    
    success, rvec, tvec = cv2.solvePnP(obj_points, corners[0], mtx, dist)
    return success, rvec, tvec