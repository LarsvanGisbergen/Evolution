# src/creatures/base_creature.py
import pygame
import numpy as np
import math
import torch
from src.nn import NeuralNetwork
import config # --- NEW ---

class BaseCreature:
    def __init__(self, x, y, color=(0, 150, 200), radius=10):
        # (x, y, radius, color, age, vx, vy are the same)
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.age = 0
        self.vx = 0.0
        self.vy = 0.0
        self.energy = config.CREATURE_MAX_ENERGY / 2 # Start with half energy

        # --- MODIFIED: NN now has 3 inputs ---
        # Inputs: dx, dy to nearest object, object_type (1 for food, -1 for creature)
        # Hidden Layer: 5 neurons
        # Outputs: dx_change, dy_change for movement
        self.nn_layer_sizes = [3, 5, 2] 
        self.nn = NeuralNetwork(self.nn_layer_sizes)
        
        genome_length = self.nn.calculate_genome_length()
        self.genome = np.random.uniform(-1, 1, genome_length)
        self.nn.set_genome(self.genome)

        # (Genetic Traits and State variables are the same)
        self.max_speed = 2.0
        self.sense_radius = 200.0
        self.nn_inputs = []
        self.nn_outputs = []

    def sense(self, world): # --- MODIFIED ---
        """Finds the nearest object (food or creature) and sets NN inputs."""
        nearest_obj = None
        min_dist = float('inf')
        obj_type = 0 # 1 for food, -1 for creature

        # Sense nearest creature
        for other in world.creatures:
            if other is self: continue
            dist = math.hypot(self.x - other.x, self.y - other.y)
            if dist < min_dist and dist < self.sense_radius:
                min_dist = dist
                nearest_obj = other
                obj_type = -1.0

        # Sense nearest food
        for food_item in world.food:
            dist = math.hypot(self.x - food_item.x, self.y - food_item.y)
            if dist < min_dist and dist < self.sense_radius:
                min_dist = dist
                nearest_obj = food_item
                obj_type = 1.0

        if nearest_obj:
            dx = (nearest_obj.x - self.x) / self.sense_radius
            dy = (nearest_obj.y - self.y) / self.sense_radius
            self.nn_inputs = [dx, dy, obj_type]
        else:
            self.nn_inputs = [0, 0, 0] # No object in range

    def think(self):
        # (No changes to this method)
        input_tensor = torch.tensor(self.nn_inputs, dtype=torch.float32)
        output_tensor = self.nn(input_tensor)
        self.nn_outputs = output_tensor.detach().cpu().numpy()

    def act(self):
        # --- MODIFIED: Added energy consumption ---
        # The core movement logic is the same
        acceleration_x = self.nn_outputs[0]
        acceleration_y = self.nn_outputs[1]

        self.vx += acceleration_x * 0.1
        self.vy += acceleration_y * 0.1

        speed = math.hypot(self.vx, self.vy)
        if speed > self.max_speed:
            self.vx = (self.vx / speed) * self.max_speed
            self.vy = (self.vy / speed) * self.max_speed
        
        # Apply velocity to position
        self.x += self.vx
        self.y += self.vy

        # --- NEW: Energy Loss ---
        # Base metabolic rate
        self.energy -= config.ENERGY_LOSS_PER_TICK
        # Movement cost (proportional to speed squared for realism)
        move_cost = config.ENERGY_LOSS_PER_MOVE * (speed / self.max_speed)**2
        self.energy -= move_cost
        
    def update(self, world):
        # (No changes to this method)
        self.sense(world)
        self.think()
        self.act()

    def draw(self, screen):
        # (No changes to this method)
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

    # --- NEW ---
    def is_alive(self):
        """Check if the creature has enough energy to live."""
        return self.energy > 0