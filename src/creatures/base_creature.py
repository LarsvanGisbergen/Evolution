# src/creatures/base_creature.py
import pygame
import numpy as np
import math
import torch
import random
from src.nn import NeuralNetwork, DEVICE

class BaseCreature:
    def __init__(self, x, y, species_config):
        self.x = x
        self.y = y
        self.species_config = species_config
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
        self.sense_radius = species_config["sense_radius"]
        self.energy = self.max_energy / 2
        self.age = 0
        self.vx = 0.0
        self.vy = 0.0
        self.nn_layer_sizes = species_config["nn_layer_sizes"]
        self.nn = NeuralNetwork(self.nn_layer_sizes).to(DEVICE)
        genome_length = self.nn.calculate_genome_length()
        self.genome = np.random.uniform(-1, 1, genome_length)
        self.nn.set_genome(self.genome)
        self.max_speed = 2.0
        self.species_name = species_config["species_name"]
        self.collision_interactions = species_config.get("collision_interactions", {})
        self.steal_amount = species_config.get("steal_amount", 0)
        self.steal_efficiency = species_config.get("steal_efficiency", 0)
        self.min_offspring = species_config.get("min_offspring", 1)
        self.max_offspring = species_config.get("max_offspring", 1)
        self.nn_inputs = []
        self.nn_outputs = []

    def _normalize_angle(self, angle):
        return (angle + math.pi) % (2 * math.pi) - math.pi

    def sense(self, world):
        nearest_obj, min_dist, obj_type = None, float('inf'), 0.0
        if self.vx == 0 and self.vy == 0:
            self.nn_inputs = [0.0, 0.0, 0.0]
            return

        forward_angle = math.atan2(self.vy, self.vx)
        local_objects = world.get_neighbors(self, self.sense_radius)
        all_objects = [('creature', c) for c in local_objects['creatures'] if c is not self] + \
                      [('food', f) for f in local_objects['food']]

        for obj_type_str, obj in all_objects:
            dist = math.hypot(self.x - obj.x, self.y - obj.y)
            if dist > self.sense_radius: continue
            angle_to_obj = math.atan2(obj.y - self.y, obj.x - self.x)
            angle_diff = self._normalize_angle(angle_to_obj - forward_angle)
            if abs(angle_diff) < self.fov_angle / 2:
                if dist < min_dist:
                    min_dist, nearest_obj = dist, obj
                    obj_type = -1.0 if obj_type_str == 'creature' else 1.0
        
        if nearest_obj:
            dx = (nearest_obj.x - self.x) / self.sense_radius
            dy = (nearest_obj.y - self.y) / self.sense_radius
            self.nn_inputs = [dx, dy, obj_type]
        else:
            self.nn_inputs = [0.0, 0.0, 0.0]

    def think(self):
        """Processes NN inputs to get outputs using PyTorch on the correct device."""
        input_tensor = torch.tensor(self.nn_inputs, dtype=torch.float32).to(DEVICE)
        
        output_tensor = self.nn(input_tensor)
        
        # Move the result back to the CPU to be used by NumPy and Pygame
        self.nn_outputs = output_tensor.detach().cpu().numpy()

    def act(self):
        acceleration_x, acceleration_y = self.nn_outputs[0], self.nn_outputs[1]
        self.vx += acceleration_x * 0.1
        self.vy += acceleration_y * 0.1
        speed = math.hypot(self.vx, self.vy)
        if speed > self.max_speed:
            self.vx = (self.vx / speed) * self.max_speed
            self.vy = (self.vy / speed) * self.max_speed
        self.x += self.vx
        self.y += self.vy
        move_energy_loss = self.move_cost * (speed / self.max_speed)**2
        self.energy -= (self.metabolic_rate + move_energy_loss)

    def reproduce(self):
        num_offspring = random.randint(self.min_offspring, self.max_offspring)
        total_cost = self.reproduction_cost * num_offspring
        children = []
        if self.energy >= total_cost:
            for _ in range(num_offspring):
                child = BaseCreature(self.x, self.y, self.species_config)
                mutated_genome = self.genome.copy()
                for i in range(len(mutated_genome)):
                    if random.random() < self.mutation_rate:
                        change = random.uniform(-self.mutation_amount, self.mutation_amount)
                        mutated_genome[i] += change
                child.genome = mutated_genome
                child.nn.set_genome(child.genome)
                children.append(child)
            return children, total_cost
        return [], 0
    
    def update(self, world):
        self.sense(world)
        self.think()
        self.act()

    def draw(self, screen, show_vision=False):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        if show_vision and (self.vx != 0 or self.vy != 0):
            vision_outline_color = (*self.color, 150)
            angle = math.atan2(self.vy, self.vx)
            p1 = (int(self.x), int(self.y))
            angle_left = angle - self.fov_angle / 2
            p2 = (int(self.x + self.sense_radius * math.cos(angle_left)), 
                  int(self.y + self.sense_radius * math.sin(angle_left)))
            angle_right = angle + self.fov_angle / 2
            p3 = (int(self.x + self.sense_radius * math.cos(angle_right)), 
                  int(self.y + self.sense_radius * math.sin(angle_right)))
            pygame.draw.aalines(screen, vision_outline_color, False, [p2, p1, p3])

    def is_alive(self):
        return self.energy > 0

    def _steal_energy(self, target):
        stolen_energy = min(target.energy, self.steal_amount)
        target.energy -= stolen_energy
        self.energy += stolen_energy * self.steal_efficiency
        if self.energy > self.max_energy:
            self.energy = self.max_energy

    def on_collide(self, other_creature, world):
        other_species = other_creature.species_name
        if other_species in self.collision_interactions:
            action = self.collision_interactions[other_species]
            if action == "steal_energy":
                self._steal_energy(other_creature)