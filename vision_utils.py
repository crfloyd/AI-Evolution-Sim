# vision_utils.py

from numba import njit
import numpy as np
import math

# Define numeric hit types Numba can handle
HIT_NONE = 0
HIT_PREDATOR = 1
HIT_PREY = 2

@njit
def raycast_batch(
    self_x, self_y, self_angle, fov, view_range, num_rays,
    other_positions, other_radii, other_types,
    detect_predator, detect_prey
):
    vision = np.ones(num_rays, dtype=np.float32)
    hits = np.full(num_rays, HIT_NONE, dtype=np.int32)

    ray_angles = np.empty(num_rays, dtype=np.float64)
    if abs(fov - 2 * math.pi) < 1e-5:
        step = (2 * math.pi) / num_rays
        for i in range(num_rays):
            ray_angles[i] = i * step
    else:
        step = fov / (num_rays - 1)
        start_angle = self_angle - fov / 2.0
        for i in range(num_rays):
            ray_angles[i] = start_angle + i * step

        ray_angles = np.linspace(start_angle, start_angle + fov, num_rays)

    for ray_idx in range(num_rays):
        angle = ray_angles[ray_idx]
        ray_dx = math.cos(angle)
        ray_dy = math.sin(angle)
        closest_dist = view_range
        hit_type = HIT_NONE

        for i in range(len(other_positions)):
            ox, oy = other_positions[i]
            radius = other_radii[i]
            typ = other_types[i]

            dx = ox - self_x
            dy = oy - self_y
            proj_len = dx * ray_dx + dy * ray_dy

            if 0 < proj_len < view_range:
                closest_x = self_x + ray_dx * proj_len
                closest_y = self_y + ray_dy * proj_len
                dist_sq = (ox - closest_x) ** 2 + (oy - closest_y) ** 2

                if dist_sq < radius ** 2 and proj_len < closest_dist:
                    if typ == HIT_PREDATOR and detect_predator:
                        closest_dist = proj_len
                        hit_type = HIT_PREDATOR
                    elif typ == HIT_PREY and detect_prey:
                        closest_dist = proj_len
                        hit_type = HIT_PREY

        vision[ray_idx] = closest_dist / view_range
        hits[ray_idx] = hit_type

    return vision, hits