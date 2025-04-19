import random
import pygame
from entities.prey import Prey
from entities.predator import Predator


pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Evolving AIs: Predator vs Prey")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)
selected_entity = None

entities = [Prey(random.randint(100, 1100), random.randint(100, 700))]
entities = [
    Prey(300, 300),
    Predator(600, 400)
]


running = True
while running:
    screen.fill((30, 30, 30))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            for e in reversed(entities):
                if (mx - e.x) ** 2 + (my - e.y) ** 2 <= e.radius ** 2:
                    selected_entity = e
                    break
            else:
                selected_entity = None

    prey_list = [e for e in entities if isinstance(e, Prey)]
    predators = [e for e in entities if isinstance(e, Predator)]

    for e in entities:
        e.cast_vision(entities)

    for p in predators:
        p.update(prey_list)

    for prey in prey_list:
        prey.update()


    new_entities = []
    for e in entities:
        if isinstance(e, Prey) and e.should_reproduce():
            print(f"[SPLIT] Gen {e.generation} splitting after {e.time_at_max_energy} frames full energy")
            e.energy = e.max_energy / 2
            e.time_at_max_energy = 0
            e.settling_timer = 10
            child = e.clone()
            child.settling_timer = 10
            new_entities.append(child)
    entities.extend(new_entities)

    for e in entities:
        e.resolve_collisions(entities)
        e.draw(screen, selected=(e == selected_entity))

    if selected_entity and isinstance(selected_entity, Prey):
        info_lines = [
            f"Energy: {int(selected_entity.energy)} / {selected_entity.max_energy}",
            f"Time @ Max Energy: {selected_entity.time_at_max_energy} / 180",
            f"Generation: {selected_entity.generation}",
            f"Speed: {selected_entity.speed:.2f}"
        ]
        x, y = SCREEN_WIDTH - 260, SCREEN_HEIGHT - 100
        pygame.draw.rect(screen, (50, 50, 50), (x, y, 250, 90))
        for i, line in enumerate(info_lines):
            text = font.render(line, True, (255, 255, 255))
            screen.blit(text, (x + 10, y + 10 + i * 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
