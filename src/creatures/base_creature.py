# src/creatures/base_creature.py
import pygame
import numpy as np
import math
import torch
import random
from src.nn import NeuralNetwork

class BaseCreature:
    def __init__(self, x, y, species_config):
        """Initializes a creature based on a species blueprint."""
        self.x = x
        self.y = y
        self.species_config = species_config # Store the blueprint for reproduction

        # --- Set properties from the blueprint ---
        self.radius = species_config["radius"]
        self.color = species_config["color"]
        self.max_energy = species_config["max_energy"]
        self.reproduction_threshold = self.max_energy * species_config["reproduction_threshold"]
        self.reproduction_cost = self.max_energy * species_config["reproduction_cost"]
        self.mutation_rate = species_config["mutation_rate"]
        self.mutation_amount = species_config["mutation_amount"]
        self.metabolic_rate = species_config["metabolic_rate"]
        self.move_cost = species_config["move_cost"]
        self.fov_angle = math.radians(species_config["fov_angle_degrees"])
        # --- Dynamic Stats ---
        self.energy = self.max_energy / 2 # Start with half energy
        self.age = 0
        self.vx = 0.0
        self.vy = 0.0

        # --- NN and Genome Setup ---
        self.nn_layer_sizes = species_config["nn_layer_sizes"]
        self.nn = NeuralNetwork(self.nn_layer_sizes)
        
        genome_length = self.nn.calculate_genome_length()
        self.genome = np.random.uniform(-1, 1, genome_length)
        self.nn.set_genome(self.genome)

        # --- Other Traits (could also be moved to blueprints later) ---
        self.max_speed = 2.0
        self.sense_radius = 200.0
        
        # --- State Variables ---
        self.nn_inputs = []
        self.nn_outputs = []

    def sense(self, world):
        """Finds the nearest object (food or creature) and sets NN inputs."""
        nearest_obj = None
        min_dist = float('inf')
        obj_type = 0.0 # 1.0 for food, -1.0 for creature

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
            self.nn_inputs = [0.0, 0.0, 0.0] # No object in range

    def think(self):
        """Processes NN inputs to get outputs using PyTorch."""
        input_tensor = torch.tensor(self.nn_inputs, dtype=torch.float32)
        output_tensor = self.nn(input_tensor)
        self.nn_outputs = output_tensor.detach().cpu().numpy()

    def act(self):
        """Uses NN outputs to change velocity and consumes energy."""
        acceleration_x = self.nn_outputs[0]
        acceleration_y = self.nn_outputs[1]

        self.vx += acceleration_x * 0.1
        self.vy += acceleration_y * 0.1

        speed = math.hypot(self.vx, self.vy)
        if speed > self.max_speed:
            self.vx = (self.vx / speed) * self.max_speed
            self.vy = (self.vy / speed) * self.max_speed
        
        self.x += self.vx
        self.y += self.vy

        # Use the creature's own metabolic traits for energy loss
        move_energy_loss = self.move_cost * (speed / self.max_speed)**2
        self.energy -= (self.metabolic_rate + move_energy_loss)

    def reproduce(self):
        """Creates a new offspring with a mutated version of this creature's genome."""
        child_x = self.x + random.uniform(-self.radius, self.radius)
        child_y = self.y + random.uniform(-self.radius, self.radius)
        
        # Pass the same blueprint to the child
        child = BaseCreature(child_x, child_y, self.species_config)

        # Inherit and mutate the genome
        mutated_genome = self.genome.copy()
        for i in range(len(mutated_genome)):
            if random.random() < self.mutation_rate:
                change = random.uniform(-self.mutation_amount, self.mutation_amount)
                mutated_genome[i] += change
        
        # Assign the new genome to the child
        child.genome = mutated_genome
        child.nn.set_genome(child.genome)
        
        return child

    def update(self, world):
        """The main sense-think-act loop for the creature."""
        self.sense(world)
        self.think()
        self.act()

    def draw(self, screen, show_vision=False):
        """Draws the creature and its vision cone (if enabled)."""
        # Draw the main body of the creature
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

        if show_vision and (self.vx != 0 or self.vy != 0): # Only draw if moving
            vision_color = (*self.color, 40)
            angle = math.atan2(self.vy, self.vx)

            # --- CORRECTED PART: Convert all points to integers as they are created ---
            p1 = (int(self.x), int(self.y))
            
            angle_left = angle - self.fov_angle / 2
            p2 = (
                int(self.x + self.sense_radius * math.cos(angle_left)),
                int(self.y + self.sense_radius * math.sin(angle_left))
            )
            
            angle_right = angle + self.fov_angle / 2
            p3 = (
                int(self.x + self.sense_radius * math.cos(angle_right)),
                int(self.y + self.sense_radius * math.sin(angle_right))
            )
            
            points = [p1, p2, p3]
            # -------------------------------------------------------------------------

            # Now that all points are integers, this complex part will work correctly.
            try:
                # Find the bounding box of the polygon
                min_x = min(p[0] for p in points)
                min_y = min(p[1] for p in points)
                max_x = max(p[0] for p in points)
                max_y = max(p[1] for p in points)
                width = max_x - min_x
                height = max_y - min_y

                # Create a temporary surface just big enough for the polygon
                shape_surf = pygame.Surface((width, height), pygame.SRCALPHA)
                
                # Draw the polygon, translating coordinates to be relative to the new surface
                pygame.draw.polygon(shape_surf, vision_color, [(p[0] - min_x, p[1] - min_y) for p in points])
                
                # Blit the transparent shape surface onto the main screen at the correct location
                screen.blit(shape_surf, (min_x, min_y))

            except ValueError:
                # This can happen on rare occasions if a point calculation results in an invalid number.
                # This try/except block makes the drawing more robust.
                pass
            
    def is_alive(self):
        """Checks if the creature has enough energy to live."""
        return self.energy > 0