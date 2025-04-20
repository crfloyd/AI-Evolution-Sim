import math
import pygame
import random
from entities.base_entity import BaseEntity
from entities.neural_network import NeuralNetwork

MAX_SPEED = 2.0
EAT_COOLDOWN_FRAMES = 30
REQUIRED_EATS_TO_REPRODUCE = 3
STARVATION_THRESHOLD_FRAMES = 1000
STARTING_ENERGY = 100
MAX_ENERGY = 100
ENERGY_BURN_RATE = 0.03

class Predator(BaseEntity):
    def __init__(self, x, y, generation=0):
        self.num_rays = 7
        super().__init__(x, y)

        self.fov = math.radians(90)
        self.view_range = 250
        self.color = (255, 80, 80)
        self.radius = 12
        self.generation = generation

        self.brain = NeuralNetwork(input_size=self.num_rays + 1)
        self.brain.b2[0] = 0.0  # no turn


        self.speed = 0
        self.max_speed = MAX_SPEED
        self.max_turn_speed = 0.15

        self.prey_eaten = 0
        self.children_spawned = 0
        self.age = 0
        self.last_eat_time = -1000
        self.eat_cooldown_frames = EAT_COOLDOWN_FRAMES
        self.required_eats_to_reproduce = REQUIRED_EATS_TO_REPRODUCE
        self.time_since_last_meal = 0
        self.starvation_threshold = STARVATION_THRESHOLD_FRAMES

        self.energy = STARTING_ENERGY
        self.max_energy = MAX_ENERGY
        self.energy_burn_base = ENERGY_BURN_RATE
        self.vision_hits = ["none"] * self.num_rays


    def update(self, frame_count, prey_list):
        self.age += 1

        # vision_input = self.vision + [1.0]
        vision_input = self.vision + [1.0 if all(hit == "none" for hit in self.vision_hits) else 0.0]
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
            generation=self.generation + 1
        )
        child.brain = self.brain.copy_with_mutation(mutation_rate=0.05)
        return child

    def draw(self, screen, selected=False):
        angle_deg = math.degrees(self.angle)
        width = self.radius * 2 * self.stretch
        height = self.radius * 2 / self.stretch

        body = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.ellipse(body, self.color, (0, 0, width, height))
        rotated = pygame.transform.rotate(body, -angle_deg)
        rect = rotated.get_rect(center=(self.x, self.y))
        screen.blit(rotated, rect)

        eye_offset_angle = math.pi / 6
        eye_distance = self.radius * 0.8
        eye_radius = 4
        pupil_radius = 2

        for side in (-1, 1):
            eye_angle = self.angle + side * eye_offset_angle
            eye_x = self.x + math.cos(eye_angle) * eye_distance
            eye_y = self.y + math.sin(eye_angle) * eye_distance
            pygame.draw.circle(screen, (255, 255, 255), (int(eye_x), int(eye_y)), eye_radius)
            pygame.draw.circle(screen, (0, 0, 0), (int(eye_x), int(eye_y)), pupil_radius)

        if selected:
            pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), int(self.radius * self.stretch), width=2)
            self.draw_vision_rays(screen)

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