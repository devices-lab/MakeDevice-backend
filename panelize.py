from pathlib import Path
import thread_context

# from process import merge_layers
# from process import merge_stacks
from consolidate import collect_references, process_cpl_file, group_components, write_consolidated_bom, write_consolidated_cpl
from process import compress_directory
from gerber_writer import DataLayer, Path as GPath, Rectangle

from gerbonara import GerberFile, ExcellonFile
import warnings

import os
import sys
import math
import subprocess
from datetime import datetime

from server_packets_panelize import PanelizeStartRequest

from module import Module

def progress(value: float):
    progress_file = thread_context.job_folder / "progress.txt"
    with open(progress_file, 'w') as file:
        file.write(str(value * 100))

def error(message: str):
    thread_context.error_message = message
    print("🔴 ", message)
    # Stop the thread when error occurs
    raise Exception(message)
    # return {
    #     "failed": True
    # }


def panelize(job_id: str, job_folder: Path, data: PanelizeStartRequest) -> dict:
    print("🟢 = OK")
    print("🟠 = WARNING")
    print("🔴 = ERROR")
    print("⚪️ = DEBUG")
    print("🔵 = INFO\n")

    thread_context.job_id = job_id
    thread_context.job_folder = Path(job_folder)

    # The Gerber layers we'd like to step, repeat and merge
    repeat_folder = thread_context.job_folder / "repeat_gerbers"
    os.makedirs(repeat_folder, exist_ok=True)

    # Output folder for merged gerbers
    output_folder = thread_context.job_folder / "output"
    os.makedirs(output_folder, exist_ok=True)

    count = data["fabSpec"]["count"]
    step = data["fabSpec"]["step"]
    gerber_origin = data["gerberOrigin"]

    if (len(data["fileTextLayers"]) == 0):
        return error("No fileTextLayers provided")



    # Save BOM and placement files to ./assembly
    assembly_folder = thread_context.job_folder / "assembly"
    os.makedirs(assembly_folder, exist_ok=True)

    # Find fileTextLayers for BOM and placement
    bom_layer = next((layer for layer in data["fileTextLayers"] if layer["layer"]["type"] == "bom"), None)
    placement_layer = next((layer for layer in data["fileTextLayers"] if layer["layer"]["type"] == "placement"), None)

    missing_assembly_data = False
    if bom_layer is not None:
        with open(assembly_folder / "BOM.csv", 'w') as file:
            file.write(bom_layer["content"])
    else:
        missing_assembly_data = "No BOM layer found"
    if placement_layer is not None:
        with open(assembly_folder / "CPL.csv", 'w') as file:
            file.write(placement_layer["content"])
    else:
        missing_assembly_data = "No placement layer found"

    if missing_assembly_data:
        print("🟠 " + missing_assembly_data + " - proceeding without assembly data")

    # Repeat and merge BOM
    # Step, repeat and merge placement files
    if (not missing_assembly_data):
        failed = consolidate_component_files(count, step, gerber_origin)
        if failed.get("failed", False):
            return failed



    # Step, repeat and merge each Gerber and drill layer
    layer_count = len(data["fileTextLayers"])
    for layer_index in range(layer_count):
        layer = data["fileTextLayers"][layer_index]

        side = layer["layer"]["side"] if layer["layer"]["side"] is not None else "none"
        type = layer["layer"]["type"] if layer["layer"]["type"] is not None else "none"
        if (type in ["drill-pth", "drill-npth"]):
            type = "drill"

        # Write each gerber file to the gerbers folder
        layer_filename = type + "_" + side + (".gbr" if type != "drill" else ".drl") # NOTE: Expects only one of each type/side combination
        # TODO: We shouldn't be identifying layers here, they should have been pre-identified (side and type properties)
        if (layer_filename == "drill_all.drl"):
            # FIXME: How to really make sure PTH and NPTH are identified, kept seperate, and merged correctly?
            if ("NPTH" in layer["name"]):
                layer_filename = "NPTH.drl"
            elif ("PTH" in layer["name"]):
                layer_filename = "PTH.drl"
            else:
                return error("Ambiguous drills: Expected 'PTH' or 'NPTH' in drill layer filename, but got " + layer["name"])

        # Skip simple gerber merging for these types
        if (type == "none" or type == "outline" or type == "drawing" or type == "bom" or type == "placement"):
            continue

        with open(repeat_folder / layer_filename, 'w') as file:
            file.write(layer["content"])

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # Step, repeat and merge the layer in gerbers_folder
            source_path = repeat_folder / layer_filename
            target_path = output_folder / layer_filename
            source = GerberFile.open(source_path) if type != "drill" else ExcellonFile.open(source_path)
            source.offset(gerber_origin["x"], -gerber_origin["y"]) # NOTE: Works with floats despite saying int, don't round it
            source.save(target_path)

            print(f"🔵 Stepping and repeating {layer_filename}...")

            target = GerberFile.open(target_path) if type != "drill" else ExcellonFile.open(target_path)

            progress( 0.9 * (layer_index / layer_count))
            for i in range(1, int(count["x"])):
                dx = i * step["x"]
                source.offset(dx, 0) # NOTE: Works with floats despite saying int, don't round it
                target = GerberFile.open(target_path) if type != "drill" else ExcellonFile.open(target_path)
                target.merge(source)
                target.save(target_path) # Save is super slow
                source.offset(-dx, 0)  # Reset position

            # Open target as source now to draw whole rows at once for massive speedup
            source = GerberFile.open(target_path) if type != "drill" else ExcellonFile.open(target_path)
            for j in range(1, int(count["y"])):
                dy = -j * step["y"]  # Invert Y axis
                source.offset(0, dy) # NOTE: Works with floats despite saying int, don't round it
                target = GerberFile.open(target_path) if type != "drill" else ExcellonFile.open(target_path)
                target.merge(source)
                target.save(target_path) # Save is super slow
                source.offset(0, -dy)  # Reset position

    # Write start request data to files in the job folder
    with open(thread_context.job_folder / "copperTop.svg", 'w') as file:
        file.write(data["svgCopperTop"])
    with open(thread_context.job_folder / "copperBot.svg", 'w') as file:
        file.write(data["svgCopperBottom"])
    with open(thread_context.job_folder / "soldermaskTop.svg", 'w') as file:
        file.write(data["soldermaskTop"])
    with open(thread_context.job_folder / "soldermaskBottom.svg", 'w') as file:
        file.write(data["soldermaskBottom"])
    with open(thread_context.job_folder / "vcut.svg", 'w') as file:
        file.write(data["vcut"])

    # Make panel folder
    panel_folder = thread_context.job_folder / "panel"
    os.makedirs(panel_folder, exist_ok=True)

    # Remove venv paths from PATH to access svg-flatten (svg-flatten is setup at system level, not in venv)
    env = os.environ.copy()
    venv_bin = sys.prefix + "/bin"
    if "site-packages" in sys.prefix or "venv" in sys.prefix:
        env["PATH"] = ":".join(p for p in env["PATH"].split(":") if p != venv_bin)

    # Turn SVG files into gerber files
    progress(0.95)
    # NOTE: The gerber-outline format is more likely to make 'line' and 'spot_circle' objects
    # instead of 'polygon' objects which fab houses treat like copper fills. 
    # I don't think gerber-outline can make polygons at all actually.
    subprocess.run(["wasi-svg-flatten", "--format", "gerber-outline", "copperTop.svg", "panel/copper_top.gbr"],
               cwd=thread_context.job_folder, env=env)
    subprocess.run(["wasi-svg-flatten", "--format", "gerber-outline", "copperBot.svg", "panel/copper_bottom.gbr"],
                cwd=thread_context.job_folder, env=env)
    # NOTE: Use of gerber-outline means we can't have rectangular pad soldermask openings, 
    # they'll just become lines with rounded edges
    subprocess.run(["wasi-svg-flatten", "--format", "gerber-outline", "soldermaskTop.svg", "panel/soldermask_top.gbr"],
                cwd=thread_context.job_folder, env=env)
    progress(0.99)
    subprocess.run(["wasi-svg-flatten", "--format", "gerber-outline", "soldermaskBottom.svg", "panel/soldermask_bottom.gbr"],
                cwd=thread_context.job_folder, env=env)

    subprocess.run(["wasi-svg-flatten", "vcut.svg", "output/vcut_all.gbr"],
                cwd=thread_context.job_folder, env=env)


    # Use gerber-writer to add rectangular pad copper and soldermask
    top = DataLayer('Copper,L1,Top,Signal')
    bot = DataLayer('Copper,L2,Bottom,Signal')
    mask_top = DataLayer('Soldermask,L1,Top,Signal')
    mask_bot = DataLayer('Soldermask,L2,Bottom,Signal')

    for pad in data["pads"]:
        tl, tr, _, br = pad
        sx = tr["x"] - tl["x"]
        sy = br["y"] - tr["y"]
        rect = Rectangle(sx, sy, "ConnectorPad")
        center = tl["x"] + sx / 2, -(tl["y"] + sy / 2)
        top.add_pad(rect, center)
        bot.add_pad(rect, center)

    for pad in data["padsSoldermask"]:
        tl, tr, _, br = pad
        sx = tr["x"] - tl["x"]
        sy = br["y"] - tr["y"]
        rect = Rectangle(sx, sy, "") # gerbonara gets rid of the function string anyway...
        center = tl["x"] + sx / 2, -(tl["y"] + sy / 2)
        mask_top.add_pad(rect, center)
        mask_bot.add_pad(rect, center)

    # Write the Gerber files
    # NOTE: Pads are done seperately from SVG flattening because we want a spot_rect, not polygon
    panel_pads_folder = thread_context.job_folder / "panel_pads"
    os.makedirs(panel_pads_folder, exist_ok=True)

    file_path = os.path.join(panel_pads_folder, "copper_top.gbr")
    with open(file_path, 'w') as file:
        file.write(top.dumps_gerber())
    file_path = os.path.join(panel_pads_folder, "copper_bottom.gbr")
    with open(file_path, 'w') as file:
        file.write(bot.dumps_gerber())
    file_path = os.path.join(panel_pads_folder, "soldermask_top.gbr")
    with open(file_path, 'w') as file:
        file.write(mask_top.dumps_gerber())
    file_path = os.path.join(panel_pads_folder, "soldermask_bottom.gbr")
    with open(file_path, 'w') as file:
        file.write(mask_bot.dumps_gerber())


    # Use gerber-writer to add board outline
    path_copper = GPath()
    dStr = data["boardOutlineD"] # SVG path 'd' attribute string

    # Parse the SVG path data to create the board outline (only supports M, L, A commands for now)
    commands = dStr.split(" ")
    i = 0
    current_pos = (0.0, 0.0)
    while i < len(commands):
        cmd = commands[i]
        if cmd == 'M':
            x = float(commands[i + 1])
            y = -float(commands[i + 2]) # Invert Y axis of d path
            path_copper.moveto((x, y))
            current_pos = (x, y)
            i += 3
        elif cmd == 'L':
            x = float(commands[i + 1])
            y = -float(commands[i + 2])
            path_copper.lineto((x, y))
            current_pos = (x, y)
            i += 3
        elif cmd == 'A':
            rx = float(commands[i + 1])
            ry = float(commands[i + 2])
            x_axis_rotation = float(commands[i + 3])
            large_arc_flag = int(commands[i + 4])
            sweep_flag = int(commands[i + 5])
            x = float(commands[i + 6])
            y = -float(commands[i + 7])

            # TODO: Calculate center of the arc (assuming rx == ry and no rotation)

            x1, y1 = current_pos
            x2, y2 = x, y
            r = rx

            dx = x2 - x1
            dy = y2 - y1
            d = math.hypot(dx, dy)

            # midpoint
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2

            # distance from midpoint to center
            h = math.sqrt(max(r*r - (d/2)*(d/2), 0))

            # perpendicular unit vector
            px = -dy / d
            py = dx / d

            # two possible centers
            cx1 = mx + px * h
            cy1 = my + py * h
            cx2 = mx - px * h
            cy2 = my - py * h

            # choose based on sweep flag
            def is_clockwise(cx, cy):
                return (x1 - cx)*(y2 - cy) - (y1 - cy)*(x2 - cx) < 0

            if sweep_flag == 1:  # clockwise
                cx, cy = (cx1, cy1) if is_clockwise(cx1, cy1) else (cx2, cy2)
            else:                # counter-clockwise
                cx, cy = (cx2, cy2) if is_clockwise(cx1, cy1) else (cx1, cy1)

            # Takes end point, center point, and direction
            path_copper.arcto((x, y), (cx, cy), '-' if sweep_flag == 1 else '+')
            current_pos = (x, y)
            i += 8
        else:
            raise ValueError(f"Unsupported SVG path command: {cmd}")

    # Add the constructed path to the layer with a trace width of 0.15 mm
    outline_layer = DataLayer("Outline,EdgeCuts", negative=False)
    outline_layer.add_traces_path(path_copper, 0.15, 'Outline')
    
    # Write the Gerber file
    file_path = os.path.join(output_folder, "outline_all.gbr")
    with open(file_path, 'w') as file:
        file.write(outline_layer.dumps_gerber())

    # Make via and bite holes (copper's already there for vias)
    via_hole_diameter = data["fabSpec"]["viaHoleDiameter"]
    
    # Drill file content
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    content = [
        "M48",
        f"; DRILL file SmartPanelizer date {timestamp}",
        "; FORMAT={-:-/ absolute / metric / decimal}",
        f"; #@! TF.CreationDate,{timestamp}",
        "; #@! TF.GenerationSoftware,Kicad,Pcbnew,8.0.2-1",
        "; #@! TF.FileFunction,Plated,1,2,PTH",
        "FMAT,2",
        "METRIC",
        "; #@! TA.AperFunction,Plated,PTH,ViaDrill",
        f"T1C{via_hole_diameter:.3f}",
        "%",
        "G90",
        "G05",
        "T1"
    ]

    # Adding drill locations from socket_locations
    for drill_hole in data["vias"]:
        content.append(f"X{drill_hole['x']:.2f}Y{-drill_hole['y']:.2f}")  # Invert Y axis
    
    content.append("M30") # End of program

    # Save drill file
    file_path = os.path.join(panel_folder, "PTH.drl")
    with open(file_path, 'w') as file:
        file.write('\n'.join(content))

    # Make bite holes (non-plated)
    bite_hole_diameter = data["fabSpec"]["biteHoleDiameter"]
    fab_rail_hole_diameter = data["fabSpec"]["fabRailHoleDiameter"]
    content = [
        "M48",
        f"; DRILL file SmartPanelizer date {timestamp}",
        "; FORMAT={-:-/ absolute / metric / decimal}",
        f"; #@! TF.CreationDate,{timestamp}",
        "; #@! TF.GenerationSoftware,Kicad,Pcbnew,8.0.2-1",
        "; #@! TF.FileFunction,Non-Plated,1,2,NPTH",
        "FMAT,2",
        "METRIC",
        "; #@! TA.AperFunction,Non-Plated,NPTH,BiteHole",
        f"T1C{bite_hole_diameter:.3f}",
        f"T2C{fab_rail_hole_diameter:.3f}",
        "%",
        "G90",
        "G05",
        "T1"
    ]

    # Adding drill locations from bite holes
    for drill_hole in data["biteHoles"]:
        content.append(f"X{drill_hole['x']:.2f}Y{-drill_hole['y']:.2f}")  # Invert Y axis

    content.append("T2")
    for drill_hole in data["fabRailHoles"]:
        content.append(f"X{drill_hole['x']:.2f}Y{-drill_hole['y']:.2f}")  # Invert Y axis

    content.append("M30") # End of program

    # Save drill file
    file_path = os.path.join(panel_folder, "NPTH.drl")
    with open(file_path, 'w') as file:
        file.write('\n'.join(content))

    # Merge layers from panel_pads folder into panel folder
    for layer_filename in ["copper_top.gbr", "copper_bottom.gbr", "soldermask_top.gbr", "soldermask_bottom.gbr"]:
        source_path = panel_pads_folder / layer_filename
        target_path = panel_folder / layer_filename
        if source_path.exists():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                print(f"🔵 Merging pad layer: {layer_filename}...")

                # Merge the panel pads into the panel layer
                source = GerberFile.open(source_path)
                target = GerberFile.open(target_path)
                target.merge(source)
                target.save(target_path)
        else:
            print(f"🟠 No pad layer found for {layer_filename}, skipping pad merging for this layer")

    # Merge the generated panel layers into the (step and repeated) user gerber layers
    for layer_filename in [
        "copper_top.gbr", "copper_bottom.gbr", "soldermask_top.gbr", "soldermask_bottom.gbr"
    ]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            print(f"🔵 Merging panel layer: {layer_filename}...")

            # Merge the panel layer in gerbers_folder
            source_path = panel_folder / layer_filename
            target_path = output_folder / layer_filename
            source = GerberFile.open(source_path)
            target = GerberFile.open(target_path)
            target.merge(source)
            target.save(target_path)

    # Put vcut on board outline layer (JLC requirement)
    source_path = output_folder / "vcut_all.gbr"
    target_path = output_folder / "outline_all.gbr"
    source = GerberFile.open(source_path)
    target = GerberFile.open(target_path)
    target.merge(source)
    target.save(target_path)
    os.remove(source_path)  # Remove seperate vcut file after merging

    # Merge PTH drill files
    source_path = panel_folder / "PTH.drl"
    target_path = output_folder / "PTH.drl"
    source = ExcellonFile.open(source_path)
    target = ExcellonFile.open(target_path)
    target.merge(source)
    target.save(target_path)

    source_path = panel_folder / "NPTH.drl"
    target_path = output_folder / "NPTH.drl"
    source = ExcellonFile.open(source_path)
    target = ExcellonFile.open(target_path)
    target.merge(source)
    target.save(target_path)

    # Convert all .gbr to protel extensions (not required, but might help with layer identification)
    for file in os.listdir(output_folder):
        if file.endswith(".gbr"):
            base = os.path.splitext(file)[0]
            ext = ""
            if "copper_top" in base:
                ext = ".GTL"
            elif "copper_bottom" in base:
                ext = ".GBL"
            elif "soldermask_top" in base:
                ext = ".GTS"
            elif "soldermask_bottom" in base:
                ext = ".GBS"
            elif "silkscreen_top" in base:
                ext = ".GTO"
            elif "silkscreen_bottom" in base:
                ext = ".GBO"
            elif "outline_all" in base:
                ext = ".GM1"
            elif "solderpaste_top" in base:
                ext = ".GTP"
            elif "solderpaste_bottom" in base:
                ext = ".GBP"
            else:
                continue  # Skip files that don't match known types

            os.rename(
                output_folder / file,
                output_folder / (base + ext)
            )
    
    compress_directory(thread_context.job_folder / "output")

    # Write to a text fail indicating zip ready
    with open(thread_context.job_folder / "zip_ready.txt", 'w') as file:
        file.write("ready")


    print("🟢 Finished job ID: ", thread_context.job_id)

    return {
        "failed": False
    }

