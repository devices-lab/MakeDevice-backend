#### Install required libraries

`pip install -r requirements.txt`

#### Running the server

`python3 run.py`

#### Editing the data, i.e. modules and positions/rotations

See the `data.json` file.


#### Next on TODO:

- blue socket doesn't connect when at 90 degrees, WHYYYYYY


1,5 units into the keepout zone, that's why it doesn't detect the connection
FIX: socket location to idex conversion is not correct

0 degree works fine, upper socket JD_GND has 0.5 units from the edge of the zone
socket location (402, 800) 
edge zone end y=401.5


360 doesn't work, moves the upper socket to 1.5 units from the edge of the zone
socket location (403, 800)
edge zone end y=401.5

transforming the shapes moves the socket location!


EXPERIMENTATION

under = socket location does not overlap the keep-out zone
over = socket location overlaps the keep-out zone

- no transformation -

JD_PWR (500, 700), edge y=699.5 (under)
JD_GND (500, 300), edge y=299.5 (over)
JD_DATA (400, 500), edge x=399.5 (over)

- 360 rotation - 
JD_PWR (500, 699), edge y=699.5 (over)
JD_GND (500, 301), edge y=299.5 (over) - 
JD_DATA (401, 500), edge x=399.5 (over) - ROUTE FAIL


observations:
1. edges didn't move
2. points moved 
