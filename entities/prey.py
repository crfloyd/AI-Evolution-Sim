import math
import random
import pygame
from entities.base_entity import BaseEntity

class Prey(BaseEntity):
    def __init__(self, x, y, generation=0):
        super().__init__(x, y)
        self.generation = generation
        self.color = (100, 200, 255)
        self.energy = 50
        self.max_energy = 100
        self.energy_regen = 1.0
        self.energy_burn_base = 0.5
        self.energy_burn_per_speed = 0.5
        self.age = 0
        self.time_at_max_energy = 0
        self.color = (100, 200, 255)

    def update(self):
        self.age += 1

        out = self.brain.forward(self.vision)
        speed_factor = (out[1] + 1) / 2
        desired_speed = speed_factor * self.max_speed

        sees_threat = self.sees_predator()
        can_move = self.energy >= self.max_energy and sees_threat

        if can_move:
            self.angular_velocity = out[0]
            self.angle += self.angular_velocity * self.max_turn_speed
            self.angle %= math.tau
            self.speed = desired_speed
            self.x += math.cos(self.angle) * self.speed
            self.y += math.sin(self.angle) * self.speed
            self.energy -= self.energy_burn_base + self.speed * self.energy_burn_per_speed
            self.energy = max(self.energy, 0)
        else:
            self.speed = 0
            self.angular_velocity = 0
            self.energy += self.energy_regen
            self.energy = min(self.energy, self.max_energy)

        if self.energy >= self.max_energy - 0.01:
            self.time_at_max_energy += 1
        else:
            self.time_at_max_energy = 0

        screen_width, screen_height = pygame.display.get_surface().get_size()
        self.x %= screen_width
        self.y %= screen_height

        if self.speed == 0:
            self.stretch = 1.0
            self.x = round(self.x * 1000) / 1000
            self.y = round(self.y * 1000) / 1000
        else:
            self._update_softbody_stretch()

        if hasattr(self, "settling_timer"):
            self.settling_timer -= 1
            if self.settling_timer <= 0:
                del self.settling_timer

        if not can_move:
            print(f"[STATIC] x={self.x:.1f}, y={self.y:.1f}, angle={math.degrees(self.angle):.1f}, stretch={self.stretch:.2f}")

    def should_reproduce(self):
        return self.time_at_max_energy >= 180

    def clone(self):
        angle = random.uniform(0, 2 * math.pi)
        separation = self.radius * 0.75
        dx = math.cos(angle) * separation
        dy = math.sin(angle) * separation

        child = Prey(self.x + dx, self.y + dy, generation=self.generation + 1)
        child.brain = self.brain.copy_with_mutation()
        self.x -= dx / 2
        self.y -= dy / 2
        child.x += dx / 2
        child.y += dy / 2
        return child

    def sees_predator(self):
        return any(d < 1.0 for d in self.vision)
    
    
