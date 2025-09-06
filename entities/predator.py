import math
import pygame
import random
from entities.base_entity import BaseEntity
from entities.neural_network import NeuralNetwork
from utils import hue_shifted_color, sanitize_color

# Import centralized frame rate constant
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from main import FRAME_RATE
except ImportError:
    FRAME_RATE = 60  # Fallback if import fails


MAX_SPEED = 4.0
EAT_COOLDOWN_FRAMES_MULTIPLIER = 0.5
REQUIRED_EATS_TO_REPRODUCE = 5
STARVATION_THRESHOLD_SECONDS = 12
STARTING_ENERGY = 100
MAX_ENERGY = 100
ENERGY_BURN_RATE = 0.15


def adaptive_mutation_probability(base_prob, generation):
    """Calculate adaptive mutation probability based on generation"""
    if generation <= 2:
        return base_prob * 1.8  # Higher early exploration
    elif generation <= 5:
        return base_prob * 1.3  # Medium exploration
    else:
        return base_prob * 0.8  # Lower fine-tuning

class Predator(BaseEntity):
    def __init__(self, x, y, generation=0, frame_rate=FRAME_RATE, num_rays=7):
        self.num_rays = num_rays
        @property
        def num_rays(self):
            return self._num_rays
        super().__init__(x, y, entity_type="predator")
        
        # Initialize fitness tracking
        self.fitness_stats['birth_frame'] = 0  # Will be set when added to simulation
        self.fitness_stats['prey_caught'] = 0
        self.fitness_stats['hunt_attempts'] = 0
        self.frame_rate = frame_rate
        self.fov = math.radians(90)
        self.view_range = 250
        self.color = (255, 80, 80)
        self.radius = 12
        self.generation = generation

        self.brain = NeuralNetwork(input_size=self.num_rays + 3, hidden_size=10)  # Predator: focused brain for hunting
        self.brain.b2[0] = 0.0  # no turn


        self.speed = 0
        self.max_speed = MAX_SPEED
        self.max_turn_speed = 0.15

        self.frames_since_prey_seen = 9999
        self.prey_eaten = 0
        self.children_spawned = 0
        self.age = 0
        self.visual_traits = []
        self.last_eat_time = -1000
        self.eat_cooldown_frames = frame_rate * EAT_COOLDOWN_FRAMES_MULTIPLIER
        self.required_eats_to_reproduce = REQUIRED_EATS_TO_REPRODUCE
        self.time_since_last_meal = 0
        self.starvation_threshold = STARVATION_THRESHOLD_SECONDS * frame_rate

        self.energy = STARTING_ENERGY
        self.max_energy = MAX_ENERGY
        self.energy_burn_base = ENERGY_BURN_RATE
        self.vision_hits = ["none"] * self.num_rays
        self.vision = [1.0] * self.num_rays 


    def update(self, frame_count, prey_list):
        self.age += 1
        # === Track prey memory ===
        sees_prey = any(ray < 0.7 and hit == "prey"
                        for ray, hit in zip(self.vision, self.vision_hits))

        if sees_prey:
            self.frames_since_prey_seen = 0
        else:
            self.frames_since_prey_seen += 1

        # Normalize memory into a value from 1.0 (just saw prey) to 0.0 (forgotten)
        prey_memory = max(0.0, 1.0 - self.frames_since_prey_seen / (2 * self.frame_rate))  # fades over 2 seconds

        # vision_input = self.vision + [1.0]
        see_nothing = 1.0 if all(hit == "none" for hit in self.vision_hits) else 0.0
        prey_count = sum(1 for hit in self.vision_hits if hit == "prey") / self.num_rays
        vision_input = self.vision + [see_nothing, prey_memory, prey_count]

        out = self.brain.forward(vision_input)
        self.angular_velocity = out[0] * 0.7
        speed_factor = (out[1] + 1) / 2
        self.speed = speed_factor * self.max_speed

        self.angle += self.angular_velocity * self.max_turn_speed * (30.0 / self.frame_rate)
        self.angle %= math.tau
        self.x += math.cos(self.angle) * self.speed * (30.0 / self.frame_rate)
        self.y += math.sin(self.angle) * self.speed * (30.0 / self.frame_rate)

        screen_width, screen_height = pygame.display.get_surface().get_size()
        self.x %= screen_width
        self.y %= screen_height

        self._update_softbody_stretch()

        self.energy -= self.energy_burn_base * (30.0 / self.frame_rate)
        self.energy = max(0, self.energy)

        if frame_count % 2 == 0:
            eaten = []
            for prey in prey_list:
                dx = prey.x - self.x
                dy = prey.y - self.y
                dist = math.hypot(dx, dy)
                angle_to_prey = math.atan2(dy, dx)
                angle_diff = (angle_to_prey - self.angle + math.pi) % (2 * math.pi) - math.pi
                facing_prey = abs(angle_diff) < math.radians(60)

                if dist < self.radius + prey.radius and facing_prey:
                    # Fitness tracking: record hunt attempt
                    self.fitness_stats['hunt_attempts'] += 1
                    
                    if frame_count - self.last_eat_time > self.eat_cooldown_frames:
                        self.prey_eaten += 1
                        self.last_eat_time = frame_count
                        self.time_since_last_meal = 0
                        self.energy = min(self.energy + 30, self.max_energy)
                        
                        # Fitness tracking: record successful hunt
                        self.fitness_stats['prey_caught'] += 1

                        if self.prey_eaten >= self.required_eats_to_reproduce:
                            self.prey_eaten = 0
                            # Fitness tracking: record reproduction
                            self.record_reproduction()
                            return "reproduce", prey

                    eaten.append(prey)

            if eaten:
                return "eat", eaten

        self.time_since_last_meal += 1
        if self.time_since_last_meal >= self.starvation_threshold or self.energy <= 0:
            return "die", self

        return None, None

    
    def clone(self):
        child = Predator(
            self.x + random.randint(-10, 10),
            self.y + random.randint(-10, 10),
            generation=self.generation + 1,
            frame_rate=self.frame_rate
        )
        child.parent_id = self.id
        child.mutations = {}

        if random.random() < adaptive_mutation_probability(0.02, self.generation):  # Adaptive vision mutation rate
            old_rays = self.num_rays
            child.num_rays = min(30, self.num_rays + random.choice([1, 2]))
            child.vision = [1.0] * child.num_rays
            child.vision_hits = ["none"] * child.num_rays
            child.brain = self.brain.resize_input(new_num_inputs=child.num_rays + 3)
            child.visual_traits.append("vision")
            # Track vision mutation
            if child.num_rays != old_rays:
                child.mutations["v"] = [old_rays, child.num_rays]
        else:
            child.num_rays = self.num_rays
            child.vision = [1.0] * child.num_rays
            child.vision_hits = ["none"] * child.num_rays
            child.brain = self.brain.copy_with_mutation(num_rays=child.num_rays + 3, generation=self.generation)

        # Track neural mutations if significant (>0.01 strength)
        if hasattr(child.brain, '_mutation_strength') and child.brain._mutation_strength > 0.01:
            child.mutations["n"] = round(child.brain._mutation_strength, 3)

        child.vision_hits = ["none"] * child.num_rays

        # Mutate physical traits
        old_speed = self.max_speed
        child.max_speed = max(1.0, round(self.max_speed + random.gauss(0, 0.1), 2))
        if abs(child.max_speed - old_speed) / old_speed > 0.1:
            child.mutations["s"] = [old_speed, child.max_speed]
            
        old_turn = self.max_turn_speed
        child.max_turn_speed = max(0.05, round(self.max_turn_speed + random.gauss(0, 0.01), 3))
        if abs(child.max_turn_speed - old_turn) / old_turn > 0.1:
            child.mutations["t"] = [old_turn, child.max_turn_speed]
            
        child.stretch = max(0.5, round(self.stretch + random.gauss(0, 0.01), 3))
        if child.stretch > self.stretch:
            child.color = hue_shifted_color(self.color, 0.1)
            
        old_energy = self.max_energy
        child.max_energy = max(100, int(self.max_energy + random.gauss(0, 10)))
        if abs(child.max_energy - old_energy) / old_energy > 0.05:
            child.mutations["e"] = [old_energy, child.max_energy]

        return child



        

        # Mutate physical traits
        child.max_speed = max(1.0, round(self.max_speed + random.gauss(0, 0.1), 2))
        child.max_turn_speed = max(0.05, round(self.max_turn_speed + random.gauss(0, 0.01), 3))
        child.stretch = max(0.5, round(self.stretch + random.gauss(0, 0.01), 3))
        if child.stretch > self.stretch:
            child.color = hue_shifted_color(self.color, 0.1)
        child.max_energy = max(100, int(self.max_energy + random.gauss(0, 10)))

        # child.view_range = max(50, int(self.view_range + random.gauss(0, 5)))
        # child.fov = max(math.radians(30), min(math.radians(180), self.fov + random.gauss(0, math.radians(5))))

        return child


    def avoid_neighbors(self, grid):
        if self.neighbor_avoid_timer > 0:
            self.neighbor_avoid_timer -= 1
            return
        self.neighbor_avoid_timer = 4
        neighbors = grid.get_neighbors(self)
        for other in neighbors:
            if other is self or not isinstance(other, Predator):
                continue
            dx = self.x - other.x
            dy = self.y - other.y
            dist = math.hypot(dx, dy)
            if dist < self.radius * 2 and dist > 0:
                repel_angle = math.atan2(dy, dx)
                self.angle += 0.05 * math.sin(repel_angle - self.angle)

    def draw_overlay(self, surface):
        if "vision" in self.visual_traits:
            import time
            pulse = 100 + int(80 * (1 + math.sin(time.time() * 4)))  # fast pulsating
            color = (pulse, pulse, 0)  # glowing yellow
            pygame.draw.circle(surface, sanitize_color(color), (int(self.x), int(self.y)), self.radius + 4, 2)
            
    def calculate_predator_fitness(self):
        """Calculate comprehensive fitness score for predator"""
        base_fitness = self.calculate_base_fitness()
        
        # Hunting efficiency bonus
        hunt_success_rate = 0.0
        if self.fitness_stats['hunt_attempts'] > 0:
            hunt_success_rate = self.fitness_stats['prey_caught'] / self.fitness_stats['hunt_attempts']
            hunt_efficiency_bonus = hunt_success_rate * 400  # Major bonus for hunting efficiency
            base_fitness += hunt_efficiency_bonus
            
        # Prey caught bonus (absolute hunting success)
        prey_bonus = self.fitness_stats['prey_caught'] * 200  # 200 points per prey caught
        base_fitness += prey_bonus
        
        # Age bonus (surviving longer is good)
        age_bonus = (self.age / self.frame_rate) * 15  # 15 points per second survived
        base_fitness += age_bonus
        
        # Reproduction efficiency bonus
        if self.age > 0:
            repro_efficiency = (self.children_spawned / (self.age / self.frame_rate)) * 500
            base_fitness += repro_efficiency
            
        return base_fitness

    