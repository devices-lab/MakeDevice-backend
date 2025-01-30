**Additions/new features**

- [ ] Re-organise the logic for the BOM and CLP logic to run separately from the Gerber generation phase (basically, in its own file and called separately from `run.py`. not mixed in with `generation.py`)
- [ ] Give full support to grid resolution being 0.1
- [ ] Implement routing sockets to any point on any path on the same net
- [ ] Check the correctness and shape of the passed JSON file, and type validity etc.
- [ ] Implement error handling to send messages back to the frontend
- [ ] Implement a server endpoint - look at what Kobi did when implemented it with the MakeDevice
- [ ] Add a flag for flooding an entire layer and add support for copper flood fills

**Issues**

- [ ] Finalise the shape of the passed JSON, and draft a shape for the device JSON for MakeDevice
- [ ] Increasing the margin to a value greater than 1 doesn't allow for routing due to the sockets not being exposed correctly
- [ ] A\* finder with 90-degree bends results in jagged and funky routes - can it get fixed? Perhaps try out some of the other finders
- [ ] Diagonal pathfinding for tunnels on a 3D grid does not work (currently set to DiagonalMovement3D.never)
- [ ] When merging overlapping segments, some vias seem to disappear (currently merging overlapping segments is turned off - see the logic in `manipulate.py`)
- [ ] Currently the tunneling layer does not take into consideration if there are any other traces/obstacles apart from the GerberSockets keep-out zones - need to take into consideration previous tunnels and other elemenents on the tunnel layers. 
- [ ] COnsider other elements on the layer which the TUNNELS go through, for example,there could be PROG traces, and therefore would need to set priority to other nets, and not TUNNELS, but also then set keep-out zones to those - need more time to think about this to come up with something smarter
- [ ] Do more testing, there are problems that will come up all the time

**Wed 15 Jan, 2025**

- [x] Fixed the issue with the socket location getting rounded to the nearest grid resolution value
- [x] Fixed keep-out zone extractions for the top-right corners
- [x] Solved an issue with not checking if the route goes inside of a keep-out zone when the route moves diagonally (cutting corners)
- [x] Implemented a margin as a better way to respect the keep-out zones
- [x] Removed breadth-first-search as it is less efficient, and only stick with A\* even though it looks a little more fuzzed
- [x] Fixed the issue with the temporary keep-out zones for vias being smaller for left and bottom located vias, and right and top are too large

**Thu 16 Jan, 2025**

- [x] Improved the logic to find the nearest positioned sockets to route them together, using UnionFind
- [x] Remove unecessary code, and simplied the heuristic
- [x] Resolve the issues of traces entering sockets diagonally, but leaving vertically/horizontally or vice versa
- [x] Tried out the `python-pathfinding` library to see if it is any good
- [x] Implemented the routing using the `python-pathfinding` library for improved efficiency
- [x] Fixed issues with keep-out zones not aligning on the same axis as the socket locations (took me 6 hours)

**Fri 17, Jan 2025**

- [x] Moved all configuration to a JSON file, including the layer mapping
- [x] Added support for selecting diagonal routing, or turning it off

**Mon 20, Jan 2025**

- [x] Improved layer mappings, and set it up so that keys are layers, and it only takes a list of nets
- [x] Fixed the way layer mappings are passed onto the generate function, the EMPTY net is not necessary anymore
- [x] Began to implement a new method to perform intersections - working on a new way using elevators layers of 2D grid = 3D grid (worlds)

**Tue 21, Jan 2025**

- [x] Implemented a new method to perform intersections using multiple grid conencted with elevators - turns out that it doesn't work exactly as intended, and has some quirks with moving up/down between layers
- [x] Re-implemented a new way using the `python-pathfinding3D` library, which supports 3D worlds by default without the need for elevators
- [x] Simplified and cleaned up the routing logic, and now it the routing will by default try to use 2D grid, and if no path is found AND another net is present, then it will try to find path using 3D grid
- [x] Adjusted the consolidation function, which now end previous segments and start new segments whenever the z-axis changes
- [x] Removed all the previous logic for preparing and generating intersections
- [x] Remaned `intersection.py` -> `manipulate.py`
- [x] Added logic for finding where vias should be inserted fr intersections with the tunnel layers
- [x] Added `playground.py` to play around with some of the features of `python-pathfinding3D` librar

**Wed 22, Jan 2025** 

- [x] Experimented once again with stacking 2D grids, but reverted changes back to 3D grids for tunnels
- [x] Updated `requirements.txt` with the latest packages

**Thursday 30, Jan 2025**

- [x] Fixed an issue where two perpendicular diagonal lines can cross each other even when one of them has been marked of as blocked - now using DiagonalMovement.if_at_most_one_obstacle when there are other nets on the layer.