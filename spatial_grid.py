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

    def get_neighbors(self, entity):
        cx, cy = self._cell_coords(entity.x, entity.y)
        neighbors = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = (cx + dx, cy + dy)
                if cell in self.grid:
                    neighbors.extend(self.grid[cell])
        return neighbors