def consolidate_component_files(count, step, gerber_origin) -> dict:
    """
    Adaptation of same-named function from consolidate.py to work for panelization
    """
    # Convert paths to Path objects
    output_dir = thread_context.job_folder / "output"
    assembly_dir = thread_context.job_folder / "assembly"
    bom_file_path = assembly_dir / "BOM.csv"
    cpl_file_path = assembly_dir / "CPL.csv"

    # Dictionary to store all components with their unique reference designators
    # ~~Key format: "module_index:module_name:original_ref" -> ensures uniqueness across duplicate modules~~
    all_components = {}
    
    # Dictionary to track reference designator remapping
    # Key: "module_index:module_name:original_ref", Value: "new_unique_ref"
    ref_mapping = {}
    
    # Dictionary to track the CPL data for each component
    cpl_entries = {}
    
    # Track used reference prefixes to avoid duplicates
    used_refs = set()
    
    modules = []

    # First pass: collect all reference designators and assign unique ones
    for y_index in range(int(count["y"])):
        for x_index in range(int(count["x"])):

            # Pretend the user's board is a module to reuse existing code
            module = Module("panel_board", "1.0", (
                x_index * step["x"] + gerber_origin["x"],
                y_index * step["y"] + gerber_origin["y"]
            ), 0)
            modules.append(module)

            # Process BOM file and collect references - using module_idx to ensure uniqueness
            collect_references(
                bom_file_path, 
                cpl_file_path, 
                module, 
                ref_mapping, 
                all_components, 
                used_refs, 
                len(modules) - 1
            )
    print(f"🔵 Created {len(all_components)} component instances from BOM")
    
    # Process component grouping (same value and package get same part number)
    component_groups = group_components(all_components)
    print(f"🔵 Created {len(component_groups)} groups of same component")
    
    # Second pass: Process CPL files with updated reference designators
    for module_idx, module in enumerate(modules):
        # Process CPL file with updated references - using module_idx to match with first pass
        process_cpl_file(cpl_file_path, module, ref_mapping, cpl_entries, module_idx)
    
    # Write consolidated BOM to output file
    write_consolidated_bom(component_groups, output_dir, "panel")
    bom_name = "BOM_panel.csv"
    if (output_dir / bom_name).exists():
        os.rename(output_dir / bom_name, output_dir / "full_panel_BOM.csv")
    else:
        error("Failed to write consolidated BOM file")

    # Write consolidated CPL to output file
    write_consolidated_cpl(cpl_entries, output_dir, "panel")
    cpl_name = "CPL_panel-top-pos.csv"
    if (output_dir / cpl_name).exists():
        os.rename(output_dir / cpl_name, output_dir / "full_panel_CPL.csv")
    else:
        error("Failed to write consolidated CPL file")

    return {
        "failed": False
    }
