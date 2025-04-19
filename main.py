import math
import random
import pygame
from entities.prey import Prey
from entities.predator import Predator
from spatial_grid import SpatialGrid

pygame.init()

MAX_PREY = 350
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 800
GRID_CELL_SIZE = 80
VISION_THROTTLE = 3
NUM_STARTING_PREY = 50
NUM_STARTING_PREDATORS = 4

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Evolving AIs: Predator vs Prey")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)

last_info_update_time = 0
displayed_energy = 0
displayed_repro_seconds = 0


entities = []
predators = []
prey_list = []


for _ in range(NUM_STARTING_PREY):
    x, y = random.randint(100, 1100), random.randint(100, 700)
    prey = Prey(x, y)
    entities.append(prey)
    prey_list.append(prey)

for _ in range(NUM_STARTING_PREDATORS):
    x, y = random.randint(100, 1100), random.randint(100, 700)
    predator = Predator(x, y)
    entities.append(predator)
    predators.append(predator)

selected_entity = None
show_debug_panel = False
frame_count = 0
grid = SpatialGrid(SCREEN_WIDTH, SCREEN_HEIGHT, cell_size=GRID_CELL_SIZE)

running = True
while running:
    frame_count += 1
    screen.fill((30, 30, 30))
    grid.clear()
    for e in entities:
        grid.add_entity(e)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            for e in reversed(entities):
                dx, dy = mx - e.x, my - e.y
                if dx * dx + dy * dy <= e.radius * e.radius:
                    selected_entity = e
                    break
            else:
                selected_entity = None
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_d and pygame.key.get_mods() & pygame.KMOD_ALT:
                show_debug_panel = not show_debug_panel

    if frame_count % VISION_THROTTLE == 0:
        for e in entities:
            neighbors = grid.get_neighbors(e)
            nearby = []

            view_range_sq = e.view_range * e.view_range
            detect_type = Predator if isinstance(e, Prey) else Prey if isinstance(e, Predator) else None

            for o in neighbors:
                if o is e:
                    continue
                if detect_type and not isinstance(o, detect_type):
                    continue
                dx = o.x - e.x
                dy = o.y - e.y
                if dx * dx + dy * dy <= view_range_sq + o.radius * o.radius:
                    nearby.append(o)

            e.cast_vision(nearby)


    new_entities = []
    removed_prey = []
    for e in entities:
        if isinstance(e, Prey):
            e.age += 1
            e.update(grid)
            if e.should_reproduce():
                e.energy -= e.reproduce_energy_cost
                if len(prey_list) >= MAX_PREY:
                    continue
                child = e.clone()
                new_entities.append(child)
                e.children_spawned += 1
                e.time_at_max_energy = 0
        elif isinstance(e, Predator):
            outcome, target = e.update(frame_count, prey_list)
            if outcome == "eat":
                for p in target:
                    if p in entities:
                        removed_prey.append(p)
            elif outcome == "reproduce":
                if target in entities:
                    removed_prey.append(target)
                child = e.clone()
                e.children_spawned += 1
                new_entities.append(child)
            elif outcome == "die":
                if target in predators:
                    predators.remove(target)
                if target in entities:
                    entities.remove(target)

    for p in removed_prey:
        if p in prey_list:
            prey_list.remove(p)
        if p in entities:
            entities.remove(p)

    for n in new_entities:
        entities.append(n)
        if isinstance(n, Prey):
            prey_list.append(n)
        else:
            predators.append(n)

    if frame_count % 5 == 0:
        for e in entities:
            neighbors = grid.get_neighbors(e)
            e.resolve_collisions(neighbors)

    for e in entities:
        e.draw(screen, selected=(e == selected_entity))

    if selected_entity:
        lines = [
            f"Gen: {selected_entity.generation}"
        ]
        if isinstance(selected_entity, Prey):
            if frame_count - last_info_update_time > 60:
                displayed_energy = round(selected_entity.energy)
                if displayed_energy >= selected_entity.max_energy:
                    remaining_frames = max(0, selected_entity.reproduce_threshold - selected_entity.time_at_max_energy)
                    displayed_repro_seconds = round(remaining_frames / 60)
                else:
                    displayed_repro_seconds = -1
                last_info_update_time = frame_count

            lines += [
                f"Energy: {displayed_energy} / {selected_entity.max_energy}",
                f"Reproduce In: {displayed_repro_seconds}s" if displayed_repro_seconds >= 0 else "Reproduce In: waiting...",
                f"Children: {selected_entity.children_spawned}"
            ]

        elif isinstance(selected_entity, Predator):
            time_to_starve = max(0, selected_entity.starvation_threshold - selected_entity.time_since_last_meal) // 60
            lines += [
                f"Age: {selected_entity.age // 60}s",
                f"Prey Eaten: {selected_entity.prey_eaten}",
                f"Children: {selected_entity.children_spawned}",
                f"Time to Starvation: {time_to_starve}s"
            ]

        panel_width = 260
        panel_height = 20 + len(lines) * 20
        panel_x = SCREEN_WIDTH - panel_width - 10
        panel_y = SCREEN_HEIGHT - panel_height - 10
        pygame.draw.rect(screen, (50, 50, 50), (panel_x, panel_y, panel_width, panel_height))
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, (255, 255, 255))
            screen.blit(text_surface, (panel_x + 10, panel_y + 10 + i * 20))

    if show_debug_panel:
        fps = int(clock.get_fps())
        stats = [
            f"FPS: {fps}",
            f"Prey: {len(prey_list)}",
            f"Predators: {len(predators)}"
        ]
        for i, line in enumerate(stats):
            surf = font.render(line, True, (255, 255, 255))
            screen.blit(surf, (SCREEN_WIDTH - 180, 10 + i * 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
