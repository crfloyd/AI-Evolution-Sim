import pygame
import math
import random
from entities.neural_network import NeuralNetwork

class BaseEntity:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 12
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = 0
        self.max_speed = 2.5
        self.stop_timer = 0
        self.move_timer = 0
        self.is_moving = True

        # Vision
        self.fov = math.radians(120)  # field of view in radians
        self.num_rays = 7             # number of rays
        self.view_range = 120         # how far rays go
        self.vision = [1.0] * self.num_rays  # initialize to "nothing seen"

        self.stretch = 1.0  # dynamic scale factor

        # Neural network
        self.brain = NeuralNetwork(input_size=self.num_rays)
        self.angular_velocity = 0.0
        self.max_turn_speed = 0.15  # radians per frame


    def update(self):
        # --- Neural network controls movement ---
        out = self.brain.forward(self.vision)
        self.angular_velocity = out[0]  # -1 to 1
        speed_factor = (out[1] + 1) / 2  # convert [-1, 1] → [0, 1]
        self.speed = speed_factor * self.max_speed

        # --- Smooth turning ---
        self.angle += self.angular_velocity * self.max_turn_speed
        self.angle %= 2 * math.pi

        # --- Movement ---
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

        # Wrap around edges
        screen_width, screen_height = pygame.display.get_surface().get_size()
        self.x %= screen_width
        self.y %= screen_height

        # --- Visual squash/stretch effect ---
        self._update_softbody_stretch()


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
        # Stretch in movement direction, compress in perpendicular
        target_stretch = 1.0 + min(self.speed / self.max_speed, 1.0) * 0.5
        self.stretch += (target_stretch - self.stretch) * 0.2  # easing factor

    def draw(self, surface):
        angle_deg = math.degrees(self.angle)
        width = self.radius * 2 * self.stretch
        height = self.radius * 2 / self.stretch

        body = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.ellipse(body, (100, 200, 255), (0, 0, width, height))
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
        half_fov = self.fov / 2
        start_angle = self.angle - half_fov

        for i, norm_dist in enumerate(self.vision):
            angle = start_angle + i * (self.fov / (self.num_rays - 1))
            dist = norm_dist * self.view_range

            end_x = self.x + math.cos(angle) * dist
            end_y = self.y + math.sin(angle) * dist

            color = (255, 255, 0) if norm_dist < 1.0 else (100, 100, 100)
            pygame.draw.line(surface, color, (self.x, self.y), (end_x, end_y), 1)



    def cast_vision(self, others):
        self.vision = []

        half_fov = self.fov / 2
        start_angle = self.angle - half_fov
        ray_angles = [start_angle + i * (self.fov / (self.num_rays - 1)) for i in range(self.num_rays)]

        for angle in ray_angles:
            closest_dist = self.view_range
            ray_dx = math.cos(angle)
            ray_dy = math.sin(angle)

            for other in others:
                if other is self:
                    continue

                dx = other.x - self.x
                dy = other.y - self.y
                proj_len = dx * ray_dx + dy * ray_dy  # projection onto ray direction

                if 0 < proj_len < self.view_range:
                    closest_point_x = self.x + ray_dx * proj_len
                    closest_point_y = self.y + ray_dy * proj_len
                    dist_to_other = math.hypot(other.x - closest_point_x, other.y - closest_point_y)

                    if dist_to_other < other.radius:
                        closest_dist = min(closest_dist, proj_len)

            self.vision.append(closest_dist / self.view_range)  # normalize


    def resolve_collisions(self, others):
        for other in others:
            if other is self:
                continue
            dx = self.x - other.x
            dy = self.y - other.y
            dist = math.hypot(dx, dy)
            overlap = self.radius + other.radius - dist
            if overlap > 0 and dist > 0:
                push_x = (dx / dist) * (overlap / 2)
                push_y = (dy / dist) * (overlap / 2)
                self.x += push_x
                self.y += push_y
                other.x -= push_x
                other.y -= push_y


