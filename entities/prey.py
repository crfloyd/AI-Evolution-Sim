import math
import random
import pygame
from entities.base_entity import BaseEntity
from entities.neural_network import NeuralNetwork

REPRODUCTION_THRESHOLD = 600
MAX_SPEED = 1.5
MAX_TURN_SPEED = 0.15
RADIUS = 10
VIEW_RANGE = 100

STARTING_ENERGY = 0
MAX_ENRERGY = 100
ENERGY_REGEN_RATE = 0.15
ENERGY_BURN_BASE = 0.4
# ENERGY_BURN_RATE_WHILE_MOVING = 0.3
REPRODUCTION_COST = 30

class Prey(BaseEntity):
    def __init__(self, x, y, generation=0):
        self.num_rays = 24
        super().__init__(x, y)
        self.color = (100, 200, 255)
        self.radius = RADIUS
        self.generation = generation
        self.max_speed = MAX_SPEED

        self.fov = math.radians(360)
        self.view_range = VIEW_RANGE

        self.max_turn_speed = MAX_TURN_SPEED
        self.energy = STARTING_ENERGY
        self.max_energy = MAX_ENRERGY
        self.energy_regen = ENERGY_REGEN_RATE
        self.energy_burn_base = ENERGY_BURN_BASE
        # self.energy_burn_per_speed = ENERGY_BURN_RATE_WHILE_MOVING

        self.reproduce_energy_cost = REPRODUCTION_COST
        self.children_spawned = 0
        self.age = 0

        self.speed = 0
        self.angular_velocity = 0

        self.brain = NeuralNetwork(input_size=self.num_rays + 1)
        self.vision_hits = ["none"] * self.num_rays

        self.neighbor_avoid_timer = 0
        self.last_avoid_frame = 0

    def update(self, grid):
        # === Detect predator ===
        sees_threat = any(ray < 0.7 and hit == "predator"
                          for ray, hit in zip(self.vision, self.vision_hits))

        # === Run brain ===
        vision_input = self.vision + [1.0]
        out = self.brain.forward(vision_input)
        self.angular_velocity = out[0]
        speed_factor = (out[1] + 1) / 2
        desired_speed = speed_factor * self.max_speed

        if self.energy > 0 and sees_threat:
            self.angle += self.angular_velocity * self.max_turn_speed
            self.angle %= math.tau

            self.speed = desired_speed
            self.x += math.cos(self.angle) * self.speed
            self.y += math.sin(self.angle) * self.speed

            self.energy -= self.energy_burn_base 
            self.energy = max(0, self.energy)
        else:
            # Not moving, regenerate
            self.angular_velocity = 0
            self.speed = 0
            self.energy += self.energy_regen
            self.energy = min(self.energy, self.max_energy)

        screen_width, screen_height = pygame.display.get_surface().get_size()
        self.x %= screen_width
        self.y %= screen_height

        self._update_softbody_stretch()
        self.avoid_neighbors(grid)

    def avoid_neighbors(self, grid):
        if self.neighbor_avoid_timer > 0:
            self.neighbor_avoid_timer -= 1
            return
        self.neighbor_avoid_timer = 4
        if self.last_avoid_frame > 0:
            self.last_avoid_frame -= 1
            return
        self.last_avoid_frame = 5
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
        # ✅ Reproduce based on energy level
        return self.energy >= self.max_energy

    def clone(self):
        child = Prey(
            self.x + random.randint(-10, 10),
            self.y + random.randint(-10, 10),
            generation=self.generation + 1
        )
        child.brain = self.brain.copy_with_mutation()

        # Mutate speed-related traits
        child.max_speed = max(0.5, self.max_speed + random.gauss(0, 0.05))
        child.energy_burn_base = max(0.1, self.energy_burn_base + random.gauss(0, 0.01))

        return child


