# blueprints.py
# This file contains the "genetic blueprints" for all creature species in the simulation.

SPECIES_BLUEPRINTS = {
    "herbivore_blue": {
        "count": 8,
        "color": (50, 100, 200),
        "radius": 8,
        "nn_layer_sizes": [3, 5, 2],
        "max_energy": 200.0,
        "reproduction_threshold": 0.9, # Reproduce at 80% of max energy
        "reproduction_cost": 0.5,      # Costs 50% of max energy
        "mutation_rate": 0.05,
        "mutation_amount": 0.1,
        "metabolic_rate": 0.05,  # Base energy loss per tick
        "move_cost": 0.05,   # Multiplier for energy loss from movement
        "fov_angle_degrees": 60,
    },
    "scavenger_red": {
        "count": 4,
        "color": (200, 50, 50),
        "radius": 8,
        "nn_layer_sizes": [3, 6, 2], # Slightly more complex brain
        "max_energy": 150.0,         # Lower max energy
        "reproduction_threshold": 0.7, # Can reproduce earlier
        "reproduction_cost": 0.6,      # Costs more relative to its max
        "mutation_rate": 0.10,         # Mutates more frequently
        "mutation_amount": 0.15,
        "metabolic_rate": 0.08, # Higher metabolism
        "move_cost": 0.03,       # More efficient movement
        "fov_angle_degrees": 90,
    }
}