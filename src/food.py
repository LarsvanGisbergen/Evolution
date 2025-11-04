# src/food.py
import pygame
import config

class Food:
    def __init__(self, x, y, energy=50, radius=5):
        self.x = x
        self.y = y
        self.energy = energy
        self.radius = radius
        self.color = (100, 220, 100) # A light green color

    def draw(self, screen):
        """Draws the food pellet on the screen."""
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)