"""
This uses Gerber step and repeat (SR) commands to copy board Gerbers rather than
Gerbonara's .offset() function. Gerbonara was corrupting geometry, like with the
Jacdac mounting-hole soldermask. SR also makes lighter-weight gerber files and tells
the fab explicitly that the geometry is meant to be the same in each repeated cell

Applying step and repeat to a whole gerber file is as simple as inserting these
at the start (after headers) and end of the file:

    %SRX3Y2I5.0J4.0*%
    ...
    %SR*%

But the problem is we need to merge the repeated board Gerbers with the panel
infrastructure (traces, etc), and merging is done with Gerbonara. And gerbonara
deletes the SR commands.

Gerbonara agressively normalizes everything: it renumbers apertures, rewrites G-codes,
inserts extra moves, collapses small coordinates, removes comments, and reformats 
numbers. Mercifully, the order that geometry is drawn is consistent, so if we can add
placeholders before and after the main board geometry, we can detect those placeholders 
after Gerbonara is done and replace them with the actual SR commands.

Unfortunately, Gerbonara's rewriting is so aggressive that almost no placeholder would
be reliably detectable after the merge. Can't use comments, macro definitions, or move 
commands. The only thing I could find that survives is a sequence of draws (D01), and 
even then the coordinate numbers change format. 

The working placeholder is a sequence of 16 draws with a specific up/down pattern and 
increasing X values, drawn with a high-numbered aperture that is guaranteed to be 
unique. Gerbonara will renumber the aperture, but it will still be a Dnn* select 
followed by 16 D01 lines with the same relative coordinate changes.

It looks like the number values themselves are actually preserved, so it wasn't needed
to look solely at relative changes. But it might be more robust anyway.

There's a problem, if the board's gerber origin isn't 0,0, then we need to offset their
board using Gerbonara anyway to get it back to 0,0 so it lines up with the panel 
infrastructure Gerbers. Since gerbonara's .offset() is the thing we're trying to avoid
with this absurd approach anyway, the solution is to offset all the panel infrastructure
object coordinates by -gerber origin before generating the panel Gerbers. This does mean
the origin of the final panel will be weird though.

Generated D01 placeholder:
    %ADD999C,0.001*%
    D999*
    X0Y0D02*
    X1000Y1000D01*
    X2000Y0D01*
    X3000Y-1000D01*
    X4000Y0D01*
    X5000Y-1000D01*
    X6000Y0D01*
    X7000Y1000D01*
    X8000Y0D01*
    X9000Y1000D01*
    X10000Y2000D01*
    X11000Y3000D01*
    X12000Y2000D01*
    X13000Y3000D01*
    X14000Y2000D01*
    X15000Y1000D01*
    X16000Y2000D01*
"""
# Vim search to find placeholders in files: \(X[-0-9]\+Y[-0-9]\+D0[1]\*\n\)\{16}

# NOTE: Code written by AI

import re

# ------------------------------------------------------------
# 1. Define the fingerprint patterns (1 = up, 2 = down)
# ------------------------------------------------------------

sr_open_pattern = [1,2,2,1,2,1,1,2,1,1,1,2,1,2,2,1]
sr_close_pattern = [2,1,1,2,1,2,2,1,2,2,1,1,2,1,1,2]

# Change to (1 -> 1, 2 -> -1)
def pattern_to_signs(pattern):
    return [1 if step == 1 else -1 for step in pattern[1:]]

sr_open_signs = pattern_to_signs(sr_open_pattern)
sr_close_signs = pattern_to_signs(sr_close_pattern)

# ------------------------------------------------------------
# 2. Generate D01 placeholder blocks from patterns
# ------------------------------------------------------------

def generate_d01_placeholder(pattern):
    x = 0
    y = 0
    step_size = 1000  # large enough to survive normalization
    lines = [
        "%ADD999C,0.001*%",  # D code high enough to be unique
        "D999*",             # select it (Gerbonara will renumber)
        "X0Y0D02*",          # starting move
    ]
    for step in pattern:
        x += step_size      # always move +X
        y += step_size if step == 1 else -step_size
        lines.append(f"X{x}Y{y}D01*")
    placeholder = "\n".join(lines) + "\n"
    # print("⚪️ Generated D01 placeholder:\n", placeholder)
    return placeholder

sr_open_placeholder = generate_d01_placeholder(sr_open_pattern)
sr_close_placeholder = generate_d01_placeholder(sr_close_pattern)


# ------------------------------------------------------------
# 3. Insert placeholders into Gerber file
# ------------------------------------------------------------

