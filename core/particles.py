import numpy as np
import random
import cv2

class Particle:
    def __init__(self, origin_3d, p_type, target_height=0):
        # 3D Position (relative to the ArUco marker)
        self.pos_3d = np.array(origin_3d, dtype=np.float32)
        self.p_type = p_type
        self.life = 1.0

        # Define type-specific behaviors
        if p_type == "water":
            speed = 0.7

            self.color = (255, 100, 0) # Blue (BGR)
            self.vel_3d = np.array([0, 0, speed]) # Rises from root
            if target_height > 0:
                self.decay = speed / target_height
            else:
                self.decay = 0.05

        elif p_type == "oxygen":
            speed = 0.05

            self.color = (255, 255, 255) # White
            self.vel_3d = np.array([speed, 0, speed]) # Rises quickly
            self.decay = 0.05

            # Add a little "jitter" so they pop out from different spots on the leaf
            self.pos_3d[0] += random.uniform(-2, 2) # Horizontal spread
            self.pos_3d[1] += random.uniform(-2, 2) # Depth spread
            self.pos_3d[2] += random.uniform(-1, 1) # Vertical spread across leaves

        elif p_type == "co2":
            speed = 0.01
            
            self.color = (100, 100, 100) # Grey
            self.vel_3d = np.array([-speed, 0, speed]) # Floats slowly
            self.decay = 0.02

            # Add a little "jitter" so they pop out from different spots on the leaf
            self.pos_3d[0] += random.uniform(-2, 2) # Horizontal spread
            self.pos_3d[1] += random.uniform(-2, 2) # Depth spread
            self.pos_3d[2] += random.uniform(-1, 1) # Vertical spread across leaves

    def update(self):
        self.pos_3d += self.vel_3d
        self.life -= self.decay

class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.max_particles = 50

    def emit(self, origin_3d, p_type, target_height=0, count=1):
        if len(self.particles) < self.max_particles:
            for _ in range(count):
                self.particles.append(Particle(origin_3d, p_type, target_height))

    def update_and_draw(self, frame, mtx, dist, rvec, tvec):
        # Filter out dead particles
        self.particles = [p for p in self.particles if p.life > 0]
        
        if not self.particles:
            return

        # Prepare 3D points for projection
        pts_3d = np.array([p.pos_3d for p in self.particles])
        
        # Project 3D points to 2D screen pixels
        pts_2d, _ = cv2.projectPoints(pts_3d, rvec, tvec, mtx, dist)
        
        for i, p in enumerate(self.particles):
            # Update particle logic
            p.update()
            
            # Draw on frame
            center = tuple(pts_2d[i].ravel().astype(int))
            #radius = int(p.life * 5) # Particles shrink as they die
            radius = 3
            if radius > 0:
                cv2.circle(frame, center, radius, p.color, -1)