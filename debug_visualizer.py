import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle, Circle

from board import Board
from objects import Point


def _has_display() -> bool:
    return bool(os.environ.get("DISPLAY")) or os.name == "nt"


def visual_debug_enabled() -> bool:
    return os.environ.get("MAKEDEVICE_DEBUG_VISUAL", "0") == "1"


class RoutingDebugger:
    def __init__(self, board: Board, router, title: str) -> None:
        self.board = board
        self.router = router
        self.title = title
        self.step_mode = True
        self._advance = False
        self._enabled = True
        self._artist_info = {}
        self._socket_meta = {}
        self._pending_events: List[str] = []
        self._all_sockets: List[Tuple[str, Tuple[float, float]]] = []
        self._done_sockets: set[Tuple[str, Tuple[float, float]]] = set()

        # Force interactive backend when possible
        has_display = _has_display()
        if has_display:
            matplotlib.use("TkAgg")
        else:
            matplotlib.use("Agg")

        import matplotlib.pyplot as plt

        self.plt = plt
        self._apply_theme()
        self.plt.ion()
        self.fig = self.plt.figure(figsize=(12, 7))
        grid = self.fig.add_gridspec(1, 2, width_ratios=[3.2, 1.2], wspace=0.05)
        self.ax = self.fig.add_subplot(grid[0, 0])
        panel_grid = grid[0, 1].subgridspec(2, 1, height_ratios=[2.2, 1.0], hspace=0.15)
        self.events_ax = self.fig.add_subplot(panel_grid[0, 0])
        self.status_ax = self.fig.add_subplot(panel_grid[1, 0])
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)
        self.fig.canvas.mpl_connect("pick_event", self._on_pick)
        self.info_text = self.ax.text(
            0.01,
            0.99,
            "",
            transform=self.ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            color="#2D3748",
            bbox=dict(facecolor="#FFFFFF", alpha=0.92, edgecolor="#CBD5E0", boxstyle="round,pad=0.5"),
            zorder=20,
        )
        if not has_display:
            self.step_mode = False

        self._init_panel()

    def log_event(self, message: str) -> None:
        self._pending_events.append(message)

    def set_routing_status(
        self,
        all_sockets: List[Tuple[str, Tuple[float, float]]],
        done_sockets: set[Tuple[str, Tuple[float, float]]],
    ) -> None:
        self._all_sockets = all_sockets
        self._done_sockets = done_sockets
        
        # Check for duplicate socket positions
        pos_count = {}
        for net, pos in all_sockets:
            key = (net, pos)
            pos_count[key] = pos_count.get(key, 0) + 1
        
        duplicates = {k: v for k, v in pos_count.items() if v > 1}
        if duplicates:
            for (net, pos), count in duplicates.items():
                self.log_event(f"⚠️  DUPLICATE: {count}x socket at net={net}, pos={pos}")

    def _on_key(self, event) -> None:
        if event.key in {" ", "enter", "n"}:
            self._advance = True
        elif event.key == "c":
            self.step_mode = False
            self._advance = True
        elif event.key == "p":
            self.step_mode = True
        elif event.key == "q":
            self._enabled = False
            self.plt.close(self.fig)

    def _on_pick(self, event) -> None:
        artist = event.artist
        if artist in self._artist_info:
            self._set_info(self._artist_info[artist])
            return
        if artist in self._socket_meta and hasattr(event, "ind") and event.ind is not None:
            indices = event.ind
            meta = self._socket_meta[artist]
            if indices is not None and len(indices):
                idx = indices[0]
                net_name = meta["net"]
                pos = meta["positions"][idx]
                self._set_info(f"socket | net={net_name} | x={pos[0]:.2f}, y={pos[1]:.2f}")

    def step(
        self,
        stage: str,
        grid: Optional[np.ndarray] = None,
        net_name: Optional[str] = None,
        socket: Optional[Tuple[float, float]] = None,
        bus_point: Optional[Point] = None,
        path: Optional[List[Tuple[int, int, int]]] = None,
    ) -> None:
        if not self._enabled:
            return

        self._artist_info = {}
        self._socket_meta = {}
        self.ax.clear()
        self.events_ax.clear()
        self.status_ax.clear()
        self._draw_board_outline()
        self._draw_zones()
        self._draw_modules()
        self._draw_buses()
        self._draw_traces()
        self._draw_vias()
        self._draw_sockets()

        if grid is not None:
            self._draw_grid(grid)

        if socket:
            self._draw_socket_highlight(socket)

        if bus_point:
            self._draw_bus_point(bus_point)

        if path:
            self._draw_candidate_path(path, net_name)

        title = stage
        if net_name:
            title = f"{stage} | net={net_name}"
        self.ax.set_title(title)

        if self.step_mode:
            self._set_info("Step mode: press Space/Enter/n to advance, c=continue, p=pause, q=quit")

        self._draw_panel(stage, net_name)

        self._finalize_axes()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        self.plt.pause(0.001)

        if self.step_mode:
            self._wait_for_step()

        self._pending_events = []

    def _wait_for_step(self) -> None:
        self._advance = False
        while self._enabled and not self._advance:
            self.plt.pause(0.05)

    def _draw_board_outline(self) -> None:
        x0 = -self.board.width / 2
        y0 = -self.board.height / 2
        rect = Rectangle(
            (x0, y0),
            self.board.width,
            self.board.height,
            linewidth=2,
            edgecolor="#2D3748",
            facecolor="none",
            linestyle="-",
            zorder=2,
        )
        self.ax.add_patch(rect)
        self._artist_info[rect] = "board outline"

    def _draw_zones(self) -> None:
        if not self.board.zones:
            return
        for zone in self.board.zones.get_data():
            bl, _, tr, _ = zone
            width = tr[0] - bl[0]
            height = tr[1] - bl[1]
            rect = Rectangle(
                (bl[0], bl[1]),
                width,
                height,
                linewidth=1.5,
                edgecolor="#FC8181",
                facecolor="#FED7D7",
                alpha=0.35,
                zorder=1,
                picker=True,
            )
            self.ax.add_patch(rect)
            self._artist_info[rect] = f"zone | bl=({bl[0]:.2f}, {bl[1]:.2f}) tr=({tr[0]:.2f}, {tr[1]:.2f})"

    def _draw_modules(self) -> None:
        for module in self.board.modules:
            if not hasattr(module, "zone") or not module.zone:
                continue
            bl, _, tr, _ = module.zone
            rect = Rectangle(
                (bl[0], bl[1]),
                tr[0] - bl[0],
                tr[1] - bl[1],
                linewidth=1.5,
                edgecolor="#4299E1",
                facecolor="none",
                linestyle="--",
                zorder=2,
                picker=True,
            )
            self.ax.add_patch(rect)
            self._artist_info[rect] = f"module | name={module.name}"

    def _draw_buses(self) -> None:
        if not self.router.buses_layer:
            return
        for segment in self.router.buses_layer.segments:
            lc = LineCollection(
                [[segment.start.as_tuple(), segment.end.as_tuple()]],
                colors="#805AD5",
                linewidths=2.5,
                zorder=3,
                picker=5,
            )
            self.ax.add_collection(lc)
            self._artist_info[lc] = (
                f"bus | net={segment.net} | layer={segment.layer} | "
                f"start=({segment.start.x:.2f}, {segment.start.y:.2f}) "
                f"end=({segment.end.x:.2f}, {segment.end.y:.2f})"
            )

    def _draw_traces(self) -> None:
        if not self.router.paths_indices:
            return
        for net_name, paths in self.router.paths_indices.items():
            color = self._net_color(net_name)
            for path in paths:
                if len(path) < 2:
                    continue
                points = [self.router._indices_to_point(x, y).as_tuple() for x, y, _ in path]
                lc = LineCollection([points], colors=[color], linewidths=2, zorder=4, picker=5)
                self.ax.add_collection(lc)
                length = 0.0
                for i in range(1, len(points)):
                    x0, y0 = points[i - 1]
                    x1, y1 = points[i]
                    length += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                self._artist_info[lc] = f"trace | net={net_name} | points={len(points)} | length={length:.2f}mm"

    def _draw_vias(self) -> None:
        if not self.router.vias_indices:
            return
        for net_name, vias in self.router.vias_indices.items():
            color = self._net_color(net_name)
            for x, y in vias:
                point = self.router._indices_to_point(x, y)
                circle = Circle(point.as_tuple(), radius=0.15, color=color, alpha=0.8, zorder=5, picker=True)
                self.ax.add_patch(circle)
                self._artist_info[circle] = f"via | net={net_name} | x={point.x:.2f}, y={point.y:.2f}"

    def _draw_sockets(self) -> None:
        if not self.board.sockets:
            return
        
        # Track socket positions to detect duplicates
        seen_positions = {}
        for net_name, positions in self.board.sockets.socket_locations.items():
            for pos in positions:
                key = (net_name, tuple(pos))
                seen_positions[key] = seen_positions.get(key, 0) + 1
        
        for net_name, positions in self.board.sockets.socket_locations.items():
            color = self._net_color(net_name)
            if not positions:
                continue
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            
            # Check if any positions are duplicates
            has_duplicates = any(seen_positions.get((net_name, tuple(p)), 0) > 1 for p in positions)
            
            if has_duplicates:
                # Draw duplicates with red outline and larger
                scatter = self.ax.scatter(xs, ys, s=60, c=color, alpha=0.9, edgecolors='#E53E3E', linewidths=3, zorder=6, picker=True, marker='X')
            else:
                scatter = self.ax.scatter(xs, ys, s=20, c=color, alpha=0.8, zorder=6, picker=True)
            
            self._socket_meta[scatter] = {"net": net_name, "positions": positions}

    def _draw_grid(self, grid: np.ndarray) -> None:
        blocked = (grid == self.router.BLOCKED_CELL).astype(float)
        if not blocked.any():
            return

        resolution = self.board.resolution
        x_extent = self.router.grid_width / 2 * resolution
        y_extent = self.router.grid_height / 2 * resolution

        self.ax.imshow(
            blocked,
            cmap="Reds",
            origin="upper",
            alpha=0.25,
            extent=[-x_extent, x_extent, -y_extent, y_extent],
            zorder=0,
        )

    def _draw_candidate_path(self, path: List[Tuple[int, int, int]], net_name: Optional[str]) -> None:
        if len(path) < 2:
            return
        points = [self.router._indices_to_point(x, y).as_tuple() for x, y, _ in path]
        color = self._net_color(net_name or "")
        lc = LineCollection([points], colors=[color], linewidths=3.5, zorder=7, picker=5)
        self.ax.add_collection(lc)
        self._artist_info[lc] = f"candidate path | net={net_name or 'unknown'} | points={len(points)}"

    def _draw_socket_highlight(self, socket: Tuple[float, float]) -> None:
        circle = Circle((socket[0], socket[1]), radius=0.25, edgecolor="#D69E2E", facecolor="#FAF089", linewidth=2, zorder=8, picker=True)
        self.ax.add_patch(circle)
        self._artist_info[circle] = f"current socket | x={socket[0]:.2f}, y={socket[1]:.2f}"

    def _draw_bus_point(self, point: Point) -> None:
        circle = Circle(point.as_tuple(), radius=0.25, edgecolor="#805AD5", facecolor="#D6BCFA", linewidth=2, zorder=8, picker=True)
        self.ax.add_patch(circle)
        self._artist_info[circle] = f"bus connection | x={point.x:.2f}, y={point.y:.2f}"

    def _finalize_axes(self) -> None:
        padding = max(self.board.width, self.board.height) * 0.05
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.set_xlim(-self.board.width / 2 - padding, self.board.width / 2 + padding)
        self.ax.set_ylim(-self.board.height / 2 - padding, self.board.height / 2 + padding)
        self.ax.grid(True, alpha=0.1, linestyle="-", linewidth=0.5, color="#CBD5E0")
        self.ax.set_facecolor("#FFFFFF")

    def _init_panel(self) -> None:
        self.events_ax.set_axis_off()
        self.status_ax.set_axis_off()
        self.events_ax.set_facecolor("#F7FAFC")
        self.status_ax.set_facecolor("#F7FAFC")

    def _draw_panel(self, stage: str, net_name: Optional[str]) -> None:
        self.events_ax.set_axis_off()
        header = stage
        if net_name:
            header = f"{stage} | net={net_name}"

        if self._pending_events:
            items = "\n".join([f"• {msg}" for msg in self._pending_events])
        else:
            items = "(no events)"

        text = f"Events since last step\n{header}\n\n{items}"
        self.events_ax.text(
            0.0,
            1.0,
            text,
            ha="left",
            va="top",
            fontsize=9,
            color="#2D3748",
            wrap=True,
        )

        self._draw_status_list()

    def _draw_status_list(self) -> None:
        if not self._all_sockets:
            return

        self.status_ax.set_axis_off()

        max_items = 8
        line_h = 0.12

        total = len(self._all_sockets)
        done_count = len(self._done_sockets)
        header = f"Routing status ({done_count}/{total})"
        
        self.status_ax.text(
            0.0,
            1.0,
            header,
            ha="left",
            va="top",
            fontsize=9,
            fontweight="bold",
            color="#2D3748",
        )

        shown = self._all_sockets[:max_items]
        for idx, (net_name, pos) in enumerate(shown):
            done = (net_name, pos) in self._done_sockets
            color = "#38A169" if done else "#E53E3E"
            suffix = " ✓" if done else ""
            label = f"{net_name} ({pos[0]:.2f}, {pos[1]:.2f}){suffix}"
            y = 1.0 - (idx + 1) * line_h
            self.status_ax.text(
                0.0,
                y,
                label,
                ha="left",
                va="top",
                fontsize=8,
                color=color,
            )

        if len(self._all_sockets) > max_items:
            remaining = len(self._all_sockets) - max_items
            y = 1.0 - (max_items + 1) * line_h
            self.status_ax.text(
                0.0,
                y,
                f"… and {remaining} more",
                ha="left",
                va="top",
                fontsize=8,
                color="#7F8C8D",
            )

    def _set_info(self, text: str) -> None:
        self.info_text.set_text(text)
        self.fig.canvas.draw_idle()

    def _apply_theme(self) -> None:
        self.plt.rcParams.update(
            {
                "figure.facecolor": "#F5F7FA",
                "axes.facecolor": "#FFFFFF",
                "axes.edgecolor": "#CBD5E0",
                "axes.labelcolor": "#2D3748",
                "text.color": "#2D3748",
                "xtick.color": "#718096",
                "ytick.color": "#718096",
                "font.family": "sans-serif",
                "font.size": 9,
            }
        )

    def _net_color(self, net_name: str) -> str:
        if not net_name:
            return "#2D3748"
        palette = [
            "#319795",  # Teal
            "#38A169",  # Green
            "#3182CE",  # Blue
            "#805AD5",  # Purple
            "#DD6B20",  # Orange
            "#E53E3E",  # Red
            "#D69E2E",  # Yellow
            "#2D3748",  # Gray
        ]
        return palette[hash(net_name) % len(palette)]
