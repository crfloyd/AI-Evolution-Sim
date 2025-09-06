import math
import random
import pygame
import sys
import argparse
import json
import time
import signal
import atexit
from entities.prey import Prey
from entities.predator import Predator
from spatial_grid import SpatialGrid




# Parse command line arguments
parser = argparse.ArgumentParser(description='Evolutionary AI Simulation')
parser.add_argument('--presentation-mode', action='store_true', help='Enable presentation mode')
args = parser.parse_args()

pygame.init()

MAX_PREY = 500
SCREEN_WIDTH, SCREEN_HEIGHT = 1440, 1000
# SCREEN_WIDTH, SCREEN_HEIGHT = 500, 500
FRAME_RATE = 30
GRID_CELL_SIZE = 50
VISION_THROTTLE = 3
NUM_STARTING_PREY = 250
NUM_STARTING_PREDATORS = 5


screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Evolving AIs: Predator vs Prey")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)

last_info_update_time = 0
displayed_energy = 0
displayed_repro_seconds = 0

# Presentation system for YouTube-style intro
presentation_mode = args.presentation_mode
presentation_step = 0
paused = args.presentation_mode  # Only start paused if in presentation mode
show_stats = True

# Data logging setup
simulation_data = {
    "start_time": time.time(),
    "frame_data": [],
    "events": []
}
log_interval = 30  # Log every 30 frames (1 second at 30fps)
last_save_time = time.time()
save_interval = 30  # Save to disk every 30 seconds (not every 10 seconds)

def save_simulation_data():
    """Save simulation data to file - called on exit or periodically"""
    try:
        with open("simulation_log.json", "w") as f:
            json.dump(simulation_data, f, indent=2)
        print(f"Simulation data saved to simulation_log.json ({len(simulation_data['events'])} events)")
    except Exception as e:
        print(f"Error saving simulation data: {e}")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nSaving simulation data before exit...")
    save_simulation_data()
    pygame.quit()
    sys.exit(0)

# Register exit handlers
signal.signal(signal.SIGINT, signal_handler)
atexit.register(save_simulation_data)

# Fonts for presentation
title_font = pygame.font.Font(None, 84)
subtitle_font = pygame.font.Font(None, 48)
text_font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 28)


entities = []
predators = []
prey_list = []


for _ in range(NUM_STARTING_PREY):
    x, y = random.randint(100, SCREEN_WIDTH - 100), random.randint(100, SCREEN_HEIGHT - 100)
    prey = Prey(x, y, FRAME_RATE)
    entities.append(prey)
    prey_list.append(prey)

for _ in range(NUM_STARTING_PREDATORS):
    x, y = random.randint(100, 1100), random.randint(100, 700)
    predator = Predator(x, y, FRAME_RATE)
    entities.append(predator)
    predators.append(predator)

selected_entity = None
show_debug_panel = False
frame_count = 0
grid = SpatialGrid(SCREEN_WIDTH, SCREEN_HEIGHT, cell_size=GRID_CELL_SIZE)

