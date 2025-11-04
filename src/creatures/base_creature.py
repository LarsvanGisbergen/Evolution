# src/creatures/base_creature.py
import pygame
import numpy as np
import math
import torch
import random
from src.nn import NeuralNetwork
from src.nn import NeuralNetwork, DEVICE

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
        self.sense_radius = species_config["sense_radius"]
        # --- Dynamic Stats ---
        self.energy = self.max_energy / 2 # Start with half energy
        self.age = 0
        self.vx = 0.0
        self.vy = 0.0

        # --- NN and Genome Setup ---
        self.nn_layer_sizes = species_config["nn_layer_sizes"]
        self.nn = NeuralNetwork(self.nn_layer_sizes)
        self.nn.to(DEVICE)
        
        genome_length = self.nn.calculate_genome_length()
        self.genome = np.random.uniform(-1, 1, genome_length)
        self.nn.set_genome(self.genome)

        # --- Other Traits (could also be moved to blueprints later) ---
        self.max_speed = 2.0
        
        # --- NEW: Store interaction properties ---
        self.species_name = species_config["species_name"]
        self.collision_interactions = species_config.get("collision_interactions", {})
        self.steal_amount = species_config.get("steal_amount", 0)
        self.steal_efficiency = species_config.get("steal_efficiency", 0)
    
        self.min_offspring = species_config.get("min_offspring", 1)
        self.max_offspring = species_config.get("max_offspring", 1)
        
        # --- State Variables ---
        self.nn_inputs = []
        self.nn_outputs = []

    def _normalize_angle(self, angle):
        """Wraps an angle to the range [-pi, pi]."""
        return (angle + math.pi) % (2 * math.pi) - math.pi

    def sense(self, world):
        """
        Finds the nearest object WITHIN THE CREATURE'S FIELD OF VIEW
        and sets NN inputs.
        """
        nearest_obj = None
        min_dist = float('inf')
        obj_type = 0.0

        # If the creature isn't moving, it can't "see" anything directionally.
        # This also prevents math errors with atan2(0, 0).
        if self.vx == 0 and self.vy == 0:
            self.nn_inputs = [0.0, 0.0, 0.0]
            return

        # 1. Determine the creature's forward-facing angle from its velocity
        forward_angle = math.atan2(self.vy, self.vx)

        # Combine all potential targets into one list to iterate through
        all_objects = [('creature', c) for c in world.creatures if c is not self] + \
                      [('food', f) for f in world.food]

        for obj_type_str, obj in all_objects:
            # 2. First, do a cheap distance check to filter out distant objects
            dist = math.hypot(self.x - obj.x, self.y - obj.y)
            if dist > self.sense_radius:
                continue

            # 3. If within range, do the more expensive angle check
            angle_to_obj = math.atan2(obj.y - self.y, obj.x - self.x)
            angle_diff = self._normalize_angle(angle_to_obj - forward_angle)

            # 4. Check if the object is within the Field of View
            if abs(angle_diff) < self.fov_angle / 2:
                # This object is visible. Is it the closest visible object?
                if dist < min_dist:
                    min_dist = dist
                    nearest_obj = obj
                    obj_type = -1.0 if obj_type_str == 'creature' else 1.0
        
        # 5. Set NN inputs based on the closest VISIBLE object
        if nearest_obj:
            dx = (nearest_obj.x - self.x) / self.sense_radius
            dy = (nearest_obj.y - self.y) / self.sense_radius
            self.nn_inputs = [dx, dy, obj_type]
        else:
            self.nn_inputs = [0.0, 0.0, 0.0] # Nothing visible in the cone

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

    def reproduce(self): # --- MODIFIED ---
        """
        Creates a list of new offspring, each with a mutated version of the genome.
        Returns the list of children and the total energy cost.
        """
        num_offspring = random.randint(self.min_offspring, self.max_offspring)
        total_cost = self.reproduction_cost * num_offspring
        
        children = []
        if self.energy >= total_cost:
            for _ in range(num_offspring):
                child_x = self.x + random.uniform(-self.radius * 2, self.radius * 2)
                child_y = self.y + random.uniform(-self.radius * 2, self.radius * 2)
                child = BaseCreature(child_x, child_y, self.species_config)

                mutated_genome = self.genome.copy()
                for i in range(len(mutated_genome)):
                    if random.random() < self.mutation_rate:
                        change = random.uniform(-self.mutation_amount, self.mutation_amount)
                        mutated_genome[i] += change
                
                child.genome = mutated_genome
                child.nn.set_genome(child.genome)
                children.append(child)
            
            return children, total_cost
        else:
            # Not enough energy for the litter, so no children are born.
            return [], 0

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
    
    def _steal_energy(self, target):
        """Action: Steals a fixed amount of energy from a target creature."""
        stolen_energy = min(target.energy, self.steal_amount) # Can't steal more than the target has
        target.energy -= stolen_energy
        self.energy += stolen_energy * self.steal_efficiency
        # Cap energy at max
        if self.energy > self.max_energy:
            self.energy = self.max_energy

    # --- NEW: The `on_collide` Dispatcher Method ---
    def on_collide(self, other_creature, world):
        """
        Called by the simulation when a collision occurs.
        This method dispatches to the correct action based on the blueprint.
        """
        other_species = other_creature.species_name

        # Check if we have a defined interaction for this species
        if other_species in self.collision_interactions:
            action = self.collision_interactions[other_species]

            # --- Dispatch to the correct action method ---
            if action == "steal_energy":
                self._steal_energy(other_creature)
            # Future actions can be added here:
            # elif action == "damage":
            #     self._deal_damage(other_creature)