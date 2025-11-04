# config.py
# Global settings and constants for the simulation

# Screen dimensions
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60  # Frames per second

# Colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BG = (25, 25, 35) # A dark blue/grey background

# Food
INITIAL_FOOD_COUNT = 50
FOOD_SPAWN_RATE = 120 # Spawn new food every N ticks (e.g., every 2 seconds at 60 FPS)
FOOD_ENERGY = 100.0

# Creature
INITIAL_CREATURE_COUNT = 60
CREATURE_MAX_ENERGY = 200.0
ENERGY_LOSS_PER_TICK = 0.01 # Basal metabolic rate
ENERGY_LOSS_PER_MOVE = 0.05 # Cost is proportional to speed squared


# --- NEW: Graph settings ---
GRAPH_UPDATE_RATE = 60 # Update the graph data every N ticks (60 ticks = 1 second at 60 FPS)
GRAPH_MAX_POINTS = 500 # Maximum number of historical data points to show on the graph
GRAPH_WIDTH = 350
GRAPH_HEIGHT = 200
GRAPH_X = SCREEN_WIDTH - GRAPH_WIDTH - 10
GRAPH_Y = SCREEN_HEIGHT - GRAPH_HEIGHT - 10
GRAPH_BG_COLOR = (40, 40, 50)
GRAPH_AXIS_COLOR = (150, 150, 150)