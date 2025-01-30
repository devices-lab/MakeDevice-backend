from pathfinding3d.core.diagonal_movement import DiagonalMovement as DiagonalMovement3D
from pathfinding3d.core.grid import Grid as Grid3D
from pathfinding3d.finder.a_star import AStarFinder as AStarFinder3D
from pathfinding3d.finder.breadth_first import BreadthFirstFinder as BreadthFirstFinder3D
import numpy as np


matrix_net = np.ones((10, 20), dtype=int)
matrix_tunnel = np.ones((10, 20), dtype=int)

matrix_net[:, 5] = 0 # obstacle
matrix_net[:, 15] = 0 # obstacle

matrix_tunnel[:, :] = 20

print("matric_tunnel")
print(matrix_tunnel)

print("matric_net")
print(matrix_net)

combined = np.stack((matrix_tunnel, matrix_net), axis=2)

grid = Grid3D(matrix=combined)

start = grid.node(5, 0, 1) # x, y, z
end = grid.node(5, 19, 1)

finder = AStarFinder3D(diagonal_movement=DiagonalMovement3D.never)
path, runs = finder.find_path(start, end, grid)

if path:
    grid.visualize(path=path, start=start, end=end, visualize_weight=True, save_html=True, save_to="path_visualization.html")
    print('operations:', runs, 'path length:', len(path))
else:
    print('no path')