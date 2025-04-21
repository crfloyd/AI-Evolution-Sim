import math
import pygame
import random
from entities.base_entity import BaseEntity
from entities.neural_network import NeuralNetwork
from utils import hue_shifted_color


MAX_SPEED = 4.0
EAT_COOLDOWN_FRAMES_MULTIPLIER = 1
REQUIRED_EATS_TO_REPRODUCE = 3
STARVATION_THRESHOLD_SECONDS = 20
STARTING_ENERGY = 100
MAX_ENERGY = 100
ENERGY_BURN_RATE = 0.15

class Predator(BaseEntity):
    def __init__(self, x, y, generation=0, frame_rate=30):
        self.num_rays = 7
        super().__init__(x, y, entity_type="predator")
        self.frame_rate = frame_rate
        self.fov = math.radians(90)
        self.view_range = 250
        self.color = (255, 80, 80)
        self.radius = 12
        self.generation = generation

        self.brain = NeuralNetwork(input_size=self.num_rays + 2)
        self.brain.b2[0] = 0.0  # no turn


        self.speed = 0
        self.max_speed = MAX_SPEED
        self.max_turn_speed = 0.15

        self.frames_since_prey_seen = 9999
        self.prey_eaten = 0
        self.children_spawned = 0
        self.age = 0
        self.last_eat_time = -1000
        self.eat_cooldown_frames = frame_rate * EAT_COOLDOWN_FRAMES_MULTIPLIER
        self.required_eats_to_reproduce = REQUIRED_EATS_TO_REPRODUCE
        self.time_since_last_meal = 0
        self.starvation_threshold = STARVATION_THRESHOLD_SECONDS * frame_rate

        self.energy = STARTING_ENERGY
        self.max_energy = MAX_ENERGY
        self.energy_burn_base = ENERGY_BURN_RATE
        self.vision_hits = ["none"] * self.num_rays


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
        prey_memory = max(0.0, 1.0 - self.frames_since_prey_seen / 60.0)

        # vision_input = self.vision + [1.0]
        see_nothing = 1.0 if all(hit == "none" for hit in self.vision_hits) else 0.0
        vision_input = self.vision + [see_nothing, prey_memory]

        out = self.brain.forward(vision_input)
        self.angular_velocity = out[0] * 0.7
        speed_factor = (out[1] + 1) / 2
        self.speed = speed_factor * self.max_speed

        self.angle += self.angular_velocity * self.max_turn_speed
        self.angle %= math.tau
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

        screen_width, screen_height = pygame.display.get_surface().get_size()
        self.x %= screen_width
        self.y %= screen_height

        self._update_softbody_stretch()

        # Burn energy
        self.energy -= self.energy_burn_base
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
                    if frame_count - self.last_eat_time > self.eat_cooldown_frames:
                        self.prey_eaten += 1
                        self.last_eat_time = frame_count
                        self.time_since_last_meal = 0
                        self.energy = min(self.energy + 30, self.max_energy)

                        if self.prey_eaten >= self.required_eats_to_reproduce:
                            self.prey_eaten = 0
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
        child.brain = self.brain.copy_with_mutation(mutation_rate=0.05)
        return child
    
    def clone(self):
        child = Predator(
            self.x + random.randint(-10, 10),
            self.y + random.randint(-10, 10),
            generation=self.generation + 1,
            frame_rate=self.frame_rate
        )
        child.brain = self.brain.copy_with_mutation(mutation_rate=0.05)

        # Mutate physical traits
        child.max_speed = max(1.0, round(self.max_speed + random.gauss(0, 0.1), 2))
        child.max_turn_speed = max(0.05, round(self.max_turn_speed + random.gauss(0, 0.01), 3))
        child.stretch = max(0.5, round(self.stretch + random.gauss(0, 0.01), 3))
        if child.stretch > self.stretch: 
            hue = max(0, 0.6 - 0.6 * child.stretch)
            child.color = hue_shifted_color(hue)
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