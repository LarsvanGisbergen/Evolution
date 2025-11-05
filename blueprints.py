# blueprints.py
# This file contains the "genetic blueprints" for all creature species in the simulation.

SPECIES_BLUEPRINTS = {
    "herbivore_blue": {
        "species_name": "herbivore_blue",
        "count": 8,
        "color": (50, 100, 200),
        "radius": 8,
        "nn_layer_sizes": [7, 12, 8, 4],
        "max_energy": 250.0,
        "reproduction_threshold": 0.6, # Reproduce at 50% of max energy
        "reproduction_cost": 0.5,      # Costs 50% of max energy
        "mutation_rate": 0.05,
        "mutation_amount": 0.1,
        "metabolic_rate": 0.03,  # Base energy loss per tick
        "move_cost": 0.1,   # Multiplier for energy loss from movement
        "max_speed": 1,
        "fov_angle_degrees": 30,
        "sense_radius": 150.0,
        "collision_interactions": {
            # Blue herbivores don't actively do anything on collision.
            # They are passive.
        },
        "min_offspring": 2,  
        "max_offspring": 4,  
    },
    "scavenger_red": {
        "species_name": "scavenger_red",
        "count": 4,
        "color": (200, 50, 50),
        "radius": 8,
        "nn_layer_sizes": [7, 16, 12, 4], # Slightly more complex brain
        "max_energy": 150.0,         # Lower max energy
        "reproduction_threshold": 0.9, # Can reproduce earlier
        "reproduction_cost": 0.2,      # Costs more relative to its max
        "mutation_rate": 0.10,         # Mutates more frequently
        "mutation_amount": 0.1,
        "metabolic_rate": 0.1, # Higher metabolism
        "move_cost": 0.03,       # More efficient movement
        "max_speed": 1.3,
        "fov_angle_degrees": 60,
        "sense_radius": 200.0,
        "collision_interactions": {
            "herbivore_blue": "steal_energy"
        },
        "steal_amount": 30.0,
        "steal_efficiency": 0.8,
        "min_offspring": 1, # Scavengers only have single births 
        "max_offspring": 1,  
    }
}