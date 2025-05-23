## Setup
### Create a virtual environement and install required libraries

1. Create a virual environment with `python3 -m venv venv`
2. Activate it with `source venv/bin/activate`
3. Install dependencies `python3 -m pip install -r requirements.txt`

You must use Python version `3.11`, or lower, othewsie it won't work with some outdated dependencies (such as `gerbonara`). To control Python versions you may use the `pyenv` tool.

1. `brew install pyenv`
2. `pyenv install 3.11.0`
3. `pyenv global 3.11.0` to set globally or `pyenv local 3.11.0` to set in the current directory.

In the case this tools doesn't change your Python version (happens on an M-chip Mac), add `eval "$(pyenv init --path)"` to your ~/.zshrc and re-open the terminal.

### Firmware
Clone [picotool](https://github.com/raspberrypi/picotool.git) into `./picotool/` and follow [the steps](https://github.com/raspberrypi/picotool/blob/master/README.md) to build it. It is a requirement for producing .uf2 files, which are used for flashing boards with the rp2040 virtual module. 

### Running the server

Run the backend server with `python3 server.py`. You could run an offline test case instead such as `python3 run.py office-vm_net_map_0.3`

## Editing the data, i.e. configurations, modules, etc.

See the [`/test_data`](./test_data) directory

## Progress and updates

See [CHANGELOG](./changelog) for latest updates and progress

## Ideas in progress

#### JSON for each module

Each module available in MakeDevice should have a central JSON file with the following information

- Name
- Humam readable description
- Version
- Module size
- Designer name
- Functional name, i.e. `rotary-button` or `RGB-ring`
- Number of functional components
- MCU part number
- Last update date
- 3D file paths
- Alternate 3D file paths 
    - Kitten bot module floating on top
    - No components, just pads
- Module type (programmer/target/connector)
- Firmware descriptions
- List of GerberSockets
- Design rules - whether can extend to board edge, or not
- Stack-up in a given module
- Info about enclosure aperture (whether or not they are included in the GerberSockers layer)
- List of functional substitutes using the functional naming scheme

#### Module annotator

When a PCB design has been yet designed with GerberSockets, you can import your current PCB and socketify it.

#### Front-end features

- Collision detection
- Alignment, centering, auto-alignment
- AI prompt integration, possible with the JSON format for each module
- Distinction between 2D/3D preview - with enclosures, components/KittenBot modules
- Better UI and general flow of things
- Eventually, follow the MakeCode/CreateAI UI theme
- Add tex editor

#### Back-end features

- Support multiple keep-out zones
- Generate enclosures
- Silkscreen text
- More things...
