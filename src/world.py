# src/world.py
import pygame
from collections import defaultdict

class World:
    def __init__(self, width, height, cell_size=100):
        self.width = width
        self.height = height
        self.creatures = []
        self.food = []
        
        # --- NEW: Spatial Partitioning Grid ---
        self.cell_size = cell_size
        self.grid = defaultdict(lambda: {'creatures': [], 'food': []})

    def add_creature(self, creature):
        self.creatures.append(creature)

    def add_food(self, food_item):
        self.food.append(food_item)

    def _get_cell_coords(self, x, y):
        """Converts world coordinates to grid cell coordinates."""
        return int(x // self.cell_size), int(y // self.cell_size)

    def update_grid(self):
        """Clears and rebuilds the grid with current object positions each frame."""
        self.grid.clear()
        for creature in self.creatures:
            cell_coords = self._get_cell_coords(creature.x, creature.y)
            self.grid[cell_coords]['creatures'].append(creature)
        for food_item in self.food:
            cell_coords = self._get_cell_coords(food_item.x, food_item.y)
            self.grid[cell_coords]['food'].append(food_item)

    def get_neighbors(self, entity, radius):
        """Gets all entities within a given radius of another entity using the grid."""
        neighbors = {'creatures': [], 'food': []}
        center_cell = self._get_cell_coords(entity.x, entity.y)
        
        search_radius_in_cells = int(radius // self.cell_size) + 1
        
        for dx in range(-search_radius_in_cells, search_radius_in_cells + 1):
            for dy in range(-search_radius_in_cells, search_radius_in_cells + 1):
                cell_x, cell_y = center_cell[0] + dx, center_cell[1] + dy
                cell = self.grid.get((cell_x, cell_y))
                if cell:
                    neighbors['creatures'].extend(cell['creatures'])
                    neighbors['food'].extend(cell['food'])
        return neighbors

    def handle_boundaries(self, creature):
        creature.x = creature.x % self.width
        creature.y = creature.y % self.height

    def draw(self, screen, show_vision=False):
        """Draws all objects in the world."""
        for food_item in self.food:
            food_item.draw(screen)
        for creature in self.creatures:
            creature.draw(screen, show_vision)