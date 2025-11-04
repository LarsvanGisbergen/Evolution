# main.py
import pygame
import config
from src.simulation import Simulation

def main():
    pygame.init()
    flags = pygame.HWSURFACE | pygame.DOUBLEBUF
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags, vsync=0)
    pygame.display.set_caption("Evolution Blob Simulator")

    sim = Simulation(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
    sim.run(screen)

    pygame.quit()

if __name__ == '__main__':
    main()