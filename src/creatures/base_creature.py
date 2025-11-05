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
        self.max_speed = species_config["max_speed"]
        self.species_name = species_config["species_name"]
        self.collision_interactions = species_config.get("collision_interactions", {})
        self.steal_amount = species_config.get("steal_amount", 0)
        self.steal_efficiency = species_config.get("steal_efficiency", 0)
        self.min_offspring = species_config.get("min_offspring", 1)
        self.max_offspring = species_config.get("max_offspring", 1)
        self.nn_inputs = []
        self.nn_outputs = []
        self.lifespan = species_config["lifespan_ticks"]
        self.population_cap = species_config["population_cap"]

    def _normalize_angle(self, angle):
        return (angle + math.pi) % (2 * math.pi) - math.pi

    def sense(self, world):
        """
        Gathers the 7 inputs for the new, more complex brain structure.
        """
        # --- NEW INPUT 1: Own Energy ---
        own_energy_normalized = self.energy / self.max_energy

        # --- Use the grid to find local objects efficiently ---
        local_objects = world.get_neighbors(self, self.sense_radius)
        
        # --- Find Nearest Food ---
        nearest_food, min_dist_food = None, float('inf')
        for food_item in local_objects['food']:
            dist = math.hypot(self.x - food_item.x, self.y - food_item.y)
            if dist < min_dist_food:
                min_dist_food, nearest_food = dist, food_item

        # --- Find Nearest Creature ---
        nearest_creature, min_dist_creature = None, float('inf')
        for other in local_objects['creatures']:
            if other is self: continue
            dist = math.hypot(self.x - other.x, self.y - other.y)
            if dist < min_dist_creature:
                min_dist_creature, nearest_creature = dist, other

        # --- Prepare the 7 NN inputs ---
        # If no food is near, provide neutral (zero) inputs for it.
        dx_food = (nearest_food.x - self.x) / self.sense_radius if nearest_food else 0.0
        dy_food = (nearest_food.y - self.y) / self.sense_radius if nearest_food else 0.0
        dist_food_norm = (min_dist_food / self.sense_radius) if nearest_food else 0.0

        # If no creature is near, provide neutral (zero) inputs for it.
        dx_creature = (nearest_creature.x - self.x) / self.sense_radius if nearest_creature else 0.0
        dy_creature = (nearest_creature.y - self.y) / self.sense_radius if nearest_creature else 0.0
        # For threat level, we'll use steal_amount for now, normalized.
        # This is a simple heuristic: a dangerous creature has a high steal_amount.
        threat_level = (nearest_creature.steal_amount / 50.0) if nearest_creature else 0.0
        
        self.nn_inputs = [
            own_energy_normalized,
            dx_food, dy_food, dist_food_norm,
            dx_creature, dy_creature, threat_level
        ]

    def think(self):
        """Processes NN inputs to get outputs using PyTorch on the correct device."""
        input_tensor = torch.tensor(self.nn_inputs, dtype=torch.float32).to(DEVICE)
        
        output_tensor = self.nn(input_tensor)
        
        # Move the result back to the CPU to be used by NumPy and Pygame
        self.nn_outputs = output_tensor.detach().cpu().numpy()

    def act(self):
        """
        Interprets the 4 new NN outputs for direction, speed, and action.
        """
        # 1. Interpret the NN outputs
        direction_x = self.nn_outputs[0]
        direction_y = self.nn_outputs[1]
        speed_output = self.nn_outputs[2]
        action_output = self.nn_outputs[3] # The new "action intent" output

        # 2. Handle Movement (this logic is the same as the previous step)
        min_speed = self.max_speed * 0.1
        speed_multiplier = (speed_output + 1) / 2
        desired_speed = min_speed + speed_multiplier * (self.max_speed - min_speed)
        
        direction_magnitude = math.hypot(direction_x, direction_y)
        if direction_magnitude > 0.01:
            norm_dx = direction_x / direction_magnitude
            norm_dy = direction_y / direction_magnitude
            self.vx = norm_dx * desired_speed
            self.vy = norm_dy * desired_speed
        else:
            self.vx *= 0.9
            self.vy *= 0.9

        self.x += self.vx
        self.y += self.vy

        # 3. Handle Energy Consumption (same as before)
        current_speed = math.hypot(self.vx, self.vy)
        move_energy_loss = self.move_cost * (current_speed / self.max_speed)**2
        self.energy -= (self.metabolic_rate + move_energy_loss)
        self.age += 1
        
        # 4. Handle the Action Intent (NEW)
        # For now, this output does nothing. But the framework is here.
        # In the future, we could check if action_output > 0.5 and then
        # try to reproduce, attack, etc.
        # For example: self.wants_to_reproduce = (action_output > 0.5)

    def reproduce(self):
        """
        Creates offspring for a flat fee, spawning them just outside the parent's radius.
        """
        flat_reproduction_cost = self.reproduction_cost
        children = []
        if self.energy >= flat_reproduction_cost:
            num_offspring = random.randint(self.min_offspring, self.max_offspring)
            
            for _ in range(num_offspring):
                # --- THIS IS THE MODIFIED PART ---
                # Create a new creature instance first to get its radius
                child = BaseCreature(self.x, self.y, self.species_config)
                
                # Calculate a safe spawn position
                spawn_angle = random.uniform(0, 2 * math.pi)
                # Spawn distance is parent radius + child radius + a small gap
                spawn_dist = self.radius + child.radius + 1
                
                child.x = self.x + spawn_dist * math.cos(spawn_angle)
                child.y = self.y + spawn_dist * math.sin(spawn_angle)
                # --------------------------------

                mutated_genome = self.genome.copy()
                for i in range(len(mutated_genome)):
                    if random.random() < self.mutation_rate:
                        change = random.uniform(-self.mutation_amount, self.mutation_amount)
                        mutated_genome[i] += change
                child.genome = mutated_genome
                child.nn.set_genome(child.genome)
                children.append(child)
            
            return children, flat_reproduction_cost
        else:
            return [], 0
    
    def update(self, world):
        self.sense(world)
        self.think()
        self.act()

    

    def is_alive(self):
        return self.energy > 0 and self.age < self.lifespan

    def _steal_energy(self, target):
        stolen_energy = min(target.energy, self.steal_amount)
        target.energy -= stolen_energy
        self.energy += stolen_energy * self.steal_efficiency
        if self.energy > self.max_energy:
            self.energy = self.max_energy

    def on_collide(self, other_creature, world):
        """
        Handles all collision logic. First, resolves the physical overlap,
        then checks for special species-specific interactions.
        """
        # --- 1. Universal Physical Response ---
        self._handle_physical_collision(other_creature)

        # --- 2. Species-Specific Interaction ---
        other_species = other_creature.species_name
        if other_species in self.collision_interactions:
            action = self.collision_interactions[other_species]
            if action == "steal_energy":
                self._steal_energy(other_creature)
    
    
    def draw(self, screen, show_vision=False):
        """Draws the creature with transparency based on its energy level."""
        # 1. Calculate energy percentage (from 0.0 to 1.0)
        energy_percentage = max(0, self.energy / self.max_energy)

        # 2. Map energy to an alpha value
        min_alpha = 40
        max_alpha = 255
        alpha = int(min_alpha + (energy_percentage * (max_alpha - min_alpha)))

        # 3. Create the color tuple with the new alpha
        dynamic_color = (*self.color, alpha)

        # 4. Create a temporary surface for the creature
        creature_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        
        # 5. Draw the circle onto the temporary surface
        pygame.draw.circle(
            surface=creature_surf,
            color=dynamic_color,
            center=(self.radius, self.radius),
            radius=self.radius
        )

        # 6. Blit the transparent creature onto the main screen
        # Position is the top-left corner of the surface
        screen.blit(creature_surf, (int(self.x - self.radius), int(self.y - self.radius)))

        # 7. Draw the vision cone if enabled
        if show_vision:
            self._draw_vision_cone(screen)
    
    def _draw_vision_cone(self, screen):
        """Draws the creature's vision cone as an outline."""
        if self.vx == 0 and self.vy == 0: return

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
        
    def _handle_physical_collision(self, other):
        """Calculates and applies a 'push-out' force to resolve physical overlap."""
        dx = self.x - other.x
        dy = self.y - other.y
        distance = math.hypot(dx, dy)
        
        # Avoid division by zero if creatures are perfectly on top of each other
        if distance == 0:
            distance = 0.01
            dx = 0.01

        # Calculate overlap amount
        overlap = (self.radius + other.radius) - distance
        if overlap > 0:
            # The amount each creature needs to move
            push_amount = overlap / 2
            
            # Normalized direction vector
            norm_dx = dx / distance
            norm_dy = dy / distance
            
            # Apply the push to both creatures
            self.x += norm_dx * push_amount
            self.y += norm_dy * push_amount
            other.x -= norm_dx * push_amount
            other.y -= norm_dy * push_amount