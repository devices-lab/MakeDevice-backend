#### Install required libraries

`pip install -r requirements.txt`

#### Running the server

`python3 run.py`

#### Editing the data, i.e. modules and positions/rotations

See the `data.json` file.

#### Next on TODO

- Fix drill file issues with merging
- Drill files contain Altium style comments to separate PTH/NPTH drill holes
- Board outlines for each individual module must be removed, and the board dimensions need to be passed on from the frontend

#### Problems

- When merging, the plated drills from the first module get put into ~test_module_1.drl file, and the remaining are not added
- The drill files from from the modules are not added into remaining of the MakeDevice-NPTH and PTH files
