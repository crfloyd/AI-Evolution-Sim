import math
import pygame
from entities.base_entity import BaseEntity

class Predator(BaseEntity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = (255, 80, 80)
        self.radius = 12

    def update(self, prey_list):
        # Chase nearest prey
        if not prey_list:
            return

        nearest = min(prey_list, key=lambda p: math.hypot(p.x - self.x, p.y - self.y))
        dx = nearest.x - self.x
        dy = nearest.y - self.y
        desired_angle = math.atan2(dy, dx)

        # Turn smoothly toward prey
        angle_diff = (desired_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.angle += max(-self.max_turn_speed, min(self.max_turn_speed, angle_diff))
        self.angle %= 2 * math.pi

        self.speed = self.max_speed * 0.9  # a bit slower than max
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

        # Screen wrap
        screen_width, screen_height = pygame.display.get_surface().get_size()
        self.x %= screen_width
        self.y %= screen_height

        self._update_softbody_stretch()



