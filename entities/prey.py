import math
import random
import pygame
from entities.base_entity import BaseEntity
from entities.neural_network import NeuralNetwork
from utils import hue_shifted_color

MAX_SPEED = 5.5
MAX_TURN_SPEED = 0.25
RADIUS = 10
VIEW_RANGE = 100

STARTING_ENERGY = 0
MAX_ENRERGY = 100
ENERGY_REGEN_RATE = 10 # Energy regeneration rate per second
ENERGY_BURN_BASE = 0.01 
# ENERGY_BURN_RATE_WHILE_MOVING = 0.3
REPRODUCTION_COST = 80
REPRODUCTION_ENERGY_THRESHOLD = 100

MUTATION_DECAY_GENERATION = 20    # Generations before mutation probability drops
ENERGY_REGEN_MUTATION_PROB = 0.1  # Mutation probability for energy regen
MAX_ENERGY_MUTATION_PROB = 0.2    # Mutation probability for increasing max energy
MAX_TURN_SPEED_MUTATION_PROB = 0.1# Mutation probability for max turn speed
SPEED_MUTATION_PROB = 0.5         # Mutation probability for speed


class Prey(BaseEntity):
    def __init__(self, x, y, generation=0, frame_rate=30):
        self.frame_rate = frame_rate
        self.num_rays = 24
        super().__init__(x, y, entity_type="prey")
        self.color = (100, 200, 255)
        self.radius = RADIUS
        self.generation = generation
        self.max_speed = MAX_SPEED


        self.fov = math.radians(360)
        self.view_range = VIEW_RANGE

        self.max_turn_speed = MAX_TURN_SPEED
        self.energy = STARTING_ENERGY
        self.max_energy = MAX_ENRERGY
        self.energy_regen = ENERGY_REGEN_RATE / frame_rate
        self.energy_burn_base = ENERGY_BURN_BASE

        self.reproduce_energy_cost = REPRODUCTION_COST
        self.children_spawned = 0
        self.age = 0

        self.speed = 0
        self.angular_velocity = 0

        self.brain = NeuralNetwork(input_size=self.num_rays + 3)
        self.vision_hits = ["none"] * self.num_rays
        self.frames_since_predator_seen = 999


        self.neighbor_avoid_timer = 0
        self.last_avoid_frame = 0

    def update(self, grid):
        sees_threat = any(ray < 0.7 and hit == "predator"
                        for ray, hit in zip(self.vision, self.vision_hits))

        danger_level = sum(1.0 - ray for ray, hit in zip(self.vision, self.vision_hits) if hit == "predator")
        see_nothing = 1.0 if all(hit == "none" for hit in self.vision_hits) else 0.0

        if sees_threat:
            self.frames_since_predator_seen = 0
        else:
            self.frames_since_predator_seen += 1

        threat_memory = max(0.0, 1.0 - self.frames_since_predator_seen / self.frame_rate)  # fades over 60 frames
        vision_input = self.vision + [danger_level, see_nothing, threat_memory]
        out = self.brain.forward(vision_input)

        self.angular_velocity = out[0]
        acceleration = (out[1] + 1) / 2  # [0, 1]
        self.speed += acceleration * 0.15
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
        # self.avoid_neighbors(grid)


    def avoid_neighbors(self, grid):
        # if self.neighbor_avoid_timer > 0:
        #     self.neighbor_avoid_timer -= 1
        #     return
        # self.neighbor_avoid_timer = 4

        radius_squared = (self.radius * 2) ** 2
        move_x, move_y = 0, 0
        count = 0

        for other in grid.get_neighbors(self):
            if other is self or not isinstance(other, Prey):
                continue
            dx = self.x - other.x
            dy = self.y - other.y
            dist_squared = dx * dx + dy * dy
            if 0 < dist_squared < radius_squared:
                strength = 1 - (dist_squared / radius_squared)
                norm = math.sqrt(dist_squared)
                move_x += (dx / norm) * strength
                move_y += (dy / norm) * strength
                count += 1

        if count > 0:
            self.x += (move_x / count) * 0.5 
            self.y += (move_y / count) * 0.5



    def should_reproduce(self):
        # ✅ Reproduce based on energy level
        return self.energy >= REPRODUCTION_ENERGY_THRESHOLD

    def clone(self):
        child = Prey(
            self.x + random.randint(-30, 30),
            self.y + random.randint(-30, 30),
            generation=self.generation + 1
        )
        child.parent_id = self.id
        child.brain = self.brain.copy_with_mutation()
        # child.speed = max(0.5, round(self.max_speed + random.gauss(0, 1), 2))
        child.energy_burn_base = max(0.1, round(self.energy_burn_base - random.gauss(0, 0.01), 2))
        
        # Track significant mutations
        child.mutations = {}
        # Track neural mutations if significant (>0.01 strength)
        if hasattr(child.brain, '_mutation_strength') and child.brain._mutation_strength > 0.01:
            child.mutations["n"] = round(child.brain._mutation_strength, 3)

        # Copy traits not currently mutated
        child.radius = self.radius
        child.max_turn_speed = self.max_turn_speed
        child.reproduce_energy_cost = self.reproduce_energy_cost

        # Mutate energy traits
        child.energy_regen = self.energy_regen
        child.max_energy = self.max_energy
        child.max_speed = self.max_speed
        child.max_turn_speed = self.max_turn_speed
        child.color = self.color
        child.stretch = self.stretch
        mutated = False

        if random.random() < SPEED_MUTATION_PROB:
            old_speed = self.max_speed
            child.max_speed = round(self.max_speed + random.uniform(0.3, 1), 2)
            if self.max_speed < child.max_speed:
                child.stretch += 0.3
                mutated = True
                # Track significant speed mutation (>10% change)
                if abs(child.max_speed - old_speed) / old_speed > 0.1:
                    child.mutations["s"] = [old_speed, child.max_speed]

        if random.random() < MAX_ENERGY_MUTATION_PROB:
            old_energy = self.max_energy
            child.max_energy = round(self.max_energy + random.uniform(1, 3), 2)
            mutated = True
            # Track significant energy mutation (>5% change)
            if abs(child.max_energy - old_energy) / old_energy > 0.05:
                child.mutations["e"] = [old_energy, child.max_energy]

        # if random.random() < MAX_TURN_SPEED_MUTATION_PROB:
        #     child.max_turn_speed = round(self.max_turn_speed + random.uniform(0.5, 3), 2)
        #     mutated = True

        if random.random() < ENERGY_REGEN_MUTATION_PROB:
            old_regen = self.energy_regen
            child.energy_regen = round(self.energy_regen + random.uniform(0.01, 0.05), 2)
            mutated = True
            # Track significant regen mutation (>10% change)
            if abs(child.energy_regen - old_regen) / old_regen > 0.1:
                child.mutations["r"] = [old_regen, child.energy_regen]

        if random.random() < MAX_ENERGY_MUTATION_PROB:
            old_energy = self.max_energy
            child.max_energy = round(self.max_energy + random.uniform(5, 20), 2)
            mutated = True
            # Track significant energy mutation (>5% change) - second mutation chance
            if abs(child.max_energy - old_energy) / old_energy > 0.05:
                child.mutations["e"] = [old_energy, child.max_energy]

        if mutated:
            child.color = hue_shifted_color(self.color, 0.1)
        else:
            child.color = self.color

        self.energy -= self.reproduce_energy_cost
        return child






