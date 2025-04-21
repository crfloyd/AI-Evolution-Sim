import math

class SpatialGrid:
    def __init__(self, width, height, cell_size):
        self.cell_size = cell_size
        self.cols = math.ceil(width / cell_size)
        self.rows = math.ceil(height / cell_size)
        self.grid = {}

    def _cell_coords(self, x, y):
        return int(x // self.cell_size), int(y // self.cell_size)

    def clear(self):
        self.grid.clear()

    def add_entity(self, entity):
        cx, cy = self._cell_coords(entity.x, entity.y)
        key = (cx, cy)
        if key not in self.grid:
            self.grid[key] = []
        self.grid[key].append(entity)

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

