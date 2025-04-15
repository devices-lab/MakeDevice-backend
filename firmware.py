"""
This script generates the firmware needed for the microbit(s) and/or rp2040 brain(s)
to act as a programmer probe, automatically flashing all virtual module MCUs
connected via SWDIO traces.

It needs an output/firmware.json file with the following structure:
e.g:
{ modules: [
    { name: "vm_jacdaptor_0.1", nets: [ "SWDIO_8", "SWDIO_1", "SWDIO_6", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] },
    { name: "vm_light_sensor_0.2", nets: [ "SWDIO_8", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] },
    { name: "vm_rotary_button_0.2", nets: [ "SWDIO_1", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] },
    { name: "vm_keycap_button_0.2", nets: [ "SWDIO_6", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] },
] }

It identifies brain modules (programmers) and peripherals (virtual modules)
based on keywords and SWDIO connections.

It also needs base microbit.bin and pico.bin files, containing the programmer probe
logic and firmware placeholders which this script replaces with the actual firmware
for each virtual module (modules/<name>/firmware.bin) - 32KB bin for STM32G030

Any pico.bin is converted to pico.uf2 and any microbit.bin to microbit.hex

If there are multiple brains, it will create a copy of the firmware for each brain,
e.g. microbit.hex, microbit-2.hex, pico-3.uf2
"""

import json
import shutil
import os
import sys
import subprocess

binaries = set()


def load_json(json_data):
    """Load JSON data and return lists of brain modules and peripherals."""
    modules = json_data["modules"]

    # Identify brain modules (must have a SWDIO connection to count)
    brain_keywords = ["jacdaptor", "rp2040"]
    brains = [
        mod
        for mod in modules
        if any(keyword in mod["name"] for keyword in brain_keywords)
        and any("SWDIO_" in net for net in mod["nets"])
    ]

    print(
        f"Identified {len(brains)} programmer modules with SWDIO nets: {[mod['name'] for mod in brains]}"
    )

    # Identify peripherals (modules not classified as brains, also with SWDIO connections)
    peripherals = [
        mod
        for mod in modules
        if mod not in brains and any("SWDIO_" in net for net in mod["nets"])
    ]
    print(
        f"Identified {len(peripherals)} peripheral modules with SWDIO nets: {[mod['name'] for mod in peripherals]}"
    )

    return brains, peripherals


def find_matching_module(swdio_net, peripherals):
    """Find a peripheral module matching the given SWDIO net."""
    matching_modules = [mod for mod in peripherals if swdio_net in mod["nets"]]

    if len(matching_modules) == 0:
        raise ValueError(f"Error: No module found matching SWDIO net '{swdio_net}'.")
    if len(matching_modules) > 1:
        raise ValueError(
            f"Error: Multiple non-programmer modules match SWDIO net '{swdio_net}'. Expected only one."
        )

    return matching_modules[0]


def ensure_target_copy(brain_name, index):
    """Ensure a unique copy of the firmware base file is created for each brain."""
    if "jacdaptor" in brain_name:
        base_name = "microbit.bin"
        if index == 0:
            target_name = "output/microbit.bin"
        else:
            target_name = f"output/microbit-{index + 1}.bin"
    else:
        base_name = "pico.bin"
        if index == 0:
            target_name = "output/pico.bin"
        else:
            target_name = f"output/pico-{index + 1}.bin"

    # Ensure output directory exists
    if not os.path.exists("output"):
        os.makedirs("output")

    # Check if the source firmware file exists
    if not os.path.exists(base_name):
        raise FileNotFoundError(f"Error: Source firmware file '{base_name}' not found.")

    # Copy the firmware file, ensuring each brain gets a unique version
    shutil.copyfile(base_name, target_name)

    return target_name


def replace_firmware(target_bin, sub_bin, swdio_num):
    """Replace the first instance of the placeholder string in target.bin with sub.bin contents."""
    placeholder = f"FIRMWARE_PLACEHOLDER_{swdio_num}".encode()

    if not os.path.exists(sub_bin):
        raise FileNotFoundError(
            f"Error: Substitution firmware file '{sub_bin}' not found."
        )

    with open(target_bin, "rb") as f:
        target_data = f.read()

    placeholder_index = target_data.find(placeholder)
    if placeholder_index == -1:
        raise ValueError(
            f"Error: Placeholder '{placeholder.decode()}' not found in {target_bin}."
        )

    with open(sub_bin, "rb") as f:
        sub_data = f.read()

    sub_data = sub_data[: 32 * 1024].ljust(32 * 1024, b"\x00")

    modified_data = (
        target_data[:placeholder_index]
        + sub_data
        + target_data[placeholder_index + 32 * 1024 :]
    )

    with open(target_bin, "wb") as f:
        f.write(modified_data)

    print(
        f"Firmware replacement for slot {swdio_num} successful in {target_bin} using {sub_bin}"
    )


