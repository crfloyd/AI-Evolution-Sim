import math
import random
import pygame
from entities.base_entity import BaseEntity
from entities.neural_network import NeuralNetwork

class Prey(BaseEntity):
    def __init__(self, x, y, generation=0):
        self.num_rays = 24
        super().__init__(x, y)
        self.color = (100, 200, 255)
        self.radius = 10
        self.generation = generation

        self.fov = math.radians(360)
        self.view_range = 100
        self.brain = NeuralNetwork(input_size=self.num_rays + 1)

        self.max_speed = 1.5
        self.max_turn_speed = 0.15
        self.energy = 50
        self.max_energy = 100
        self.energy_regen = 0.4
        self.energy_burn_base = 0.4
        self.energy_burn_per_speed = 0.3

        self.speed = 0
        self.angular_velocity = 0
        self.time_at_max_energy = 0
        self.reproduce_threshold = 600  # 10s at 60fps
        self.reproduce_energy_cost = 10
        self.children_spawned = 0
        self.age = 0

        self.vision_hits = ["none"] * self.num_rays

    def update(self, grid):
        # === Detect predator ===
        sees_threat = any(ray < 0.7 and hit == "predator"
                          for ray, hit in zip(self.vision, self.vision_hits))

        # === Run brain ===
        vision_input = self.vision + [1.0]  # bias
        out = self.brain.forward(vision_input)
        self.angular_velocity = out[0]
        speed_factor = (out[1] + 1) / 2
        desired_speed = speed_factor * self.max_speed

        if self.energy > 0 and sees_threat:
            self.angle += self.angular_velocity * self.max_turn_speed

        self.angle %= math.tau

        if self.energy > 0 and sees_threat:
            self.speed = desired_speed
            self.x += math.cos(self.angle) * self.speed
            self.y += math.sin(self.angle) * self.speed

            self.energy -= self.energy_burn_base + self.speed * self.energy_burn_per_speed
            self.energy = max(0, self.energy)
            self.time_at_max_energy = 0
        else:
            self.angular_velocity = 0
            self.speed = 0

            self.energy += self.energy_regen
            self.energy = min(self.energy, self.max_energy)

            if self.energy >= self.max_energy:
                self.time_at_max_energy += 1
            else:
                self.time_at_max_energy = 0

        screen_width, screen_height = pygame.display.get_surface().get_size()
        self.x %= screen_width
        self.y %= screen_height

        self._update_softbody_stretch()
        self.avoid_neighbors(grid)

    def avoid_neighbors(self, grid):
        neighbors = grid.get_neighbors(self)
        for other in neighbors:
            if other is self or not isinstance(other, Prey):
                continue
            dx = self.x - other.x
            dy = self.y - other.y
            dist = math.hypot(dx, dy)
            if 0 < dist < self.radius * 2:
                repel_angle = math.atan2(dy, dx)
                self.angle += 0.04 * math.sin(repel_angle - self.angle)

    def should_reproduce(self):
        return (self.time_at_max_energy >= self.reproduce_threshold and
                self.energy >= self.reproduce_energy_cost)

    def clone(self):
        child = Prey(
            self.x + random.randint(-10, 10),
            self.y + random.randint(-10, 10),
            generation=self.generation + 1
        )
        child.brain = self.brain.copy_with_mutation()
        return child
