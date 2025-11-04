# main.py
import pygame
import config
from src.simulation import Simulation

def main():
    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("Evolution Blob Simulator")

    sim = Simulation(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
    sim.run(screen)

    pygame.quit()

if __name__ == '__main__':
    main()