def process_firmware(json_data):
    """Main function to process firmware replacements for each brain."""
    try:
        brains, peripherals = load_json(json_data)
    except ValueError as e:
        print(e)
        sys.exit(1)

    for index, brain in enumerate(brains):
        try:
            target_bin = ensure_target_copy(brain["name"], index)
            processed_swdio = set()

            for swdio_net in brain["nets"]:
                if "SWDIO_" in swdio_net:
                    if swdio_net in processed_swdio:
                        raise ValueError(
                            f"Error: Duplicate SWDIO connection '{swdio_net}' found in brain '{brain['name']}'."
                        )

                    processed_swdio.add(swdio_net)

                    match_mod = find_matching_module(swdio_net, peripherals)
                    sub_bin = f"modules/{match_mod['name']}/firmware.bin"

                    replace_firmware(target_bin, sub_bin, swdio_net.split("_")[1])
            binaries.add(target_bin)

        except (FileNotFoundError, ValueError) as e:
            print(e)
            sys.exit(1)


def convert_firmware(target_bin):
    """Convert the firmware binary to the required format for uploading to a programmer."""

    # Determine output filename based on type
    if "pico" in target_bin:
        if shutil.which("uf2conv") is None:
            raise EnvironmentError(
                "Error: uf2conv is not installed. Please install it to proceed. `python3 -m pip install --pre -U git+https://github.com/makerdiary/uf2utils.git@main`"
            )

        output_file = target_bin.replace(".bin", ".uf2")
        convert_command = f"uf2conv {target_bin} -o {output_file}"

    elif "microbit" in target_bin:
        output_file = target_bin.replace(".bin", ".hex")
        convert_command = f"objcopy -I binary -O ihex {target_bin} {output_file}"

    else:
        raise ValueError(
            "Unsupported firmware type for conversion. Expected 'pico' or 'microbit' in filename."
        )

    if not os.path.exists(target_bin):
        raise FileNotFoundError(f"Error: Firmware binary '{target_bin}' not found.")

    try:
        subprocess.run(convert_command.split(), check=True)
        print(f"Conversion successful: {target_bin} → {output_file}")
    except subprocess.CalledProcessError:
        raise RuntimeError(f"Error converting firmware {target_bin}.")

    # Remove the original binary after conversion
    os.remove(target_bin)

    return output_file


if __name__ == "__main__":
    # json_input = """
    # { "modules": [ { "name": "jacdac_connector_0.1", "nets": [  ] }, { "name": "vm_light_sensor_0.2", "nets": [ "SWDIO_8", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_jacdaptor_0.1", "nets": [ "SWDIO_8", "SWDIO_1", "SWDIO_6", "SWDIO_3", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_rotary_button_0.2", "nets": [ "SWDIO_1", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_keycap_button_0.2", "nets": [ "SWDIO_6", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_rgb_ring_0.2", "nets": [ "SWDIO_3", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] } ] }
    # """
    # json_input = """
    # { "modules": [ { "name": "jacdac_connector_0.1", "nets": [  ] }, { "name": "vm_light_sensor_0.2", "nets": [ "SWDIO_8", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_rp2040.1", "nets": [ "SWDIO_8", "SWDIO_1", "SWDIO_6", "SWDIO_3", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_rotary_button_0.2", "nets": [ "SWDIO_1", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_keycap_button_0.2", "nets": [ "SWDIO_6", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_rgb_ring_0.2", "nets": [ "SWDIO_3", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] } ] }
    # """
    # json_input = """
    # { "modules": [ { "name": "jacdaptor_connector_0.1", "nets": [ "SWDIO_10" ] },{ "name": "jacdac_connector_0.1", "nets": [ "SWDIO_10" ] }, { "name": "vm_light_sensor_0.2", "nets": [ "SWDIO_8", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_jacdaptor_0.1", "nets": [ "SWDIO_8", "SWDIO_1", "SWDIO_6", "SWDIO_3", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_rotary_button_0.2", "nets": [ "SWDIO_1", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_keycap_button_0.2", "nets": [ "SWDIO_6", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_rgb_ring_0.2", "nets": [ "SWDIO_3", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] } ] }
    # """
    # json_input = """
    # { "modules": [ { "name": "rp2040_connector_0.1", "nets": [ "SWDIO_10" ] },{ "name": "jacdac_connector_0.1", "nets": [ "SWDIO_10" ] }, { "name": "vm_light_sensor_0.2", "nets": [ "SWDIO_8", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_jacdaptor_0.1", "nets": [ "SWDIO_8", "SWDIO_1", "SWDIO_6", "SWDIO_3", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_rotary_button_0.2", "nets": [ "SWDIO_1", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_keycap_button_0.2", "nets": [ "SWDIO_6", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] }, { "name": "vm_rgb_ring_0.2", "nets": [ "SWDIO_3", "JD_PWR", "GND", "JD_DATA", "SWCLK", "RESET" ] } ] }
    # """

    # Load JSON data from output/firmware.json
    with open("output/firmware.json", "r") as f:
        json_input = f.read()

    json_data = json.loads(json_input)
    process_firmware(json_data)
    for binary in binaries:
        try:
            convert_firmware(binary)
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            print(e)
            sys.exit(1)
