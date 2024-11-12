#### Install required libraries

`pip install -r requirements.txt`

#### Running the server

`python3 run.py`

#### Editing the data, i.e. modules and positions/rotations

See the `data.json` file.

#### Modification to route on the same layer

1. a. Update route_sockets to accept a list of nets that should be routed together on the same copper layer
1. b. Have an indicator as to which layer the routing should be on, for example layer=1 for the top copper layer

1. Route

#### New ideas/discussions

- What's the effective startegy for routing?
  (1) Algorithmic - path finding for every net [go for this]
  (2) Parametric/pre-defined - having routes go up/down, connect to a bus, or other consistent method
- How much do we care about modularity for other types of boards, apart from the micro:bit?
- Programming layer
  (a) What's the approach going to be
  (b) Impedence matched programming/debug lines?
  (c) Any additional hardware/button that will need to be places in the design?
- BOM generation and pick & place files
- Use GerberSocket layer to define apertures for 3D prints
- Thinking about the next step of MakeDevice i.e. removing the MCUs
  (a) MakeDevice should know about which components go together, there needs to metadata
  (b) Tiers of modules
  (1) Physical Jacdac modules that have a virtual mounting footprint
  (2) Virtual Jacdac modules, simply flattened (we are working on it now)
  (3) Virtual modules without MCUs, one central brain component

#### Progress

- Work completed since last meeting
  1. Fixed issues with generated traces cutting through the keep-out zones, particularly top and right side of the keep-out zones
  2. Fixed A\* search algorithm for pathfinding
  3. Implemented diagonal routing, breadth first search creates noticebly cleaner traces
  4. New layer_mappings parameters passed into generate_gebrer script, which specify which net goes on which layer
  5. Implemented detection of intersection
  6. Now removes traces that overlap on top of each other, entirely or partially
  7. Segment splitting (removing the old segment at the intersection and insering two new ones)
  8. 

#### TODO:

- [ ] Fix up the way layer mappings are passed onto the generate, maybe the EMPTY net is not necessary to puy through
- [ ] BUGS: fix the bugs that occur when rotating modules, UGH!

Other notes from the meeting:

Solid ground plane vs traces
Can use the one free layer to run trace/vias for routing on the top layer
