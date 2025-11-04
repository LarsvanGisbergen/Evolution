# src/simulation.py
import pygame
import random
import math
from collections import defaultdict
from src.world import World
from src.creatures.base_creature import BaseCreature
from src.food import Food
import config
import pygame_gui

class Simulation:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.world = World(width, height)
        self.is_running = False
        self.clock = pygame.time.Clock()
        self.tick_counter = 0
        self.target_tick_rate = config.FPS

        # --- GUI SETUP ---
        self.gui_manager = pygame_gui.UIManager((width, height))
        slider_rect = pygame.Rect((10, 10), (200, 20))
        self.tick_rate_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=slider_rect,
            start_value=self.target_tick_rate,
            value_range=(1, 300),
            manager=self.gui_manager
        )
        label_rect = pygame.Rect((220, 10), (150, 20))
        self.tick_rate_label = pygame_gui.elements.UILabel(
            relative_rect=label_rect,
            text=f"Tick Rate: {self.target_tick_rate}",
            manager=self.gui_manager
        )
        
        # --- Graph data storage ---
        self.population_data = defaultdict(list)
        self.graph_rect = pygame.Rect(config.GRAPH_X, config.GRAPH_Y, config.GRAPH_WIDTH, config.GRAPH_HEIGHT)
        
        # --- Populate with distinct species ---
        species_colors = [(200, 50, 50), (50, 200, 50), (50, 50, 200)]
        creatures_per_species = config.INITIAL_CREATURE_COUNT // len(species_colors)
        for color in species_colors:
            for _ in range(creatures_per_species):
                x = random.randint(0, width)
                y = random.randint(0, height)
                self.world.add_creature(BaseCreature(x=x, y=y, color=color))
        
        for _ in range(config.INITIAL_FOOD_COUNT):
            self.spawn_food()

    def spawn_food(self):
        x = random.randint(0, self.width)
        y = random.randint(0, self.height)
        self.world.add_food(Food(x, y, energy=config.FOOD_ENERGY))

    def log_population_data(self):
        total_creatures = len(self.world.creatures)
        if total_creatures == 0:
            # Continue logging zeros for existing species so lines go to the bottom
            for color in self.population_data:
                self.population_data[color].append(0)
                if len(self.population_data[color]) > config.GRAPH_MAX_POINTS:
                    self.population_data[color].pop(0)
            return

        counts = defaultdict(int)
        for creature in self.world.creatures:
            counts[creature.color] += 1
        
        all_species = set(self.population_data.keys()).union(set(counts.keys()))
        for color in all_species:
            percentage = (counts[color] / total_creatures) * 100
            self.population_data[color].append(percentage)
            if len(self.population_data[color]) > config.GRAPH_MAX_POINTS:
                self.population_data[color].pop(0)

    def draw_population_graph(self, screen):
        pygame.draw.rect(screen, config.GRAPH_BG_COLOR, self.graph_rect)
        pygame.draw.rect(screen, config.GRAPH_AXIS_COLOR, self.graph_rect, 1)

        if not self.population_data:
            return

        for color, history in self.population_data.items():
            if len(history) < 2:
                continue

            points = []
            num_points_to_draw = len(history)
            
            # Prevent division by zero if there's only one data point
            point_spacing = self.graph_rect.width / (config.GRAPH_MAX_POINTS - 1) if config.GRAPH_MAX_POINTS > 1 else 0

            for i in range(num_points_to_draw):
                x = self.graph_rect.x + i * point_spacing
                y = self.graph_rect.bottom - (history[i] / 100) * self.graph_rect.height
                points.append((x, y))
            
            pygame.draw.lines(screen, color, False, points, 2)

    def run(self, screen):
        self.is_running = True
        while self.is_running:
            time_delta = self.clock.tick(self.target_tick_rate) / 1000.0
            self.handle_events()
            self.update(time_delta)
            self.draw(screen)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False

            self.gui_manager.process_events(event)

            if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_element == self.tick_rate_slider:
                    self.target_tick_rate = int(event.value)
                    self.tick_rate_label.set_text(f"Tick Rate: {self.target_tick_rate}")

    def update(self, time_delta):
        self.gui_manager.update(time_delta)
        
        for creature in self.world.creatures:
            creature.update(self.world)
            self.world.handle_boundaries(creature)

        eaten_food = []
        for creature in self.world.creatures:
            for food_item in self.world.food:
                if food_item in eaten_food: continue
                dist = math.hypot(creature.x - food_item.x, creature.y - food_item.y)
                if dist < creature.radius + food_item.radius:
                    creature.energy += food_item.energy
                    if creature.energy > config.CREATURE_MAX_ENERGY:
                        creature.energy = config.CREATURE_MAX_ENERGY
                    eaten_food.append(food_item)
                    break
        self.world.food = [f for f in self.world.food if f not in eaten_food]

        survivors = []
        for creature in self.world.creatures:
            if creature.is_alive():
                survivors.append(creature)
        self.world.creatures = survivors
        
        self.tick_counter += 1
        if self.tick_counter % config.FOOD_SPAWN_RATE == 0:
            self.spawn_food()

        if self.tick_counter % config.GRAPH_UPDATE_RATE == 0:
            self.log_population_data()

    def draw(self, screen):
        screen.fill(config.COLOR_BG)
        self.world.draw(screen)
        self.draw_population_graph(screen)
        self.gui_manager.draw_ui(screen)
        pygame.display.flip()