def log_simulation_data():
    """Collect and log current simulation state"""
    if frame_count % log_interval != 0:
        return
    
    # Calculate stats
    prey_generations = [p.generation for p in prey_list] if prey_list else [0]
    pred_generations = [p.generation for p in predators] if predators else [0]
    
    prey_energies = [p.energy for p in prey_list] if prey_list else [0]
    prey_max_speeds = [p.max_speed for p in prey_list] if prey_list else [0]
    pred_max_speeds = [p.max_speed for p in predators] if predators else [0]
    
    frame_data = {
        "frame": frame_count,
        "time_seconds": frame_count // FRAME_RATE,
        "populations": {
            "prey_count": len(prey_list),
            "predator_count": len(predators)
        },
        "generations": {
            "prey_avg": sum(prey_generations) / len(prey_generations),
            "prey_max": max(prey_generations),
            "predator_avg": sum(pred_generations) / len(pred_generations),
            "predator_max": max(pred_generations)
        },
        "traits": {
            "prey_energy": {
                "avg": sum(prey_energies) / len(prey_energies) if prey_energies else 0,
                "min": min(prey_energies) if prey_energies else 0,
                "max": max(prey_energies) if prey_energies else 0
            },
            "prey_speed": {
                "avg": sum(prey_max_speeds) / len(prey_max_speeds) if prey_max_speeds else 0,
                "min": min(prey_max_speeds) if prey_max_speeds else 0,
                "max": max(prey_max_speeds) if prey_max_speeds else 0
            },
            "predator_speed": {
                "avg": sum(pred_max_speeds) / len(pred_max_speeds) if pred_max_speeds else 0,
                "min": min(pred_max_speeds) if pred_max_speeds else 0,
                "max": max(pred_max_speeds) if pred_max_speeds else 0
            }
        }
    }
    
    simulation_data["frame_data"].append(frame_data)
    
    # Periodic save to disk (much less frequent)
    global last_save_time
    current_time = time.time()
    if current_time - last_save_time > save_interval:
        save_simulation_data()
        last_save_time = current_time

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
            if presentation_mode:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    presentation_step += 1
                    if presentation_step > 6:  # Total number of presentation screens
                        presentation_mode = False
                        paused = False
            else:
                if event.key == pygame.K_d and pygame.key.get_mods() & pygame.KMOD_ALT:
                    show_debug_panel = not show_debug_panel
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_s:
                    show_stats = not show_stats

    # Only update simulation when not paused
    if not paused:
        if frame_count % VISION_THROTTLE == 0:
            for e in entities:
                neighbors = grid.get_neighbors(e, radius=e.view_range)
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
                    if len(prey_list) >= MAX_PREY:
                        continue
                    child = e.clone()
                    new_entities.append(child)
                    e.children_spawned += 1
                    e.time_at_max_energy = 0
            elif isinstance(e, Predator):
                outcome, target = e.update(frame_count, prey_list)
                if outcome == "eat":
                    # Log hunt success - compact format
                    simulation_data["events"].append([
                        frame_count, "hunt", e.id, e.generation, 
                        len([p for p in target if p in entities])
                    ])
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
                    # Log predator death - compact format  
                    simulation_data["events"].append([
                        frame_count, "death_pred", target.id, target.generation,
                        target.age // FRAME_RATE, target.prey_eaten
                    ])
                    if target in predators:
                        predators.remove(target)
                    if target in entities:
                        entities.remove(target)

        # Log prey death events - compact format
        for p in removed_prey:
            simulation_data["events"].append([
                frame_count, "death_prey", p.id, p.generation,
                p.age // FRAME_RATE, int(p.energy), p.children_spawned
            ])
            if p in prey_list:
                prey_list.remove(p)
            if p in entities:
                entities.remove(p)

        # Log birth events - compact format
        for child in new_entities:
            birth_event = [
                frame_count, "birth_prey" if isinstance(child, Prey) else "birth_pred",
                child.id, child.parent_id, child.generation
            ]
            # Add mutations if any significant ones occurred
            if hasattr(child, 'mutations') and child.mutations:
                birth_event.append(child.mutations)
            simulation_data["events"].append(birth_event)

        for n in new_entities:
            entities.append(n)
            if isinstance(n, Prey):
                prey_list.append(n)
            else:
                predators.append(n)
                
        # Log simulation data
        log_simulation_data()

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
            energy_percent = 0
            if frame_count - last_info_update_time > 30:
                displayed_energy = round(selected_entity.energy)
                energy_percent = (displayed_energy / selected_entity.max_energy) * 100
                last_info_update_time = frame_count

            lines += [
                f"Energy: {displayed_energy} / {selected_entity.max_energy} ({energy_percent:.0f}%)",
                "Ready to Reproduce!" if selected_entity.should_reproduce() else "Charging...",
                f"Children: {selected_entity.children_spawned}"
            ]


        elif isinstance(selected_entity, Predator):
            time_to_starve = max(0, selected_entity.starvation_threshold - selected_entity.time_since_last_meal) // FRAME_RATE
            lines += [
                f"Age: {selected_entity.age // FRAME_RATE}s",
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

    # Presentation system
    if presentation_mode:
        # Dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        # Center coordinates
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        
        if presentation_step == 0:
            # Title screen
            title = title_font.render("EVOLUTIONARY AI SIMULATION", True, (100, 200, 255))
            subtitle = subtitle_font.render("Predator vs Prey", True, (255, 100, 100))
            instruction = text_font.render("Press SPACE to continue", True, (200, 200, 200))
            
            screen.blit(title, (center_x - title.get_width() // 2, center_y - 100))
            screen.blit(subtitle, (center_x - subtitle.get_width() // 2, center_y - 40))
            screen.blit(instruction, (center_x - instruction.get_width() // 2, center_y + 100))
            
        elif presentation_step == 1:
            # Concept introduction
            title = subtitle_font.render("What you're about to see:", True, (255, 200, 100))
            lines = [
                "• AI creatures with neural network brains",
                "• They evolve through natural selection",
                "• Survivors pass traits to their offspring",
                "• Each generation gets smarter at survival"
            ]
            
            screen.blit(title, (center_x - title.get_width() // 2, center_y - 120))
            for i, line in enumerate(lines):
                text = text_font.render(line, True, (255, 255, 255))
                screen.blit(text, (center_x - text.get_width() // 2, center_y - 40 + i * 40))
            
            instruction = small_font.render("SPACE to continue", True, (150, 150, 150))
            screen.blit(instruction, (center_x - instruction.get_width() // 2, center_y + 120))
            
        elif presentation_step == 2:
            # Meet the prey
            title = subtitle_font.render("MEET THE PREY", True, (100, 200, 255))
            lines = [
                "Blue circles = Prey",
                "• Wide 360° vision to spot predators",
                "• Must gather energy to reproduce", 
                "• Evolve speed and evasion strategies"
            ]
            
            # Draw sample prey
            pygame.draw.circle(screen, (100, 200, 255), (center_x, center_y - 120), 12)
            pygame.draw.circle(screen, (50, 150, 255), (center_x, center_y - 120), 100, 2)  # Vision range
            
            screen.blit(title, (center_x - title.get_width() // 2, center_y - 200))
            for i, line in enumerate(lines):
                text = text_font.render(line, True, (255, 255, 255))
                screen.blit(text, (center_x - text.get_width() // 2, center_y - 40 + i * 30))
            
            instruction = small_font.render("SPACE to continue", True, (150, 150, 150))
            screen.blit(instruction, (center_x - instruction.get_width() // 2, center_y + 120))
            
        elif presentation_step == 3:
            # Meet the predators
            title = subtitle_font.render("MEET THE PREDATORS", True, (255, 80, 80))
            lines = [
                "Red circles = Predators",
                "• Narrow 90° forward vision for hunting",
                "• Must eat 3 prey to reproduce",
                "• Starve if they don't eat regularly"
            ]
            
            # Draw sample predator with vision cone
            pygame.draw.circle(screen, (255, 80, 80), (center_x, center_y - 120), 14)
            # Draw vision cone
            angle = 0
            fov = math.radians(90)
            vision_range = 120
            points = [(center_x, center_y - 120)]
            for i in range(int(math.degrees(fov)) + 1):
                a = angle - fov/2 + math.radians(i)
                x = center_x + math.cos(a) * vision_range
                y = (center_y - 120) + math.sin(a) * vision_range
                points.append((x, y))
            pygame.draw.polygon(screen, (100, 40, 40), points)
            
            screen.blit(title, (center_x - title.get_width() // 2, center_y - 200))
            for i, line in enumerate(lines):
                text = text_font.render(line, True, (255, 255, 255))
                screen.blit(text, (center_x - text.get_width() // 2, center_y - 40 + i * 30))
                
            instruction = small_font.render("SPACE to continue", True, (150, 150, 150))
            screen.blit(instruction, (center_x - instruction.get_width() // 2, center_y + 120))
            
        elif presentation_step == 4:
            # Evolution explanation
            title = subtitle_font.render("HOW EVOLUTION WORKS", True, (255, 200, 100))
            lines = [
                "• Each creature has a unique neural network brain",
                "• Successful survivors reproduce and pass traits",
                "• Offspring inherit parent traits with mutations",
                "• Over generations, populations adapt and improve"
            ]
            
            screen.blit(title, (center_x - title.get_width() // 2, center_y - 120))
            for i, line in enumerate(lines):
                text = text_font.render(line, True, (255, 255, 255))
                screen.blit(text, (center_x - text.get_width() // 2, center_y - 40 + i * 35))
            
            instruction = small_font.render("SPACE to continue", True, (150, 150, 150))
            screen.blit(instruction, (center_x - instruction.get_width() // 2, center_y + 120))
            
        elif presentation_step == 5:
            # What to watch for
            title = subtitle_font.render("WHAT TO WATCH FOR", True, (200, 255, 200))
            lines = [
                "• Prey learning to flee from predators",
                "• Predators developing hunting strategies", 
                "• Population dynamics and adaptation",
                "• Generation numbers increasing over time"
            ]
            
            screen.blit(title, (center_x - title.get_width() // 2, center_y - 120))
            for i, line in enumerate(lines):
                text = text_font.render(line, True, (255, 255, 255))
                screen.blit(text, (center_x - text.get_width() // 2, center_y - 40 + i * 35))
                
            instruction = small_font.render("SPACE to continue", True, (150, 150, 150))
            screen.blit(instruction, (center_x - instruction.get_width() // 2, center_y + 120))
            
        elif presentation_step == 6:
            # Ready to start
            title = subtitle_font.render("READY TO BEGIN!", True, (100, 255, 100))
            lines = [
                "Click on creatures to inspect their stats",
                "Watch the generation numbers increase",
                "Observe how behavior evolves over time"
            ]
            
            screen.blit(title, (center_x - title.get_width() // 2, center_y - 80))
            for i, line in enumerate(lines):
                text = text_font.render(line, True, (255, 255, 255))
                screen.blit(text, (center_x - text.get_width() // 2, center_y - 20 + i * 35))
                
            instruction = text_font.render("Press SPACE to start simulation!", True, (100, 255, 100))
            screen.blit(instruction, (center_x - instruction.get_width() // 2, center_y + 80))
    
    else:
        # Live simulation stats overlay
        if not paused and show_stats:
            avg_prey_gen = sum(p.generation for p in prey_list) / max(len(prey_list), 1)
            avg_pred_gen = sum(p.generation for p in predators) / max(len(predators), 1)
            
            stats_text = [
                f"Prey: {len(prey_list)} | Predators: {len(predators)}",
                f"Avg Generation - Prey: {avg_prey_gen:.1f} | Predators: {avg_pred_gen:.1f}",
                f"Time: {frame_count // FRAME_RATE}s"
            ]
            
            # Semi-transparent background
            stats_panel_height = len(stats_text) * 22 + 12
            stats_overlay = pygame.Surface((420, stats_panel_height))
            stats_overlay.set_alpha(150)
            stats_overlay.fill((20, 20, 20))
            screen.blit(stats_overlay, (SCREEN_WIDTH - 430, 20))
            
            for i, stat in enumerate(stats_text):
                stat_surface = small_font.render(stat, True, (200, 255, 200))
                screen.blit(stat_surface, (SCREEN_WIDTH - 420, 26 + i * 22))

    pygame.display.flip()
    clock.tick(FRAME_RATE)

pygame.quit()
