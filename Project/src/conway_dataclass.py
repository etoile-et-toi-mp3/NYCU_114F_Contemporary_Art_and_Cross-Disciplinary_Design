import pygame
import cv2
from dataclasses import dataclass, field
from conway_config import *
import numpy as np
from typing import Any

ALIVE_COLOR_DEFAULT = ALIVE_COLOR

@dataclass
class Nocap_params:
    screen: pygame.Surface = field(default=None)
    live_cells: dict[tuple, int] = field(default_factory=dict) # (x, y) -> color_index
    prev_live_cells: dict[tuple, int] = field(default_factory=dict)
    force_full_redraw: bool = True
    BASE_COLOR: tuple = BASE_COLOR
    ALIVE_COLOR: list[tuple] = field(default_factory=lambda: ALIVE_COLOR_DEFAULT.copy())
    DEAD_COLOR: tuple = DEAD_COLOR
    WIDTH: int = WIDTH
    HEIGHT: int = HEIGHT
    PX_SIZE: int = PX_SIZE
    working: bool = False
    osc_client: Any = None

@dataclass
class Withcap_params:
    screen: pygame.Surface = field(default=None)
    cap: cv2.VideoCapture = field(default=None)
    live_cells: dict[tuple, int] = field(default_factory=dict) # (x, y) -> color_index
    ALIVE_COLOR: list[tuple] = field(default_factory=lambda: ALIVE_COLOR_DEFAULT.copy())
    BASE_COLOR: tuple = BASE_COLOR
    WIDTH: int = WIDTH
    HEIGHT: int = HEIGHT
    PX_SIZE: int = PX_SIZE
    grid_surface: pygame.Surface = field(default=None)
    working: bool = False

    cursor_pos: tuple = (-1, -1)
    cursor_size: int = 1
    hand_drawing: bool = False
    hand_erasing: bool = False
    frame_with_lm_drawn: np.ndarray = None

    # Debounce flags (to prevent rapid-fire toggling)
    last_toggle_time: int = 0
    last_random_time: int = 0
    last_clear_time: int = 0

    osc_client: Any = None
    cell_stability: dict[tuple, int] = field(default_factory=dict)
    sound_posedge: set = field(default_factory=set)