def insert_sr_placeholders(input_file_path, output_file_path):
    with open(input_file_path, 'r') as infile:
        lines = infile.readlines()

    # Find first non-header line
    insert_index = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not (stripped.startswith('%') or stripped.startswith('G04')):
            insert_index = i
            break
    else:
        insert_index = len(lines)

    modified_lines = (
        lines[:insert_index] +
        [sr_open_placeholder + "\n"] +
        lines[insert_index:]
    )

    modified_lines.append(sr_close_placeholder + "\n")

    with open(output_file_path, 'w') as outfile:
        outfile.writelines(modified_lines)


# ------------------------------------------------------------
# 4. Helpers: parse D01 block and compare sign pattern
# ------------------------------------------------------------

def parse_d01_line(line):
    m = re.match(r"X(-?\d+)Y(-?\d+)D01\*", line.strip())
    if not m:
        return None
    x = int(m.group(1))
    y = int(m.group(2))
    return x, y

def parse_d02_line(line):
    return bool(re.match(r"X-?\d+Y-?\d+D02\*", line.strip()))

"""
After seeing a Dnn*:
- Skip any number of lines that are:
    - Gxx*
    - X…Y…D02*
    - comments (G04, %, etc.)
    - blank lines
- Stop when you hit the first D01 line
- Collect exactly 16 D01 lines
- Compute sign(dY)
- Compare to open/close patterns
"""

def extract_d01_block_after(lines, start_index, length):
    """
    After start_index, skip any number of ignorable lines (G01*, D02*, comments),
    then read exactly `length` D01 lines.
    Returns (coords, consumed_lines) or (None, 0) on failure.
    """
    i = start_index
    consumed = 0

    # Skip ignorable lines until first D01
    while i < len(lines):
        line = lines[i].strip()

        # D01 line → stop skipping
        if re.match(r"X-?\d+Y-?\d+D01\*", line):
            break

        # Ignorable lines:
        if (
            line == "" or
            line.startswith("G") or
            line.startswith("%") or
            line.startswith("G04") or
            re.match(r"X-?\d+Y-?\d+D02\*", line)
        ):
            i += 1
            consumed += 1
            continue

        # Anything else breaks detection
        return None, 0

    # Now collect exactly `length` D01 lines
    coords = []
    for _ in range(length):
        if i >= len(lines):
            return None, 0

        parsed = parse_d01_line(lines[i])
        if not parsed:
            return None, 0

        coords.append(parsed)
        i += 1
        consumed += 1

    return coords, consumed     

def compute_sign_dy(coords):
    signs = []
    for i in range(len(coords) - 1):
        dy = coords[i+1][1] - coords[i][1]
        if dy == 0:
            return None  # we expect strictly up/down
        signs.append(1 if dy > 0 else -1)
    return signs

def is_strictly_increasing_x(coords):
    return all(coords[i+1][0] > coords[i][0] for i in range(len(coords) - 1))


# ------------------------------------------------------------
# 5. Replace placeholders with real SR commands + warnings
# ------------------------------------------------------------

def replace_sr_placeholders(input_file_path, output_file_path,
                            x_repeats, y_repeats, x_spacing, y_spacing):

    with open(input_file_path, 'r') as infile:
        lines = infile.readlines()

    block_len = len(sr_open_pattern)  # 16 D01 lines

    sr_open_command = f"%SRX{x_repeats}Y{y_repeats}I{x_spacing}J{y_spacing}*%\n"
    sr_close_command = "%SR*%\n"

    found_open = False
    found_close = False

    i = 0
    while i < len(lines):

        # Detect ANY aperture select: Dnn*
        m = re.match(r"D(\d+)\*", lines[i].strip())
        if m:
            # Try to extract a D01 block after this Dnn*
            coords, consumed = extract_d01_block_after(lines, i+1, block_len)
            if coords and is_strictly_increasing_x(coords):
                signs = compute_sign_dy(coords)
                if signs is not None:
                    # Compare to open pattern
                    if signs == sr_open_signs:
                        # Replace Dnn* + optional D02 + 16 D01 lines
                        lines[i:i+1+consumed] = [sr_open_command]
                        found_open = True
                        # print(f"⚪️ Replaced SR open placeholder at line {i}, in file {input_file_path}")
                        i += 1
                        continue
                    # Compare to close pattern
                    if signs == sr_close_signs:
                        lines[i:i+1+consumed] = [sr_close_command]
                        found_close = True
                        # print(f"⚪️ Replaced SR close placeholder at line {i}, in file {input_file_path}")
                        i += 1
                        continue

        i += 1

    if not found_open and not found_close:
        print("🔵 No SR placeholders found for file", input_file_path)
    elif not found_open:
        print("🔴 Error: SR open placeholder not found for file", input_file_path)
    elif not found_close:
        print("🔴 Error: SR close placeholder not found for file", input_file_path)
    else:
        print("🟢 Replaced SR placeholders for file", input_file_path)

    with open(output_file_path, 'w') as outfile:
        outfile.writelines(lines)
