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
    # In src/simulation.py, inside the Simulation class

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.world = World(width, height, cell_size=config.WORLD_GRID_CELL_SIZE)
        self.is_running = False
        self.clock = pygame.time.Clock()
        self.tick_counter = 0
        self.target_tick_rate = config.FPS
        self.show_vision = False
        self.gui_manager = pygame_gui.UIManager((width, height))
        self.fps_font = pygame.font.SysFont("Arial", 18)

        # --- Dynamic food spawning variables ---
        self.food_spawn_interval = config.FOOD_SPAWN_INTERVAL
        self.food_spawn_amount = config.FOOD_SPAWN_AMOUNT
        
        # --- COMPLETE GUI ELEMENT SETUP ---
        # Tick Rate Slider & Label
        slider_rect = pygame.Rect((10, 10), (200, 20))
        self.tick_rate_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=slider_rect, start_value=self.target_tick_rate,
            value_range=(1, 300), manager=self.gui_manager)
        label_rect = pygame.Rect((220, 10), (150, 20))
        self.tick_rate_label = pygame_gui.elements.UILabel(
            relative_rect=label_rect, text=f"Tick Rate: {self.target_tick_rate}",
            manager=self.gui_manager)

        # Food Spawn Interval Slider & Label
        interval_slider_rect = pygame.Rect((10, 60), (200, 20))
        self.interval_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=interval_slider_rect, start_value=self.food_spawn_interval,
            value_range=(1, 500), manager=self.gui_manager)
        interval_label_rect = pygame.Rect((220, 60), (180, 20))
        self.interval_label = pygame_gui.elements.UILabel(
            relative_rect=interval_label_rect, text=f"Spawn Interval: {self.food_spawn_interval}",
            manager=self.gui_manager)

        # Food Spawn Amount Slider & Label
        amount_slider_rect = pygame.Rect((10, 85), (200, 20))
        self.amount_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=amount_slider_rect, start_value=self.food_spawn_amount,
            value_range=(1, 50), manager=self.gui_manager)
        amount_label_rect = pygame.Rect((220, 85), (180, 20))
        self.amount_label = pygame_gui.elements.UILabel(
            relative_rect=amount_label_rect, text=f"Spawn Amount: {self.food_spawn_amount}",
            manager=self.gui_manager)
        
        # Vision Toggle Label
        vision_label_rect = pygame.Rect((width - 150, 10), (140, 20))
        self.vision_toggle_label = pygame_gui.elements.UILabel(
            relative_rect=vision_label_rect, text="Vision: OFF [V]",
            manager=self.gui_manager)
        
        # Reset Button
        reset_button_rect = pygame.Rect((width - 150, 35), (140, 30))
        self.reset_button = pygame_gui.elements.UIButton(
            relative_rect=reset_button_rect, text="Reset Simulation",
            manager=self.gui_manager)
        # ------------------------------------

        # --- THIS IS THE MISSING PART ---
        self.population_data = defaultdict(list)
        self.graph_rect = pygame.Rect(config.GRAPH_X, config.GRAPH_Y, config.GRAPH_WIDTH, config.GRAPH_HEIGHT)
        
        # Use the helper to populate the world for the first time
        self._populate_world()

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

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.reset_button:
                    self.reset()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_v:
                    self.show_vision = not self.show_vision
                    self.vision_toggle_label.set_text("Vision: ON [V]" if self.show_vision else "Vision: OFF [V]")
            
            # --- MODIFIED: Handle all slider movements ---
            if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_element == self.tick_rate_slider:
                    self.target_tick_rate = int(event.value)
                    self.tick_rate_label.set_text(f"Tick Rate: {self.target_tick_rate}")
                elif event.ui_element == self.interval_slider:
                    self.food_spawn_interval = int(event.value)
                    self.interval_label.set_text(f"Spawn Interval: {self.food_spawn_interval}")
                elif event.ui_element == self.amount_slider:
                    self.food_spawn_amount = int(event.value)
                    self.amount_label.set_text(f"Spawn Amount: {self.food_spawn_amount}")

    def update(self, time_delta):
        """Updates the state of the simulation for one tick."""
        self.gui_manager.update(time_delta)
        
        # 1. Update the spatial grid once per frame for efficiency
        self.world.update_grid()

        # 2. Update all creatures (movement, energy loss, aging)
        for creature in self.world.creatures:
            creature.update(self.world)
            self.world.handle_boundaries(creature)
        
        # 3. Handle Collisions using the grid
        checked_pairs = set()
        for creature_a in self.world.creatures:
            # Only check against creatures in the local neighborhood
            local_creatures = self.world.get_neighbors(creature_a, creature_a.radius * 2)['creatures']
            for creature_b in local_creatures:
                if creature_a is creature_b: continue
                
                # Use a sorted tuple of IDs to ensure each pair is checked only once
                pair = tuple(sorted([id(creature_a), id(creature_b)]))
                if pair in checked_pairs: continue
                
                dist = math.hypot(creature_a.x - creature_b.x, creature_a.y - creature_b.y)
                if dist < creature_a.radius + creature_b.radius:
                    creature_a.on_collide(creature_b, self.world)
                    creature_b.on_collide(creature_a, self.world)
                    checked_pairs.add(pair)
        
        # 4. Handle eating using the grid
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
        
        # 5. Handle Reproduction with Population Caps
        species_counts = defaultdict(int)
        for creature in self.world.creatures:
            species_counts[creature.species_name] += 1

        newborns = []
        for creature in self.world.creatures:
            current_pop = species_counts[creature.species_name]
            if creature.energy >= creature.reproduction_threshold and current_pop < creature.population_cap:
                children, total_cost = creature.reproduce()
                if children:
                    creature.energy -= total_cost
                    newborns.extend(children)
                    species_counts[creature.species_name] += len(children)
        self.world.creatures.extend(newborns)

        # 6. Handle Deaths from starvation or old age
        self.world.creatures = [c for c in self.world.creatures if c.is_alive()]
        
        # 7. Spawn new food and log data periodically
        self.tick_counter += 1
        if self.food_spawn_interval > 0 and self.tick_counter % self.food_spawn_interval == 0:
            self.spawn_food(amount=self.food_spawn_amount)
            
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
        
    def _populate_world(self):
        """Clears and populates the world with creatures and food from blueprints."""
        # Clear any existing entities
        self.world.creatures.clear()
        self.world.food.clear()
        
        # Populate creatures
        for blueprint in SPECIES_BLUEPRINTS.values():
            for _ in range(blueprint["count"]):
                x = random.randint(0, self.width)
                y = random.randint(0, self.height)
                self.world.add_creature(BaseCreature(x=x, y=y, species_config=blueprint))
        
        # Populate initial food
        self.spawn_food(amount=config.INITIAL_FOOD_COUNT)
        
    def reset(self):
        """Resets the simulation to its initial state."""
        print("--- Simulation Reset ---")
        # Reset counters and data logs
        self.tick_counter = 0
        self.population_data.clear()

        # Repopulate the world using the helper method
        self._populate_world()