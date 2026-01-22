import numpy as np
import cv2
import random
import math

class WaterSystem:
    def __init__(self, num_particles=15):
        # Initialize particles at random Z positions between 0 and -0.1
        self.particles = [[0, 0, random.uniform(-0.1, 0)] for _ in range(num_particles)]
        self.speed = 0.002

    def update(self, target_height):
        for p in self.particles:
            p[2] += self.speed  # Move Up (OpenCV Z is negative for 'up')
            
            # Reset to bottom if it reaches the tip
            # We use target_height (e.g., -0.05) to know where to loop
            if p[2] >= target_height:
                p[2] = 0

    def draw(self, img, rvec, tvec, mtx, dist):
        if not self.particles: return
        
        # Project all 3D particles to 2D screen points
        pts_3d = np.array(self.particles, dtype=np.float32)
        imgpts, _ = cv2.projectPoints(pts_3d, rvec, tvec, mtx, dist)
        
        for pt in imgpts:
            x, y = pt.ravel()
            # Draw a glowing blue drop
            cv2.circle(img, (int(x), int(y)), 3, (255, 150, 50), -1) # BGR: Light Blue