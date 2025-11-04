import pygame
import cv2
from dataclasses import dataclass, field
from conway_config import *

@dataclass
class Nocap_params:
    screen: pygame.Surface = field(default=None)
    live_cells: set = field(default_factory=set)
    prev_live_cells: set = field(default_factory=set)
    force_full_redraw: bool = True
    BASE_COLOR: tuple = BASE_COLOR
    ALIVE_COLOR: tuple = ALIVE_COLOR
    DEAD_COLOR: tuple = DEAD_COLOR
    WIDTH: int = 100
    HEIGHT: int = 100
    PX_SIZE: int = PX_SIZE

@dataclass
class Withcap_params:
    screen: pygame.Surface = field(default=None)
    cap: cv2.VideoCapture = field(default=None)
    live_cells: set = field(default_factory=set)
    ALIVE_COLOR: tuple = ALIVE_COLOR
    WIDTH: int = 100
    HEIGHT: int = 100
    PX_SIZE: int = PX_SIZE
