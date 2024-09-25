#### Install required libraries

`pip install -r requirements.txt`

#### Running the server

`python3 run.py`

#### Editing the data, i.e. modules and positions/rotations

See the `data.json` file.


#### Next on TODO:





### TO FIX

- show_grid_segments_sockets is inverted compared to show_grid_routes_sockets
This is an issue somewhere with inverting the y-axis for the keep-out-zones or the socket-locations. I currently (24-09-2024 @ 22:20) do not have the time to fix this, as it is merely a debug function, but it would be good to enure that the y-axis coordiantes are consistent throughout the extraction and routing. I added the -ve sign to flip the socket-locations on the debug function `show_grid_segments_sockets` and it will do for debugging for now. Strangely all of the segments seem to have the correct coordinates for the inverted y-axis setup. Need to look into this when I have the time.

F_Cu.gbr - Top copper - JD_PWR
In1_Cu.gbr - Inner top copper - JD_DATA
In2_Cu.gbr - Inner bottom copper - SWD/DEBUGGING (work on later)
B_Cu.gbr - Bottom copper - JD_GND


TO FIX:
1. plated and non-plated drill files just end up merged onto an "unknown" drill file
2. inner layers are unrecognised and cause trouble
3. jacdac-bus layers don't get merged, but don't need to

maybe merge layer using GerberFile? one by one?