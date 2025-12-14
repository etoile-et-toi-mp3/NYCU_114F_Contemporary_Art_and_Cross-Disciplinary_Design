import pygame
from pygame import surfarray
import numpy as np
from collections import Counter
from conway_dataclass import *
import mediapipe as mp
import os
import psutil
from conway_sound import process_sound

# --- INIT UI RESOURCES ---
pygame.font.init()
try:
    FONT_MAIN = pygame.font.SysFont("Consolas", 18, bold=True)
    FONT_SMALL = pygame.font.SysFont("Consolas", 14)
except:
    FONT_MAIN = pygame.font.SysFont("Arial", 18, bold=True)
    FONT_SMALL = pygame.font.SysFont("Arial", 14)

PROCESS = psutil.Process(os.getpid())


def update_game_logic(params):
    """
    Only handles the Game of Life simulation (Births/Deaths/Stability).
    Does NOT handle sound.
    """
    neighbor_counts = Counter()
    color_accumulator = {tuple: list()}

    # 1. Count Neighbors
    for x, y in params.live_cells:
        for i in range(x - 1, x + 2):
            for j in range(y - 1, y + 2):
                if (i, j) == (x, y):
                    continue
                neighbor_counts[(i, j)] += 1
                color_accumulator.setdefault((i, j), [])
                color_accumulator[(i, j)].append(params.live_cells[(x, y)])

    next_generation = dict()
    next_stability = dict()

    # 2. Apply Rules
    for cell, count in neighbor_counts.items():
        if (cell in params.live_cells and (count == 2 or count == 3)) or (
            cell not in params.live_cells and count == 3
        ):
            if cell in params.live_cells:
                # SURVIVOR -> STABLE
                next_generation[cell] = params.live_cells[cell]
                next_stability[cell] = params.cell_stability.get(cell, 0) + 1 # current stability + 1
            else:
                # NEWBORN -> CHAOS
                most_common_color = Counter(color_accumulator[cell]).most_common(1)[0][0]
                next_generation[cell] = most_common_color
                next_stability[cell] = 0

    # 3. Apply Update
    params.live_cells = next_generation
    params.cell_stability = next_stability

def update_sound_probe(params):
    """
    Checks the cursor position and sends sound to VCV Rack.
    """
    # 1. Clear previous sound buffer
    params.sound_posedge.clear()

    # 2. Probe the Cursor Area
    # --- CHANGE: Added "and params.working" to this check ---
    # Now, if the game is PAUSED, this block is skipped. 
    # The list stays empty, and process_sound kills the volume.
    if params.working and isinstance(params, Withcap_params) and params.cursor_pos != (-1, -1):
        gx = params.cursor_pos[0] // params.PX_SIZE
        gy = params.cursor_pos[1] // params.PX_SIZE
        r = params.cursor_size
        r_sq = r * r
        
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx*dx + dy*dy <= r_sq:
                    nx = gx + dx
                    ny = gy + dy
                    
                    if (nx, ny) in params.live_cells:
                        params.sound_posedge.add((nx, ny))

    # 3. Process Sound
    # If paused, sound_posedge is empty -> Sends Gate 0 -> Silence.
    process_sound(params)


def render_nocap(params: Nocap_params):
    # ... (Same as before) ...
    if params.force_full_redraw:
        params.screen.fill(params.BASE_COLOR)
        for x in range(params.WIDTH):
            for y in range(params.HEIGHT):
                rect = pygame.Rect(x * params.PX_SIZE, y * params.PX_SIZE, params.PX_SIZE - 1, params.PX_SIZE - 1)
                if (x, y) in params.live_cells:
                    pygame.draw.rect(params.screen, params.ALIVE_COLOR[params.live_cells[(x, y)]], rect)
                else:
                    pygame.draw.rect(params.screen, params.DEAD_COLOR, rect)
        params.force_full_redraw = False
    else:
        cells_that_died = set(params.prev_live_cells) - set(params.live_cells)
        cells_that_were_born = set(params.live_cells) - set(params.prev_live_cells)
        cells_to_redraw = cells_that_died.union(cells_that_were_born)

        for x, y in cells_to_redraw:
            if 0 <= x < params.WIDTH and 0 <= y < params.HEIGHT:
                rect = pygame.Rect(x * params.PX_SIZE, y * params.PX_SIZE, params.PX_SIZE - 1, params.PX_SIZE - 1)
                if (x, y) in params.live_cells:
                    pygame.draw.rect(params.screen, params.ALIVE_COLOR[params.live_cells[(x, y)]], rect)
                else:
                    pygame.draw.rect(params.screen, params.DEAD_COLOR, rect)

    params.prev_live_cells = params.live_cells.copy()


