import math
import random
import pygame
from entities.base_entity import BaseEntity
from entities.neural_network import NeuralNetwork
from utils import hue_shifted_color

# Import centralized frame rate constant
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from main import FRAME_RATE
except ImportError:
    FRAME_RATE = 60  # Fallback if import fails

MAX_SPEED = 5.5
MAX_TURN_SPEED = 0.25
RADIUS = 10
VIEW_RANGE = 100

STARTING_ENERGY = 0  # Will be randomized in __init__
MAX_ENRERGY = 100
ENERGY_REGEN_RATE = 15 # Energy regeneration rate per second (increased from 10)
ENERGY_BURN_BASE = 0.01 
# ENERGY_BURN_RATE_WHILE_MOVING = 0.3
REPRODUCTION_COST = 60  # Reduced from 80 to match new threshold
REPRODUCTION_ENERGY_THRESHOLD = 75  # Reduced from 100

# Death conditions
MAX_AGE_SECONDS = 45      # Prey dies of old age after 45 seconds
STARVATION_ENERGY = 0     # Prey dies when energy reaches 0

MUTATION_DECAY_GENERATION = 20    # Generations before mutation probability drops
ENERGY_REGEN_MUTATION_PROB = 0.05  # Mutation probability for energy regen (was 0.1)
MAX_ENERGY_MUTATION_PROB = 0.1     # Mutation probability for increasing max energy (was 0.2)
MAX_TURN_SPEED_MUTATION_PROB = 0.05 # Mutation probability for max turn speed (was 0.1)
SPEED_MUTATION_PROB = 0.25         # Mutation probability for speed (was 0.5)


def adaptive_mutation_probability(base_prob, generation):
    """Calculate adaptive mutation probability based on generation"""
    if generation <= 2:
        return base_prob * 1.8  # Higher early exploration
    elif generation <= 5:
        return base_prob * 1.3  # Medium exploration
    else:
        return base_prob * 0.8  # Lower fine-tuning


