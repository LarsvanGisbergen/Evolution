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
from blueprints import SPECIES_BLUEPRINTS

class Simulation:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # OPTIMIZATION: Initialize world with a cell size for the grid
        self.world = World(width, height, cell_size=config.WORLD_GRID_CELL_SIZE)
        self.is_running = False
        self.clock = pygame.time.Clock()
        self.tick_counter = 0
        self.target_tick_rate = config.FPS
        self.show_vision = False
        self.gui_manager = pygame_gui.UIManager((width, height))
        self.fps_font = pygame.font.SysFont("Arial", 18)
        
        slider_rect = pygame.Rect((10, 10), (200, 20))
        self.tick_rate_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=slider_rect, start_value=self.target_tick_rate,
            value_range=(1, 300), manager=self.gui_manager)
        label_rect = pygame.Rect((220, 10), (150, 20))
        self.tick_rate_label = pygame_gui.elements.UILabel(
            relative_rect=label_rect, text=f"Tick Rate: {self.target_tick_rate}",
            manager=self.gui_manager)
        vision_label_rect = pygame.Rect((width - 150, 10), (140, 20))
        self.vision_toggle_label = pygame_gui.elements.UILabel(
            relative_rect=vision_label_rect, text="Vision: OFF [V]",
            manager=self.gui_manager)
        self.population_data = defaultdict(list)
        self.graph_rect = pygame.Rect(config.GRAPH_X, config.GRAPH_Y, config.GRAPH_WIDTH, config.GRAPH_HEIGHT)
        
        for blueprint in SPECIES_BLUEPRINTS.values():
            for _ in range(blueprint["count"]):
                x, y = random.randint(0, width), random.randint(0, height)
                self.world.add_creature(BaseCreature(x=x, y=y, species_config=blueprint))
        
        self.spawn_food(amount=config.INITIAL_FOOD_COUNT)

    def spawn_food(self, amount=1):
        for _ in range(amount):
            x, y = random.randint(0, self.width), random.randint(0, self.height)
            self.world.add_food(Food(x, y, energy=config.FOOD_ENERGY))

    def log_population_data(self):
        total_creatures = len(self.world.creatures)
        if total_creatures == 0:
            for color in self.population_data:
                self.population_data[color].append(0)
                if len(self.population_data[color]) > config.GRAPH_MAX_POINTS: self.population_data[color].pop(0)
            return
        counts = defaultdict(int)
        for creature in self.world.creatures: counts[creature.color] += 1
        all_species = set(self.population_data.keys()).union(set(counts.keys()))
        for color in all_species:
            percentage = (counts[color] / total_creatures) * 100
            self.population_data[color].append(percentage)
            if len(self.population_data[color]) > config.GRAPH_MAX_POINTS: self.population_data[color].pop(0)

    def draw_population_graph(self, screen):
        pygame.draw.rect(screen, config.GRAPH_BG_COLOR, self.graph_rect)
        pygame.draw.rect(screen, config.GRAPH_AXIS_COLOR, self.graph_rect, 1)
        if not self.population_data: return
        for color, history in self.population_data.items():
            if len(history) < 2: continue
            points = []
            point_spacing = self.graph_rect.width / (config.GRAPH_MAX_POINTS - 1) if config.GRAPH_MAX_POINTS > 1 else 0
            for i, p in enumerate(history): points.append((self.graph_rect.x + i * point_spacing, self.graph_rect.bottom - (p / 100) * self.graph_rect.height))
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
            if event.type == pygame.QUIT: self.is_running = False
            self.gui_manager.process_events(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_v:
                    self.show_vision = not self.show_vision
                    self.vision_toggle_label.set_text("Vision: ON [V]" if self.show_vision else "Vision: OFF [V]")
            if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED and event.ui_element == self.tick_rate_slider:
                self.target_tick_rate = int(event.value)
                self.tick_rate_label.set_text(f"Tick Rate: {self.target_tick_rate}")

    def update(self, time_delta):
        self.gui_manager.update(time_delta)
        
        # OPTIMIZATION: Update the spatial grid once per frame
        self.world.update_grid()

        # Update creatures (their internal logic and movement)
        for creature in self.world.creatures:
            creature.update(self.world)
            self.world.handle_boundaries(creature)
        
        # OPTIMIZATION: Efficiently check for collisions using the grid
        checked_pairs = set()
        for creature_a in self.world.creatures:
            local_creatures = self.world.get_neighbors(creature_a, creature_a.radius * 2)['creatures']
            for creature_b in local_creatures:
                if creature_a is creature_b: continue
                pair = tuple(sorted([id(creature_a), id(creature_b)]))
                if pair in checked_pairs: continue
                
                dist = math.hypot(creature_a.x - creature_b.x, creature_a.y - creature_b.y)
                if dist < creature_a.radius + creature_b.radius:
                    creature_a.on_collide(creature_b, self.world)
                    creature_b.on_collide(creature_a, self.world)
                    checked_pairs.add(pair)
        
        # Handle eating
        eaten_food = []
        for creature in self.world.creatures:
            local_food = self.world.get_neighbors(creature, creature.radius)['food']
            for food_item in local_food:
                if food_item in eaten_food: continue
                dist = math.hypot(creature.x - food_item.x, creature.y - food_item.y)
                if dist < creature.radius + food_item.radius:
                    creature.energy += food_item.energy
                    if creature.energy > creature.max_energy: creature.energy = creature.max_energy
                    eaten_food.append(food_item)
                    break
        self.world.food = [f for f in self.world.food if f not in eaten_food]
        
        # Handle Reproduction and Deaths
        newborns = []
        for creature in self.world.creatures:
            if creature.energy >= creature.reproduction_threshold:
                children, total_cost = creature.reproduce()
                if children:
                    creature.energy -= total_cost
                    newborns.extend(children)
        self.world.creatures.extend(newborns)
        self.world.creatures = [c for c in self.world.creatures if c.is_alive()]
        
        # Spawn new food and log data
        self.tick_counter += 1
        # BUG FIX: Use correct config variables for food spawning
        if self.tick_counter % config.FOOD_SPAWN_INTERVAL == 0:
            self.spawn_food(amount=config.FOOD_SPAWN_AMOUNT)
        if self.tick_counter % config.GRAPH_UPDATE_RATE == 0:
            self.log_population_data()

    def draw(self, screen):
        screen.fill(config.COLOR_BG)
        self.world.draw(screen, self.show_vision)
        self.draw_population_graph(screen)
        self.gui_manager.draw_ui(screen)
        actual_fps = self.clock.get_fps()
        fps_text = f"FPS: {actual_fps:.0f}"
        fps_surface = self.fps_font.render(fps_text, True, (200, 200, 200))
        # UI TWEAK: Moved FPS counter to a cleaner position
        screen.blit(fps_surface, (10, 35))
        pygame.display.flip()