def render_withcap(params: Withcap_params):
    # ... (Same as before) ...
    if params.frame_with_lm_drawn is None:
        return

    frame = params.frame_with_lm_drawn
    img_height, img_width = frame.shape[0], frame.shape[1]
    screen_width, screen_height = params.screen.get_size()

    img_aspect = img_width / img_height
    screen_aspect = screen_width / screen_height

    if img_aspect > screen_aspect:
        scale_factor = screen_height / img_height
        scaled_width = int(img_width * scale_factor)
        scaled_height = screen_height
        blit_x = (screen_width - scaled_width) // 2
        blit_y = 0
    else:
        scale_factor = screen_width / img_width
        scaled_width = screen_width
        scaled_height = int(img_height * scale_factor)
        blit_x = 0
        blit_y = (screen_height - scaled_height) // 2

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_rgb = np.transpose(frame_rgb, (1, 0, 2))

    wbcm = surfarray.make_surface(frame_rgb)
    webcam_surface = pygame.transform.smoothscale(wbcm, (scaled_width, scaled_height))

    # 4. Blit Webcam
    params.screen.blit(webcam_surface, (blit_x, blit_y))

    # --- NEW: DIMMER LAYER ---
    # Create a black surface with Alpha (Transparency)
    # 0 = Invisible, 255 = Pitch Black. 
    # 150 is a good "Sunglass" effect.
    dim_surface = pygame.Surface(params.screen.get_size(), pygame.SRCALPHA)
    dim_surface.fill((0, 0, 0, 150)) 
    params.screen.blit(dim_surface, (0, 0))
    # -------------------------

    # 5. Draw Grid (Optional, if you want it on top of the dimmer)
    if params.grid_surface:
        params.screen.blit(params.grid_surface, (0, 0))

    for x, y in params.live_cells:
        if 0 <= x < params.WIDTH and 0 <= y < params.HEIGHT:
            rect = pygame.Rect(x * params.PX_SIZE, y * params.PX_SIZE, params.PX_SIZE - 1, params.PX_SIZE - 1)
            pygame.draw.rect(params.screen, params.ALIVE_COLOR[params.live_cells[(x, y)]], rect)

    cx, cy = params.cursor_pos
    if cx != -1 and cy != -1:
        cursor_color = (0, 0, 255)
        if params.hand_drawing:
            cursor_color = (0, 255, 0)
        elif params.hand_erasing:
            cursor_color = (255, 0, 0)

        visual_radius = (params.cursor_size * params.PX_SIZE) + (params.PX_SIZE // 2)
        pygame.draw.circle(params.screen, cursor_color, (cx, cy), visual_radius, 2)
        pygame.draw.circle(params.screen, cursor_color, (cx, cy), 3)


def draw_hud(params, fps: float):
    # ... (Same as before) ...
    screen = params.screen
    mem_info = PROCESS.memory_info()
    mem_usage_mb = mem_info.rss / 1024 / 1024
    num_cells = len(params.live_cells)

    lines = []
    lines.append((f"FPS: {int(fps)} | RAM: {mem_usage_mb:.1f} MB", (200, 200, 200)))
    lines.append((f"Cells: {num_cells}", (200, 200, 200)))

    if params.working:
        lines.append(("STATE: RUNNING", (0, 255, 0)))
    else:
        lines.append(("STATE: PAUSED", (255, 50, 50)))

    if isinstance(params, Withcap_params):
        lines.append((f"Cursor Size: {params.cursor_size}", (255, 255, 0)))
        if params.hand_drawing:
            lines.append(("[ DRAWING ]", (0, 255, 0)))
        elif params.hand_erasing:
            lines.append(("[ ERASING ]", (255, 0, 0)))
        else:
            lines.append(("[ HOVERING ]", (200, 200, 200)))

    panel_width = 280
    panel_height = 10 + (len(lines) * 20)
    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 180))
    pygame.draw.rect(panel, (100, 100, 100), panel.get_rect(), 1)
    screen.blit(panel, (10, 10))

    x_offset = 20; y_offset = 15
    for text_str, color in lines:
        text_surf = FONT_MAIN.render(text_str, True, color)
        screen.blit(text_surf, (x_offset, y_offset))
        y_offset += 20

    help_text = "L-Hand: Pinch Index(Draw) Middle(Erase) Ring(Rnd) Pinky(Clr) | R-Hand: Pinch to Resize"
    help_surf = FONT_SMALL.render(help_text, True, (200, 200, 200))
    bottom_strip = pygame.Surface((params.WIDTH * params.PX_SIZE, 25), pygame.SRCALPHA)
    bottom_strip.fill((0, 0, 0, 150))
    screen.blit(bottom_strip, (0, params.HEIGHT * params.PX_SIZE - 25))
    
    screen_w = params.WIDTH * params.PX_SIZE
    text_w = help_surf.get_width()
    screen.blit(help_surf, ((screen_w - text_w) // 2, params.HEIGHT * params.PX_SIZE - 22))