class Prey(BaseEntity):
    def __init__(self, x, y, generation=0, frame_rate=FRAME_RATE):
        self.frame_rate = frame_rate
        self.num_rays = 24
        super().__init__(x, y, entity_type="prey")
        
        # Initialize fitness tracking
        self.fitness_stats['birth_frame'] = 0  # Will be set when added to simulation
        self.color = (100, 200, 255)
        self.radius = RADIUS
        self.generation = generation
        self.max_speed = MAX_SPEED


        self.fov = math.radians(360)
        self.view_range = VIEW_RANGE

        self.max_turn_speed = MAX_TURN_SPEED
        # Randomize starting energy to prevent synchronization across all generations
        base_energy = STARTING_ENERGY if generation > 0 else 0
        self.energy = base_energy + random.randint(0, 40)  # Add 0-40 random energy
        self.max_energy = MAX_ENRERGY
        # Randomize energy regen rate to prevent synchronization (±20% variation)
        self.energy_regen = (ENERGY_REGEN_RATE / frame_rate) * random.uniform(0.8, 1.2)
        self.energy_burn_base = ENERGY_BURN_BASE

        self.reproduce_energy_cost = REPRODUCTION_COST
        self.children_spawned = 0
        self.age = 0

        self.speed = 0
        self.angular_velocity = 0

        self.brain = NeuralNetwork(input_size=self.num_rays + 3, hidden_size=16)
        self.vision_hits = ["none"] * self.num_rays
        self.frames_since_predator_seen = 999
        
        # Cache screen dimensions to avoid repeated pygame calls
        self._screen_width = None
        self._screen_height = None


        self.neighbor_avoid_timer = 0
        self.last_avoid_frame = 0

    def update(self, grid):
        # Optimize vision processing with single pass
        predator_hits = 0
        sees_threat = False
        danger_level = 0.0
        
        for ray, hit in zip(self.vision, self.vision_hits):
            if hit == "predator":
                predator_hits += 1
                danger_level += (1.0 - ray)
                if ray < 0.7:
                    sees_threat = True
        
        see_nothing = 1.0 if predator_hits == 0 else 0.0

        if sees_threat:
            self.frames_since_predator_seen = 0
            # Fitness tracking: record threat encounter
            if self.frames_since_predator_seen > (0.5 * self.frame_rate):  # Only count if not recently seen (0.5s)
                self.record_threat_encounter()
        else:
            self.frames_since_predator_seen += 1
            # Fitness tracking: record successful escape if previously in danger
            if self.frames_since_predator_seen == 1:  # Just escaped from danger
                self.record_successful_escape()

        threat_memory = max(0.0, 1.0 - self.frames_since_predator_seen / self.frame_rate)  # fades over 60 frames
        vision_input = self.vision + [danger_level, see_nothing, threat_memory]
        out = self.brain.forward(vision_input)

        self.angular_velocity = out[0]
        acceleration = (out[1] + 1) / 2  # [0, 1]
        self.speed += acceleration * 0.15 * (30.0 / self.frame_rate)
        self.speed = min(self.speed, self.max_speed)

        # Cache screen dimensions on first use
        if self._screen_width is None:
            self._screen_width, self._screen_height = pygame.display.get_surface().get_size()

        if self.energy > 0 and sees_threat:
            self.angle += self.angular_velocity * self.max_turn_speed * (30.0 / self.frame_rate)
            self.angle %= math.tau

            # Cache trig calculations and only calculate if moving
            if self.speed > 0.01:
                cos_angle = math.cos(self.angle)
                sin_angle = math.sin(self.angle)
                frame_speed = self.speed * (30.0 / self.frame_rate)
                self.x += cos_angle * frame_speed
                self.y += sin_angle * frame_speed
            
            self.energy -= self.energy_burn_base * (30.0 / self.frame_rate)
            self.energy = max(0, self.energy)
        else:   
            self.angular_velocity = 0
            decay_factor = 0.9 ** (30.0 / self.frame_rate)
            self.speed *= decay_factor
            self.energy += self.energy_regen
            self.energy = min(self.energy, self.max_energy)

        self.x %= self._screen_width
        self.y %= self._screen_height

        self._update_softbody_stretch()
        # self.avoid_neighbors(grid)
        
        # Check death conditions
        return self.should_die_naturally()


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
        # ✅ Reproduce based on energy level with slight randomization to prevent synchronization
        threshold = REPRODUCTION_ENERGY_THRESHOLD + random.uniform(-5, 5)
        return self.energy >= threshold
    
    def should_die_naturally(self):
        # Die from old age
        age_seconds = self.age / self.frame_rate
        if age_seconds >= MAX_AGE_SECONDS:
            return "old_age"
        
        # Die from starvation (energy depletion)
        if self.energy <= STARVATION_ENERGY:
            return "starvation"
            
        return None

    def clone(self):
        child = Prey(
            self.x + random.randint(-30, 30),
            self.y + random.randint(-30, 30),
            generation=self.generation + 1
        )
        child.parent_id = self.id
        child.brain = self.brain.copy_with_mutation(generation=self.generation)
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

        if random.random() < adaptive_mutation_probability(SPEED_MUTATION_PROB, self.generation):
            old_speed = self.max_speed
            child.max_speed = round(self.max_speed + random.uniform(0.3, 1), 2)
            if self.max_speed < child.max_speed:
                child.stretch += 0.3
                mutated = True
                # Track significant speed mutation (>10% change)
                if abs(child.max_speed - old_speed) / old_speed > 0.1:
                    child.mutations["s"] = [old_speed, child.max_speed]

        if random.random() < adaptive_mutation_probability(MAX_ENERGY_MUTATION_PROB, self.generation):
            old_energy = self.max_energy
            child.max_energy = round(self.max_energy + random.uniform(1, 3), 2)
            mutated = True
            # Track significant energy mutation (>5% change)
            if abs(child.max_energy - old_energy) / old_energy > 0.05:
                child.mutations["e"] = [old_energy, child.max_energy]

        # if random.random() < MAX_TURN_SPEED_MUTATION_PROB:
        #     child.max_turn_speed = round(self.max_turn_speed + random.uniform(0.5, 3), 2)
        #     mutated = True

        if random.random() < adaptive_mutation_probability(ENERGY_REGEN_MUTATION_PROB, self.generation):
            old_regen = self.energy_regen
            child.energy_regen = round(self.energy_regen + random.uniform(0.01, 0.05), 2)
            mutated = True
            # Track significant regen mutation (>10% change)
            if abs(child.energy_regen - old_regen) / old_regen > 0.1:
                child.mutations["r"] = [old_regen, child.energy_regen]

        if random.random() < adaptive_mutation_probability(MAX_ENERGY_MUTATION_PROB, self.generation):
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
        # Fitness tracking: record reproduction
        self.record_reproduction()
        return child
        
    def calculate_prey_fitness(self):
        """Calculate comprehensive fitness score for prey"""
        base_fitness = self.calculate_base_fitness()
        
        # Energy efficiency bonus
        if hasattr(self, 'energy'):
            energy_ratio = self.energy / self.max_energy
            energy_bonus = energy_ratio * 100  # Bonus for maintaining high energy
            base_fitness += energy_bonus
            
        # Age bonus (surviving longer is good for prey)
        age_bonus = (self.age / self.frame_rate) * 10  # 10 points per second survived
        base_fitness += age_bonus
        
        # Reproduction efficiency (children per time alive)
        if self.age > 0:
            repro_efficiency = (self.children_spawned / (self.age / self.frame_rate)) * 300
            base_fitness += repro_efficiency
            
        return base_fitness






