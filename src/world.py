# src/world.py

class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.creatures = []
        self.food = [] # --- NEW ---

    def add_creature(self, creature):
        self.creatures.append(creature)

    # --- NEW ---
    def add_food(self, food_item):
        self.food.append(food_item)
    
    def handle_boundaries(self, creature):
        creature.x = creature.x % self.width
        creature.y = creature.y % self.height

    def update(self):
        # The responsibility of updating creatures is now more complex,
        # so it will be handled by the Simulation class.
        # This method can be simplified or removed later.
        for creature in self.creatures:
            creature.update(self) # Creature still needs the world for sensing
            self.handle_boundaries(creature)

    def draw(self, screen, show_vision=False): # --- MODIFIED ---
        """Draw all objects in the world."""
        # Draw food first, so creatures appear on top
        for food_item in self.food:
            food_item.draw(screen)

        for creature in self.creatures:
            creature.draw(screen, show_vision)