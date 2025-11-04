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
        self.world = World(width, height)
        self.is_running = False
        self.clock = pygame.time.Clock()
        self.tick_counter = 0
        self.target_tick_rate = config.FPS
        self.show_vision = False

        # --- GUI SETUP ---
        self.gui_manager = pygame_gui.UIManager((width, height))
        self.fps_font = pygame.font.SysFont("Arial", 18)
        self.show_fps = True # You could add a key to toggle this too

        # Tick Rate Slider
        slider_rect = pygame.Rect((10, 10), (200, 20))
        self.tick_rate_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=slider_rect,
            start_value=self.target_tick_rate,
            value_range=(1, 300),
            manager=self.gui_manager
        )
        # Tick Rate Label
        label_rect = pygame.Rect((220, 10), (150, 20))
        self.tick_rate_label = pygame_gui.elements.UILabel(
            relative_rect=label_rect,
            text=f"Tick Rate: {self.target_tick_rate}",
            manager=self.gui_manager
        )
        
        # Vision Toggle Label
        vision_label_rect = pygame.Rect((width - 150, 10), (140, 20)) # THIS LINE WAS MISSING
        self.vision_toggle_label = pygame_gui.elements.UILabel(
            relative_rect=vision_label_rect,
            text="Vision: OFF [V]",
            manager=self.gui_manager
        )
        # --------------------------------

        # --- Graph data storage ---
        self.population_data = defaultdict(list)
        self.graph_rect = pygame.Rect(config.GRAPH_X, config.GRAPH_Y, config.GRAPH_WIDTH, config.GRAPH_HEIGHT)
        
        # --- Populate world from blueprints ---
        for species_name, blueprint in SPECIES_BLUEPRINTS.items():
            for _ in range(blueprint["count"]):
                x = random.randint(0, width)
                y = random.randint(0, height)
                self.world.add_creature(BaseCreature(x=x, y=y, species_config=blueprint))
        
        for _ in range(config.INITIAL_FOOD_COUNT):
            self.spawn_food()

    def spawn_food(self):
        """Spawns a single food item in a random location."""
        x = random.randint(0, self.width)
        y = random.randint(0, self.height)
        self.world.add_food(Food(x, y, energy=config.FOOD_ENERGY))

    def log_population_data(self):
        """Calculates and stores population percentages for the graph."""
        total_creatures = len(self.world.creatures)
        if total_creatures == 0:
            # If all creatures are dead, log 0% for any species that used to exist
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
        """Draws the population graph onto the screen."""
        pygame.draw.rect(screen, config.GRAPH_BG_COLOR, self.graph_rect)
        pygame.draw.rect(screen, config.GRAPH_AXIS_COLOR, self.graph_rect, 1)

        if not self.population_data:
            return

        for color, history in self.population_data.items():
            if len(history) < 2:
                continue

            points = []
            point_spacing = self.graph_rect.width / (config.GRAPH_MAX_POINTS - 1) if config.GRAPH_MAX_POINTS > 1 else 0

            for i, percentage in enumerate(history):
                x = self.graph_rect.x + i * point_spacing
                y = self.graph_rect.bottom - (percentage / 100) * self.graph_rect.height
                points.append((x, y))
            
            pygame.draw.lines(screen, color, False, points, 2)

    def run(self, screen):
        """The main loop of the simulation."""
        self.is_running = True
        while self.is_running:
            time_delta = self.clock.tick(self.target_tick_rate) / 1000.0
            self.handle_events()
            self.update(time_delta)
            self.draw(screen)

    def handle_events(self):
        """Handles user input and events for Pygame and the GUI."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False

            self.gui_manager.process_events(event)
            
            # --- NEW: Keyboard press event for toggling vision ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_v: # 'V' key
                    self.show_vision = not self.show_vision
                    text = "Vision: ON [V]" if self.show_vision else "Vision: OFF [V]"
                    self.vision_toggle_label.set_text(text)
                    
            self.gui_manager.process_events(event)
            
            if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_element == self.tick_rate_slider:
                    self.target_tick_rate = int(event.value)
                    self.tick_rate_label.set_text(f"Tick Rate: {self.target_tick_rate}")

    def update(self, time_delta):
        """Updates the state of the simulation for one tick."""
        self.gui_manager.update(time_delta)
        
        # 1. Update all creatures (sense, think, act, lose energy)
        for creature in self.world.creatures:
            creature.update(self.world)
            self.world.handle_boundaries(creature)
            
        # 2. Handle Collisions and Interactions (NEW SECTION)
        # Use a copy of the list to iterate over, as creatures might die
        all_creatures = self.world.creatures[:]
        for i, creature_a in enumerate(all_creatures):
            for creature_b in all_creatures[i+1:]:
                dist = math.hypot(creature_a.x - creature_b.x, creature_a.y - creature_b.y)
                if dist < creature_a.radius + creature_b.radius:
                    # Collision detected!
                    # The interaction is not necessarily symmetrical.
                    creature_a.on_collide(creature_b, self.world)
                    creature_b.on_collide(creature_a, self.world)

        # 3. Handle interactions (eating)
        eaten_food = []
        for creature in self.world.creatures:
            for food_item in self.world.food:
                if food_item in eaten_food: continue
                dist = math.hypot(creature.x - food_item.x, creature.y - food_item.y)
                if dist < creature.radius + food_item.radius:
                    creature.energy += food_item.energy
                    if creature.energy > creature.max_energy:
                        creature.energy = creature.max_energy
                    eaten_food.append(food_item)
                    break
        self.world.food = [f for f in self.world.food if f not in eaten_food]

        # 4. Handle Reproduction
        newborns = []
        for creature in self.world.creatures:
            # Check the basic threshold for a single offspring first.
            if creature.energy >= creature.reproduction_threshold:
                # The reproduce method now determines the litter size and total cost.
                children, total_cost = creature.reproduce()
                
                if children: # If any children were actually created
                    creature.energy -= total_cost
                    newborns.extend(children)
        
        # Add all newborns from all successful reproductions to the world
        self.world.creatures.extend(newborns)

        # 5. Handle deaths
        survivors = []
        for creature in self.world.creatures:
            if creature.is_alive():
                survivors.append(creature)
        self.world.creatures = survivors
        
        # 6. Spawn new food and log data
        self.tick_counter += 1
        if self.tick_counter % config.FOOD_SPAWN_RATE == 0:
            self.spawn_food()

        if self.tick_counter % config.GRAPH_UPDATE_RATE == 0:
            self.log_population_data()

    def draw(self, screen):
        """Draws the current state of the simulation."""
        screen.fill(config.COLOR_BG)
        self.world.draw(screen, self.show_vision)
        self.draw_population_graph(screen)
        self.gui_manager.draw_ui(screen)
        
        if self.show_fps:
            actual_fps = self.clock.get_fps()
            fps_text = f"Actual FPS: {actual_fps:.1f}"
            fps_surface = self.fps_font.render(fps_text, True, (200, 200, 200))
            screen.blit(fps_surface, (10, self.height - 30)) # Draw at the bottom-left
        
        pygame.display.flip()