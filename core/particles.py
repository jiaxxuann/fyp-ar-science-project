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
            self.vel_3d = np.array([0, 0, speed]) # [x, y, z]
            if target_height > 0:
                self.decay = speed / target_height
            else:
                self.decay = 0.05

        elif p_type == "oxygen":
            speed = 0.05

            self.color = (255, 255, 255) # White
            self.vel_3d = np.array([speed, 0, speed]) 
            self.decay = 0.05

            # Add a little "jitter" so they pop out from different spots on the leaf
            self.pos_3d[0] += random.uniform(-2, 2) # Horizontal spread
            self.pos_3d[1] += random.uniform(-2, 2) # Depth spread
            self.pos_3d[2] += random.uniform(-1, 1) # Vertical spread across leaves

        elif p_type == "co2":
            speed = 0.01
            
            self.color = (100, 100, 100) # Grey
            self.vel_3d = np.array([speed, 0, -speed]) 
            self.decay = 0.01

            # Add a little "jitter" so they pop out from different spots on the leaf
            self.pos_3d[0] += random.uniform(-2, 2) # Horizontal spread
            self.pos_3d[1] += random.uniform(-2, 2) # Depth spread
            self.pos_3d[2] += random.uniform(0, 3) # Vertical spread across leaves
            
            # # 1. Set the target (e.g., the center of your 3D leaf model)
            # leaf_center = np.array([5.0, 0, -5.0]) # Example coordinates on the Right and Down
            
            # # 2. Calculate the vector from particle to leaf
            # direction_to_leaf = leaf_center - self.pos_3d
            
            # # 3. Normalize the vector so the speed is consistent
            # norm = np.linalg.norm(direction_to_leaf)
            # if norm > 0:
            #     unit_vector = direction_to_leaf / norm
            
            # # 4. Set velocity: move Right and Down toward that target
            # speed = 0.015
            # self.color = (100, 100, 100) # Grey
            # self.vel_3d = unit_vector * speed
            
            # # 5. Faster decay as it gets closer (Simulating absorption)
            # # The closer it is to the leaf, the faster it fades away
            # if norm < 1.0:
            #     self.decay = 0.05  # Disappear quickly once "inside" the leaf
            # else:
            #     self.decay = 0.01  # Normal drift speed

        # ---------------------------------------------------------
        # MICROSCOPE MODE SPECIFIC PARTICLES
        # ---------------------------------------------------------
        elif p_type == "micro_o2":
            import math
            speed = 0.08
            self.color = (255, 255, 255) # White
            self.decay = 0.03 # Fades as it moves away

            # 1. EXPLOSION LOGIC: Moves OUT from the center in random directions
            angle = random.uniform(0, math.pi)
            
            # 2. Calculate velocity pushing outward
            vx = math.cos(angle) * speed
            vz = math.sin(angle) * speed
            self.vel_3d = np.array([vx, 0, vz])

        elif p_type == "micro_co2":
            import math
            speed = 0.08
            self.color = (100, 100, 100) # Grey
            self.decay = 0.03

            # 1. IMPLOSION LOGIC: Spawn in a ring OUTSIDE the leaf
            angle = random.uniform(0, math.pi)
            spawn_radius = 4.0 # Start 4 units away from the center
            
            # 2. Offset the starting position
            offset_x = math.cos(angle) * spawn_radius
            offset_z = math.sin(angle) * spawn_radius
            self.pos_3d[0] += offset_x
            self.pos_3d[2] += offset_z

            # 3. Set velocity TOWARDS the center
            # By moving exactly opposite to the offset, it perfectly targets the leaf
            self.vel_3d = np.array([-offset_x, 0, -offset_z])
            
            # Normalize the vector so speed is consistent, then multiply by speed
            norm = np.linalg.norm(self.vel_3d)
            if norm > 0:
                self.vel_3d = (self.vel_3d / norm) * speed

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
        try:
            pts_2d, _ = cv2.projectPoints(pts_3d, rvec, tvec, mtx, dist)
        except cv2.error:
            return # Skip drawing this frame if projection fails completely
        
        # Get screen boundaries for clamping
        h, w = frame.shape[:2] 
        
        for i, p in enumerate(self.particles):
            # Update particle logic (movement, life reduction)
            p.update()
            
            # Safety check: Extract and validate coordinates
            raw_point = pts_2d[i].ravel()
            
            # Check for NaN (Not a Number) or Inf (Infinity)
            if not np.all(np.isfinite(raw_point)):
                continue

            # Scale & clamp: convert to integers safely
            # Use clip to ensure points don't explode way beyond screen limits
            ix = int(np.clip(raw_point[0], -1000, w + 1000))
            iy = int(np.clip(raw_point[1], -1000, h + 1000))
            center = (ix, iy)

            # radius = int(p.life * 5) 
            radius = 3
            
            # Only draw if the point is somewhat near the screen
            if 0 < radius < 100: # Sanity check for radius size
                try:
                    cv2.circle(frame, center, radius, p.color, -1)
                except cv2.error:
                    continue # Skip if specific circle drawing fails