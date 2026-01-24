import cv2

def get_green_mask(frame_bgr, lower_green, upper_green):
    """
    Converts BGR to HSV and creates a binary mask of green areas.
    """
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    
    # Create the mask based on config values
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # Optional: Clean up noise (Morphological operations)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    return mask