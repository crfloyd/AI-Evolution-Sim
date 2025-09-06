import pygame
import math
import random
from entities.neural_network import NeuralNetwork
from vision_utils import raycast_batch, HIT_NONE, HIT_PREDATOR, HIT_PREY

HIT_TYPE_MAP = {
    HIT_PREDATOR: "predator",
    HIT_PREY: "prey",
    HIT_NONE: "none"
}

import numpy as np

class BaseEntity:
    _next_id = 1  # Class variable for unique IDs

    def __init__(self, x, y, entity_type="unknown"):
        self.id = BaseEntity._next_id
        BaseEntity._next_id += 1
        self.x = x
        self.y = y
        self.angle = random.uniform(0, 2 * math.pi)
        self.last_avoid_frame = 0
        self.max_speed = 2.5
        self.stop_timer = 0
        self.move_timer = 0
        self.is_moving = True
        self.entity_type = entity_type
        self.stretch_amount = 1.0

        
        self.last_collision_frame = 0
        self.neighbor_avoid_timer = 0

        # Vision
        self.vision = [1.0] * (self.num_rays) # initialize to "nothing seen"
        self.stretch = 1.0  # dynamic scale factor
        
        # Fitness tracking
        self.fitness_stats = {
            'birth_frame': 0,
            'death_frame': None,
            'survival_time': 0,
            'children_produced': 0,
            'energy_efficiency': 0.0,
            'threat_encounters': 0,
            'successful_escapes': 0
        }


    def _update_movement_timing(self):
        if self.is_moving:
            self.move_timer -= 1
            if self.move_timer <= 0:
                self.is_moving = False
                self.stop_timer = random.randint(30, 100)
        else:
            self.stop_timer -= 1
            if self.stop_timer <= 0:
                self.is_moving = True
                self.angle = random.uniform(0, 2 * math.pi)
                self.move_timer = random.randint(60, 180)

    def _update_softbody_stretch(self):
        # Early out if not moving
        if self.speed == 0:
            self.stretch = 1.0
            return
        # Stretch in movement direction, compress in perpendicular
        target_stretch = 1.0 + min(self.speed / self.max_speed, 1.0) * 0.5
        self.stretch += (target_stretch - self.stretch) * 0.2  # easing factor

    def draw(self, surface, selected=False):
        angle_deg = math.degrees(self.angle)
        width = self.radius * 2 * self.stretch
        height = self.radius * 2 / self.stretch

        body = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.ellipse(body, self.color, (0, 0, width, height))
        rotated = pygame.transform.rotate(body, -angle_deg)
        rect = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rect)

        # === EYE RENDERING ===
        eye_offset_angle = math.pi / 6  # separation between eyes
        eye_distance = self.radius * 0.8
        eye_radius = 4
        pupil_radius = 2

        for side in (-1, 1):  # left and right
            eye_angle = self.angle + side * eye_offset_angle
            eye_x = self.x + math.cos(eye_angle) * eye_distance
            eye_y = self.y + math.sin(eye_angle) * eye_distance

            # Sclera
            pygame.draw.circle(surface, (255, 255, 255), (int(eye_x), int(eye_y)), eye_radius)

            # Pupil (centered for now)
            pygame.draw.circle(surface, (0, 0, 0), (int(eye_x), int(eye_y)), pupil_radius)

        # Draw vision rays
        if selected:
            self.draw_vision_rays(surface)

        self.draw_overlay(surface) 


    def draw_vision_rays(self, surface):
        if not self.vision or not hasattr(self, "vision_hits"):
            return

        if math.isclose(self.fov, math.tau):  # 360° vision
            ray_angles = [i * (math.tau / self.num_rays) for i in range(self.num_rays)]
        else:
            half_fov = self.fov / 2
            start_angle = self.angle - half_fov
            ray_angles = [start_angle + i * (self.fov / (self.num_rays - 1)) for i in range(self.num_rays)]

        for i, angle in enumerate(ray_angles):
            # Actual distance is capped at view_range
            ray_length = self.vision[i] * self.view_range
            end_x = self.x + math.cos(angle) * ray_length
            end_y = self.y + math.sin(angle) * ray_length

            # Color logic: Yellow if hit something, gray otherwise
            hit = self.vision_hits[i]
            color = (255, 255, 0) if hit != "none" else (100, 100, 100)

            pygame.draw.line(surface, color, (self.x, self.y), (end_x, end_y), 1)


    def cast_vision(self, others):

        other_positions = np.empty((len(others), 2), dtype=np.float32)
        other_radii = np.empty(len(others), dtype=np.float32)
        other_types = np.empty(len(others), dtype=np.int32)

        for i, o in enumerate(others):
            other_positions[i, 0] = o.x
            other_positions[i, 1] = o.y
            other_radii[i] = o.radius
            if o.entity_type == "predator":
                other_types[i] = HIT_PREDATOR
            elif o.entity_type == "prey":
                other_types[i] = HIT_PREY
            else:
                other_types[i] = HIT_NONE

        detect_predator = self.entity_type == "prey"
        detect_prey = self.entity_type == "predator"

        vision_raw, hits_raw = raycast_batch(
            self.x, self.y, self.angle, self.fov, self.view_range,
            self.num_rays, other_positions, other_radii, other_types,
            detect_predator, detect_prey
        )

        self.vision = vision_raw.tolist()
        self.vision_hits = [HIT_TYPE_MAP[h] for h in hits_raw]



    def resolve_collisions(self, others, push_strength=0.05, max_push=0.8):
        return
        # if self.last_collision_frame > 0:
        #     self.last_collision_frame -= 1
        #     return
        # self.last_collision_frame = 5

        # if hasattr(self, "settling_timer") and self.settling_timer > 0:
        #     return
        # for other in others:
        #     if other is self:
        #         continue
        #     if type(self) != type(other):  # 🔒 skip predator-prey collisions
        #         continue
        #     dx = self.x - other.x
        #     dy = self.y - other.y
        #     dist_sq = dx * dx + dy * dy
        #     overlap = 0
        #     radius_sum = self.radius + other.radius
        #     if dist_sq < radius_sum * radius_sum:
        #         dist = math.sqrt(dist_sq)
        #         overlap = radius_sum - dist

        #     if overlap > 0 and dist > 0:
        #         push_amount = min(overlap * push_strength, max_push)
        #         if push_amount < 0.05:
        #             continue
        #         push_x = (dx / dist) * (push_amount / 2)
        #         push_y = (dy / dist) * (push_amount / 2)
        #         self.x += push_x
        #         self.y += push_y
        #         other.x -= push_x
        #         other.y -= push_y

    def draw_overlay(self, surface):
        pass
        
    def update_fitness_stats(self, frame_count):
        """Update fitness tracking statistics"""
        self.fitness_stats['survival_time'] = frame_count - self.fitness_stats['birth_frame']
        
    def record_threat_encounter(self):
        """Record when entity encounters a threat"""
        self.fitness_stats['threat_encounters'] += 1
        
    def record_successful_escape(self):
        """Record when entity successfully escapes from threat"""
        self.fitness_stats['successful_escapes'] += 1
        
    def record_reproduction(self):
        """Record when entity successfully reproduces"""
        self.fitness_stats['children_produced'] += 1
        
    def calculate_base_fitness(self):
        """Calculate basic fitness score for this entity"""
        survival_time = self.fitness_stats['survival_time']
        children = self.fitness_stats['children_produced']
        
        # Base fitness: survival time + reproductive success bonus
        fitness = survival_time + (children * 500)  # 500 frames bonus per child
        
        # Escape efficiency bonus (for prey)
        if self.fitness_stats['threat_encounters'] > 0:
            escape_rate = self.fitness_stats['successful_escapes'] / self.fitness_stats['threat_encounters']
            fitness += escape_rate * 200  # Bonus for good escape rate
            
        return max(0, fitness)










