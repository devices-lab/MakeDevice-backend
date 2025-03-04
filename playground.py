from pathfinding.core.diagonal_movement import DiagonalMovement as DiagonalMovement3D
from pathfinding.core.grid import Grid as Grid3D
from pathfinding.finder.a_star import AStarFinder as AStarFinder3D
from pathfinding.finder.breadth_first import BreadthFirstFinder as BreadthFirstFinder3D
import numpy as np

matrix = np.ones((10, 20), dtype=int)

grid = Grid3D(matrix=matrix)

start = grid.node(5, 0) # x, y, z
end = grid.node(5, 9)

finder = AStarFinder3D(diagonal_movement=DiagonalMovement3D.never)
path, runs = finder.find_path(start, end, grid)

if path:
    print(grid.grid_str(path=path, start=start, end=end))
else:
    print('no path')