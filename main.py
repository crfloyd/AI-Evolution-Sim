import pygame
from entities.base_entity import BaseEntity

pygame.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Evolving AIs: Predator vs Prey")

clock = pygame.time.Clock()
entity = BaseEntity(x=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2)

running = True
while running:
    screen.fill((30, 30, 30))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    entity.update()
    entity.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
