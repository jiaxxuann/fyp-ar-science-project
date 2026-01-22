import config

def calculate_height(plant_pixels, marker_pixels):
    # find the ratio: real size / pixel size of marker
    pixels_to_cm = config.ARUCO_MARKER_SIZE / marker_pixels
    
    # multiply plant's pixel height by that ratio
    plant_height_cm = plant_pixels * pixels_to_cm
    
    return plant_height_cm