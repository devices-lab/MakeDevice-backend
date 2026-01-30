from pathlib import Path
from thread_context import thread_context

# from process import merge_layers
# from process import merge_stacks
# from consolidate import consolidate_component_files
from process import compress_directory
from gerber_writer import DataLayer, Path as GPath

import os
import sys
import math
import subprocess
from datetime import datetime

from server_packets_panelize import PanelizeStartRequest

def progress(value: float):
    progress_file = thread_context.job_folder / "progress.txt"
    with open(progress_file, 'w') as file:
        file.write(str(value * 100))

def panelize(job_id: str, job_folder: Path, data: PanelizeStartRequest) -> dict:
    print("🟢 = OK")
    print("🟠 = WARNING")
    print("🔴 = ERROR")
    print("⚪️ = DEBUG")
    print("🔵 = INFO\n")

    thread_context.job_id = job_id
    thread_context.job_folder = Path(job_folder)

    # Write start request data to files in the job folder
    with open(thread_context.job_folder / "copperTop.svg", 'w') as file:
        file.write(data["svgCopperTop"])
    with open(thread_context.job_folder / "copperBot.svg", 'w') as file:
        file.write(data["svgCopperBottom"])
    with open(thread_context.job_folder / "soldermaskTop.svg", 'w') as file:
        file.write(data["soldermaskTop"])
    with open(thread_context.job_folder / "soldermaskBottom.svg", 'w') as file:
        file.write(data["soldermaskBottom"])

    # Remove venv paths from PATH (svg-flatten set up at system level, not in venv)
    env = os.environ.copy()
    venv_bin = sys.prefix + "/bin"
    if "site-packages" in sys.prefix or "venv" in sys.prefix:
        env["PATH"] = ":".join(p for p in env["PATH"].split(":") if p != venv_bin)

    # Turn SVG files into gerber files
    progress(0.3)
    subprocess.run(["wasi-svg-flatten", "copperTop.svg", "output/F_Cu.gtl"],
               cwd=thread_context.job_folder, env=env)
    progress(0.5)
    subprocess.run(["wasi-svg-flatten", "copperBot.svg", "output/B_Cu.gbl"],
                cwd=thread_context.job_folder, env=env)
    progress(0.7)
    subprocess.run(["wasi-svg-flatten", "soldermaskTop.svg", "output/F_Mask.gts"],
                cwd=thread_context.job_folder, env=env)
    progress(0.9)
    subprocess.run(["wasi-svg-flatten", "soldermaskBottom.svg", "output/B_Mask.gbs"],
                cwd=thread_context.job_folder, env=env)

    output_dir = thread_context.job_folder / "output"

    # Use gerber-writer to add board outline
    outline_layer = DataLayer("Outline,EdgeCuts", negative=False)
    path = GPath()
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
            path.moveto((x, y))
            current_pos = (x, y)
            i += 3
        elif cmd == 'L':
            x = float(commands[i + 1])
            y = -float(commands[i + 2])
            path.lineto((x, y))
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
            path.arcto((x, y), (cx, cy), '-' if sweep_flag == 1 else '+')
            current_pos = (x, y)
            i += 8
        else:
            raise ValueError(f"Unsupported SVG path command: {cmd}")

    # Add the constructed path to the layer with a trace width of 0.15 mm
    outline_layer.add_traces_path(path, 0.15, 'Outline')
    
    # Write the Gerber file
    file_path = os.path.join(output_dir, "Edge_Cuts.gm1")
    with open(file_path, 'w') as file:
        file.write(outline_layer.dumps_gerber())

    # Make via and bite holes (copper's already there for vias)
    via_hole_diameter = data["fabSpec"]["viaHoleDiameter"]
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
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
    file_path = os.path.join(output_dir, "PTH.drl")
    with open(file_path, 'w') as file:
        file.write('\n'.join(content))

    # Make bite holes (non-plated)
    bite_hole_diameter = data["fabSpec"]["biteHoleDiameter"]
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
        "%",
        "G90",
        "G05",
        "T1"
    ]

    # Adding drill locations from bite holes
    for drill_hole in data["biteHoles"]:
        content.append(f"X{drill_hole['x']:.2f}Y{-drill_hole['y']:.2f}")  # Invert Y axis

    content.append("M30") # End of program

    # Save drill file
    file_path = os.path.join(output_dir, "NPTH.drl")
    with open(file_path, 'w') as file:
        file.write('\n'.join(content))

    # Merge the GerberSockets layers from all individual modules
    # gerbersockets_layer = merge_layers(
    #     board.modules, loader.gerbersockets_layer_name, board.name
    # )

    # Suppress warnings from Gerbonara during generation
    # with warnings.catch_warnings():
    #     warnings.simplefilter("ignore")
    #     generate(board)
    #     merge_stacks(board.modules, board.name)
    #     consolidate_component_files(board.modules, board.name)

    compress_directory(thread_context.job_folder / "output")

    print("🟢 Finished job ID: ", thread_context.job_id)

    return {
        "failed": False
    }
