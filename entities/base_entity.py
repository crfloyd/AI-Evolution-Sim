import pygame
import math
import random

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

        self.stretch = 1.0  # dynamic scale factor

    def update(self):
        self._update_movement_timing()

        if self.is_moving:
            self.speed = min(self.speed + 0.1, self.max_speed)
        else:
            self.speed = max(self.speed - 0.2, 0)

        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

        screen_width, screen_height = pygame.display.get_surface().get_size()
        self.x %= screen_width
        self.y %= screen_height

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
