# config.py

# --- Global Simulation Settings ---
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 1000
FPS = 60
COLOR_BG = (25, 25, 35)
WORLD_GRID_CELL_SIZE = 100 # For the performance optimization grid

# --- Food Settings (This is the corrected part) ---
INITIAL_FOOD_COUNT = 20
# RENAMED: This variable controls the interval between spawning events.
FOOD_SPAWN_INTERVAL = 100  # Spawns food every 10 ticks.
# NEW: This variable controls how much food is created during each event.
FOOD_SPAWN_AMOUNT = 2
FOOD_ENERGY = 100.0

# --- Graph Settings ---
GRAPH_UPDATE_RATE = 60
GRAPH_MAX_POINTS = 500
GRAPH_WIDTH = 350
GRAPH_HEIGHT = 200
GRAPH_X = SCREEN_WIDTH - GRAPH_WIDTH - 10
GRAPH_Y = SCREEN_HEIGHT - GRAPH_HEIGHT - 10
GRAPH_BG_COLOR = (40, 40, 50)
GRAPH_AXIS_COLOR = (150, 150, 150)