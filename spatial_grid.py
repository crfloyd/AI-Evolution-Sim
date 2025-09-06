import math

class SpatialGrid:
    def __init__(self, width, height, cell_size):
        self.cell_size = cell_size
        self.cols = math.ceil(width / cell_size)
        self.rows = math.ceil(height / cell_size)
        self.grid = {}
        # Track entity positions for incremental updates
        self.entity_positions = {}  # entity_id -> (cell_x, cell_y)

    def _cell_coords(self, x, y):
        return int(x // self.cell_size), int(y // self.cell_size)

    def clear(self):
        self.grid.clear()
        self.entity_positions.clear()

    def add_entity(self, entity):
        cx, cy = self._cell_coords(entity.x, entity.y)
        key = (cx, cy)
        if key not in self.grid:
            self.grid[key] = []
        self.grid[key].append(entity)
        # Track initial position
        self.entity_positions[entity.id] = (cx, cy)

    def remove_entity(self, entity):
        """Remove entity from its current cell"""
        if entity.id in self.entity_positions:
            old_cx, old_cy = self.entity_positions[entity.id]
            old_key = (old_cx, old_cy)
            if old_key in self.grid and entity in self.grid[old_key]:
                self.grid[old_key].remove(entity)
                # Clean up empty cells
                if not self.grid[old_key]:
                    del self.grid[old_key]
            del self.entity_positions[entity.id]

    def update_entity(self, entity):
        """Update entity position incrementally (only if it moved cells)"""
        new_cx, new_cy = self._cell_coords(entity.x, entity.y)
        
        # Check if entity is tracked and moved to different cell
        if entity.id in self.entity_positions:
            old_cx, old_cy = self.entity_positions[entity.id]
            if (old_cx, old_cy) != (new_cx, new_cy):
                # Entity moved to different cell - remove from old, add to new
                old_key = (old_cx, old_cy)
                if old_key in self.grid and entity in self.grid[old_key]:
                    self.grid[old_key].remove(entity)
                    if not self.grid[old_key]:
                        del self.grid[old_key]
                
                # Add to new cell
                new_key = (new_cx, new_cy)
                if new_key not in self.grid:
                    self.grid[new_key] = []
                self.grid[new_key].append(entity)
                self.entity_positions[entity.id] = (new_cx, new_cy)
        else:
            # New entity - add normally
            self.add_entity(entity)

    def get_neighbors(self, entity, radius=None):
        cx, cy = self._cell_coords(entity.x, entity.y)
        cells = set()

        radius = radius or self.cell_size * 1.5  # fallback
        cell_range = int(math.ceil(radius / self.cell_size))

        for dx in range(-cell_range, cell_range + 1):
            for dy in range(-cell_range, cell_range + 1):
                cells.add((cx + dx, cy + dy))

        neighbors = []
        for cell in cells:
            neighbors.extend(self.grid.get(cell, []))
        return neighbors

