**TODO**

- [ ] Improve layer mappings, and set it up so that keys are layers, and it only takes a list of nets (one of those specified
- [ ] Fix up the way layer mappings are passed onto the generate, maybe the EMPTY net is not necessary to put through
- [ ] Set up the intersections using elevators and world 
- [ ] Re-work the intersections
- [ ] Re-organise the logic for the BOM and CLP logic to run separately from the Gerber generation phase
- [ ] When setting the grid resolution to 0.1, it doesn't work when it does work in 1 grid resolution
- [ ] Fix up JSON extractions and maybe alter the shape of the JSON file
- [ ] Check the correctness and shape of the JSON file, and validity of the file names, etc.
- [ ] Implement error handling
- [ ] Implement a server endpoint


**Issues**

- [ ] Increasing the margin to a value greater than 1 doesn't allow for routing due to the sockets not being exposed correctly

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

- [ ]
