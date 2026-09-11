"""
PowerPlay Biomechanical Tremor Engine.
Harris-Wolpert SDN, physiological tremor generator, and Costello's Two-Phase Saccadic Search Model
using Quadratic Bezier Curves.
"""

import math
import random
import time
import numpy as np

class BiomechanicalTremorEngine:
    """
    Harris-Wolpert SDN & Physiological Tremor (8-12 Hz) Generator [৫০, ৭০].
    Implements Costello's Two-Phase Saccadic Search Model using Quadratic Bezier Curves [৮০].
    
    Formulas:
    1. Quadratic Bezier Curve: B(t) = (1-t)²*P0 + 2(1-t)t*P1 + t²*P2
    2. SDN Variance: σ² = k_sdn * ||v||²
    3. Muscle Tremor: T(t) = A_tremor * (1 / (1 + 0.3||v||)) * sin(2πft) + σ * N(0, 1)
    """
    def __init__(self, tremor_amp=0.55, sdn_k=0.04):
        self.tremor_amp = tremor_amp
        self.sdn_k = sdn_k

    def compute_human_noise(self, speed, elapsed_time):
        """Calculates speed-modulated muscle jitter and signal-dependent noise."""
        tremor_freq = random.uniform(8.0, 12.0)  # Human physiological tremor frequency
        tremor_modulation = 1.0 / (1.0 + speed * 0.3)
        
        # Tremor component
        tremor_x = self.tremor_amp * tremor_modulation * math.sin(2.0 * math.pi * tremor_freq * elapsed_time)
        tremor_y = self.tremor_amp * tremor_modulation * math.cos(2.0 * math.pi * tremor_freq * elapsed_time)
        
        # Harris-Wolpert Signal-Dependent Noise (SDN)
        sdn_std = self.sdn_k * speed
        sdn_x = random.normalvariate(0, sdn_std) if sdn_std > 0 else 0
        sdn_y = random.normalvariate(0, sdn_std) if sdn_std > 0 else 0
        
        return (tremor_x + sdn_x), (tremor_y + sdn_y)

    def apply_saccadic_overshoot(self, start_pos, target_pos):
        """Costello's Two-Phase Saccadic model: Ballistic phase (α ∈ [0.92, 1.08])."""
        start = np.array(start_pos, dtype=float)
        target = np.array(target_pos, dtype=float)
        vector = target - start
        
        # 20% chance of overshoot, 80% under-reach for ballistic landing
        alpha = random.uniform(1.02, 1.08) if random.random() < 0.20 else random.uniform(0.92, 0.97)
        return tuple(start + alpha * vector)

    def generate_bezier_trajectory(self, start_pos, target_pos, steps=30):
        """
        MATHEMATICALLY SOLVED (Costello's Two-Phase Saccadic Curve) [৮০]
        - Phase 1: Rapid ballistic movement (80% steps) targeting a slightly overshot/undershot 'ballistic_target' [৮০].
        - Phase 2: Micro-corrective movement (20% steps) from the ballistic endpoint to the 'actual target' [৮০].
        Both phases use smooth Bezier curvature and speed-modulated muscle tremors.
        Includes a critical numerical safety guard for zero-distance drift in Phase 2 to prevent 0/0 and NaN [৮০].
        """
        start = np.array(start_pos, dtype=float)
        target = np.array(target_pos, dtype=float)
        
        # Calculate ballistic target (incorporating Costello's saccadic overshoot/undershoot)
        ballistic_target = np.array(self.apply_saccadic_overshoot(start, target))
        
        # Split steps into Ballistic (80%) and Corrective (20%)
        steps_ballistic = max(2, int(steps * 0.8))
        steps_corrective = max(1, steps - steps_ballistic)
        
        points = []
        t_start = time.time()
        
        # --- PHASE 1: Ballistic Bezier Curve (start -> ballistic_target) ---
        midpoint_1 = (start + ballistic_target) / 2.0
        diff_1 = ballistic_target - start
        perp_vec_1 = np.array([-diff_1[1], diff_1[0]])
        norm_perp_1 = np.linalg.norm(perp_vec_1)
        if norm_perp_1 > 0:
            perp_vec_1 = perp_vec_1 / norm_perp_1
        else:
            perp_vec_1 = np.array([0.0, 0.0])
            
        distance_1 = np.linalg.norm(diff_1)
        drift_magnitude_1 = random.uniform(-0.10, 0.10) * distance_1
        control_point_1 = midpoint_1 + perp_vec_1 * drift_magnitude_1
        
        for i in range(steps_ballistic):
            t = i / float(steps_ballistic - 1) if steps_ballistic > 1 else 1.0
            
            # Quadratic Bezier base point interpolation for Phase 1
            base_pt = ((1 - t) ** 2) * start + 2 * (1 - t) * t * control_point_1 + (t ** 2) * ballistic_target
            
            # Velocity vector (Derivative)
            velocity_vec = 2 * (1 - t) * (control_point_1 - start) + 2 * t * (ballistic_target - control_point_1)
            speed = np.linalg.norm(velocity_vec) / steps
            
            noise_x, noise_y = self.compute_human_noise(speed, time.time() - t_start)
            points.append((base_pt[0] + noise_x, base_pt[1] + noise_y))
            
        # --- PHASE 2: Micro-Correction (ballistic_target -> actual target) ---
        corrective_start = np.array(points[-1])
        diff_2 = target - corrective_start
        distance_2 = np.linalg.norm(diff_2)
        
        # 🎯 FIX 1: If distance_2 is extremely small, avoid NaN / 0-division by using direct linear interpolation midpoint [৮০]
        if distance_2 < 1e-3:
            control_point_2 = (corrective_start + target) / 2.0
        else:
            # Perpendicular control point for small micro-corrective arc
            midpoint_2 = (corrective_start + target) / 2.0
            perp_vec_2 = np.array([-diff_2[1], diff_2[0]])
            norm_perp_2 = np.linalg.norm(perp_vec_2)
            if norm_perp_2 > 0:
                perp_vec_2 = perp_vec_2 / norm_perp_2
            else:
                perp_vec_2 = np.array([0.0, 0.0])
                
            drift_magnitude_2 = random.uniform(-0.05, 0.05) * distance_2
            control_point_2 = midpoint_2 + perp_vec_2 * drift_magnitude_2
        
        # We start from step 1 (skip index 0 as it equals corrective_start)
        for i in range(1, steps_corrective + 1):
            t = i / float(steps_corrective)
            
            # Bezier base point interpolation for Phase 2
            base_pt = ((1 - t) ** 2) * corrective_start + 2 * (1 - t) * t * control_point_2 + (t ** 2) * target
            
            velocity_vec = 2 * (1 - t) * (control_point_2 - corrective_start) + 2 * t * (target - control_point_2)
            speed = np.linalg.norm(velocity_vec) / steps
            
            noise_x, noise_y = self.compute_human_noise(speed, time.time() - t_start)
            points.append((base_pt[0] + noise_x, base_pt[1] + noise_y))
            
        return points

    def simulate_click_micro_slip(self, target_pos):
        """Simulates human click tension release causing 1-2px physical slips."""
        target = np.array(target_pos, dtype=float)
        slip_x = random.uniform(-0.5, 0.5)
        slip_y = random.uniform(-0.5, 0.5)
        mousedown_pos = (target[0] + slip_x, target[1] + slip_y)
        
        dwell_time = random.uniform(0.06, 0.14)  # 60ms to 140ms click hold
        
        slip_distance = random.uniform(1.0, 2.0)
        slip_angle = random.uniform(0, 2 * math.pi)
        mouseup_pos = (
            mousedown_pos[0] + slip_distance * math.cos(slip_angle),
            mousedown_pos[1] + slip_distance * math.sin(slip_angle)
        )
        return mousedown_pos, mouseup_pos, dwell_time


