import math
import random
import pygame
from entities.base_entity import BaseEntity
from entities.neural_network import NeuralNetwork
from utils import hue_shifted_color

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

MUTATION_DECAY_GENERATION = 20    # Generations before mutation probability drops
ENERGY_REGEN_MUTATION_PROB = 0.1  # Mutation probability for energy regen
MAX_ENERGY_MUTATION_PROB = 0.2    # Mutation probability for increasing max energy


class Prey(BaseEntity):
    def __init__(self, x, y, generation=0, frame_rate=30):
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

        self.reproduce_energy_cost = REPRODUCTION_COST
        self.time_since_threat = 0
        self.children_spawned = 0
        self.age = 0

        self.speed = 0
        self.angular_velocity = 0

        self.brain = NeuralNetwork(input_size=self.num_rays + 3)
        self.vision_hits = ["none"] * self.num_rays

        self.neighbor_avoid_timer = 0
        self.last_avoid_frame = 0

    def update(self, grid):
        sees_threat = any(ray < 0.7 and hit == "predator"
                        for ray, hit in zip(self.vision, self.vision_hits))

        danger_level = sum(1.0 - ray for ray, hit in zip(self.vision, self.vision_hits) if hit == "predator")
        see_nothing = 1.0 if all(hit == "none" for hit in self.vision_hits) else 0.0

        if sees_threat:
            self.time_since_threat = 0
        else:
            self.time_since_threat += 1

        threat_time_norm = min(self.time_since_threat / 300, 1.0)

        vision_input = self.vision + [danger_level, see_nothing, threat_time_norm]
        out = self.brain.forward(vision_input)

        self.angular_velocity = out[0]
        acceleration = (out[1] + 1) / 2  # [0, 1]
        self.speed += acceleration * 0.1
        self.speed = min(self.speed, self.max_speed)

        if self.energy > 0 and sees_threat:
            self.angle += self.angular_velocity * self.max_turn_speed
            self.angle %= math.tau

            self.x += math.cos(self.angle) * self.speed
            self.y += math.sin(self.angle) * self.speed

            self.energy -= self.energy_burn_base
            self.energy = max(0, self.energy)
        else:
            self.angular_velocity = 0
            self.speed *= 0.9  # decay
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

        child.max_speed = max(0.5, round(self.max_speed + random.gauss(0, 0.1), 2))
        child.energy_burn_base = max(0.1, round(self.energy_burn_base + random.gauss(0, 0.01), 2))

        # Copy traits not currently mutated
        child.radius = self.radius
        child.max_turn_speed = self.max_turn_speed
        child.reproduce_energy_cost = self.reproduce_energy_cost

        # Mutate energy traits
        child.energy_regen = self.energy_regen
        child.max_energy = self.max_energy
        mutated = False

        if random.random() < ENERGY_REGEN_MUTATION_PROB:
            child.energy_regen = round(self.energy_regen + random.uniform(0.01, 0.05), 2)
            mutated = True

        if random.random() < MAX_ENERGY_MUTATION_PROB:
            child.max_energy = round(self.max_energy + random.uniform(5, 20), 2)
            mutated = True

        if mutated:
            regen_factor = (child.energy_regen - ENERGY_REGEN_RATE) / 0.3
            energy_factor = (child.max_energy - MAX_ENRERGY) / 100
            combined = max(0.0, min(regen_factor + energy_factor, 1.0))
            hue = 0.6 - 0.6 * combined
            child.color = hue_shifted_color(hue)
        else:
            child.color = self.color

        return child






