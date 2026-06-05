"""
One-shot per-module socket and zone extractor for the frontend bus router
migration. Walks `backend_module_data/<name>_<version>/gerbers/*GerberSockets.gbr`,
runs the same extraction the backend uses at routing time, and dumps:

  <out-dir>/<name>_<version>/sockets.json
  <out-dir>/<name>_<version>/zones.json

Coordinates are in MODULE-LOCAL frame (no module placement transform applied);
the frontend runtime applies translate + rotate per placed instance to mirror
backend `process.merge_layers`.

Usage (run from backend dir, inside venv):
    python extract_module_sockets.py <out-dir>

`<out-dir>` should typically be `../MakeDevice/public/frontend_module_data` so
the JSON lands next to existing module assets.
"""

import json
import os
import sys
from pathlib import Path

# Silence unrelated backend prints to keep stdout clean.
os.environ["MAKEDEVICE_DEBUG_VISUAL"] = "0"

from gerbonara import GerberFile

from loader import Loader
from gerbersockets import Sockets, Zones


def _make_minimal_loader() -> Loader:
    """The Sockets/Zones constructors only need a few fields from Loader.
    Fake one without a project file so we can call them in isolation."""
    class _MiniLoader:
        # Mirror Loader defaults that gerbersockets reads.
        resolution = 0.25
        module_margin = 0
    return _MiniLoader()  # type: ignore[return-value]


def _extract_for_module(module_dir: Path, gerber_name: str = "GerberSockets.gbr"):
    """Returns (sockets_dict, zones_list) or (None, None) when no GerberSockets layer."""
    gerbers_dir = module_dir / "gerbers"
    if not gerbers_dir.is_dir():
        return None, None

    matches = list(gerbers_dir.glob(f"*{gerber_name}"))
    if not matches:
        return None, None

    gerber = GerberFile.open(matches[0])
    loader = _make_minimal_loader()

    sockets = Sockets(loader, gerber)
    zones = Zones(loader, gerber)

    sockets_dict = {
        net: [list(p) for p in pos] for net, pos in sockets.socket_locations.items()
    }
    zones_list = [
        [list(corner) for corner in z] for z in zones.zone_rectangles
    ]
    return sockets_dict, zones_list


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: extract_module_sockets.py <out-dir>\n")
        return 2

    out_root = Path(argv[1]).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    backend_dir = Path(__file__).resolve().parent
    modules_root = backend_dir / "backend_module_data"
    if not modules_root.is_dir():
        sys.stderr.write(f"missing {modules_root}\n")
        return 2

    written = 0
    skipped = 0
    for module_dir in sorted(modules_root.iterdir()):
        if not module_dir.is_dir():
            continue
        sockets_dict, zones_list = _extract_for_module(module_dir)
        if sockets_dict is None:
            sys.stderr.write(f"skip {module_dir.name}: no GerberSockets.gbr\n")
            skipped += 1
            continue

        target_dir = out_root / module_dir.name
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "sockets.json").write_text(json.dumps(sockets_dict, indent=2))
        (target_dir / "zones.json").write_text(json.dumps(zones_list, indent=2))
        written += 1
        sys.stderr.write(f"wrote {module_dir.name} ({len(sockets_dict)} nets, {len(zones_list)} zones)\n")

    sys.stderr.write(f"\nDone. wrote={written} skipped={skipped}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
