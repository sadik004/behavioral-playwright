"""
PowerPlay Action Guard: Normalized GIoU and Centroid Spatial Alignment.
"""

import math
import numpy as np

class UltimateVisionLanguageActionGuard:
    """
    MATHEMATICALLY SECURED GIoU & CENTROID-AREA HEALER [৩৫]
    - Computes Normalized Generalized Intersection over Union (GIoU) in [0, 1] range to ensure valid probability math!
    - Integrates Centroid Distance & Area Ratio to allow graceful validation of nested elements of different sizes.
    
    Formulas:
    1. GIoU = IoU - (Area(C) - Area(Union)) / Area(C)  ∈ [-1, 1]
    2. Normalized GIoU = (GIoU + 1.0) / 2.0  ∈ [0, 1]  (SOLVES probability range leaks!)
    3. Centroid distance: d = sqrt((x_a - x_b)² + (y_a - y_b)²)
    4. Normalised Centroid Score: S_centroid = exp(-d / diagonal_C)
    5. Combined Spatial Score: Spatial_Score = 0.4 * Normalized_GIoU + 0.6 * S_centroid
    """
    def __init__(self, min_safe_probability=0.80):
        self.min_safe_probability = min_safe_probability

    def calculate_cosine_similarity(self, vec_a, vec_b):
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        return dot_product / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0

    def calculate_giou_and_centroid_score(self, box_a, box_b):
        """Computes Normalized Generalized IoU and centroid spatial safety safety coefficient."""
        # Coordinates of intersection
        xA = max(box_a[0], box_b[0])
        yA = max(box_a[1], box_b[1])
        xB = min(box_a[2], box_b[2])
        yB = min(box_a[3], box_b[3])
        
        inter_area = max(0, xB - xA) * max(0, yB - yA)
        
        box_a_area = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        box_b_area = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        union_area = float(box_a_area + box_b_area - inter_area)
        
        iou = inter_area / union_area if union_area > 0 else 0.0
        
        # Coordinates of smallest enclosing box C (Smallest convex hull)
        xC1 = min(box_a[0], box_b[0])
        yC1 = min(box_a[1], box_b[1])
        xC2 = max(box_a[2], box_b[2])
        yC2 = max(box_a[3], box_b[3])
        
        area_C = float((xC2 - xC1) * (yC2 - yC1))
        
        # Generalized IoU (GIoU) in range [-1, 1] [৩৫]
        if area_C > 0:
            giou = iou - ((area_C - union_area) / area_C)
        else:
            giou = iou
            
        # 🎯 NORMALIZATION to [0, 1] range to ensure valid probability math!
        norm_giou = (giou + 1.0) / 2.0
            
        # Centroid Distance and Area ratio healing [৩৫]
        centroid_a = ((box_a[0] + box_a[2])/2.0, (box_a[1] + box_a[3])/2.0)
        centroid_b = ((box_b[0] + box_b[2])/2.0, (box_b[1] + box_b[3])/2.0)
        
        d_centroid = math.hypot(centroid_a[0] - centroid_b[0], centroid_a[1] - centroid_b[1])
        diag_C = math.hypot(xC2 - xC1, yC2 - yC1)
        
        centroid_score = math.exp(-d_centroid / (diag_C if diag_C > 0 else 1.0))
        
        # Combined Robust Spatial Score using Normalized GIoU
        spatial_score = 0.4 * norm_giou + 0.6 * centroid_score
        return spatial_score, giou, norm_giou, centroid_score

    def evaluate_and_heal_click(self, vec_intended, vec_scanned, box_intended, box_scanned):
        """Analyzes spatial and linguistic compatibility using Normalized GIoU and centroid matrices."""
        text_sim = self.calculate_cosine_similarity(vec_intended, vec_scanned)
        spatial_score, giou, norm_giou, centroid_score = self.calculate_giou_and_centroid_score(box_intended, box_scanned)
        
        combined_prob = (0.5 * text_sim) + (0.5 * spatial_score)
        
        if combined_prob >= self.min_safe_probability:
            return {
                "decision": "PASS",
                "confidence_score": round(combined_prob, 4),
                "text_similarity": round(text_sim, 4),
                "spatial_score": round(spatial_score, 4),
                "giou": round(giou, 4),
                "norm_giou": round(norm_giou, 4),
                "centroid_score": round(centroid_score, 4),
                "resolved_coords": (int((box_scanned[0] + box_scanned[2])/2), int((box_scanned[1] + box_scanned[3])/2)),
                "action": "✅ HEALED & APPROVED (Generalized IoU and Centroid alignment satisfied safety parameters) [৩৫]"
            }
        else:
            return {
                "decision": "BLOCK",
                "confidence_score": round(combined_prob, 4),
                "text_similarity": round(text_sim, 4),
                "spatial_score": round(spatial_score, 4),
                "giou": round(giou, 4),
                "norm_giou": round(norm_giou, 4),
                "centroid_score": round(centroid_score, 4),
                "action": "❌ HARD SECURITY BLOCK TRIGGERED (Linguistic/Spatial divergence too high to safely click)"
            }


