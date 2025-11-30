import pygame
from pygame import surfarray
import numpy as np
from collections import Counter
from conway_dataclass import *
import mediapipe as mp
import os
import psutil
from conway_sound import process_sound

# --- INIT UI RESOURCES ONCE ---
# We initialize these at the module level so we don't reload fonts every frame
pygame.font.init()
# "Consolas" or "Courier New" are good because they are monospaced (numbers line up)
try:
    FONT_MAIN = pygame.font.SysFont("Consolas", 18, bold=True)
    FONT_SMALL = pygame.font.SysFont("Consolas", 14)
except:
    FONT_MAIN = pygame.font.SysFont("Arial", 18, bold=True)
    FONT_SMALL = pygame.font.SysFont("Arial", 14)

PROCESS = psutil.Process(os.getpid())

def update(params):
    params.sound_posedge.clear()
    
    # Count neighbors of all live cells
    neighbor_counts = Counter()
    # collect the colors indexes of a cell's neighbors, to decide color of born cells
    color_accumulator = {tuple: list()}
    
    for (x, y) in params.live_cells:
        # Iterate over all 8 neighbors and broadcast my existence
        for i in range(x - 1, x + 2):
            for j in range(y - 1, y + 2):
                if (i, j) == (x, y):
                    continue  # Don't count the cell itself
                neighbor_counts[(i, j)] += 1
                # accumulate color indexes
                color_accumulator.setdefault((i, j), [])
                color_accumulator[(i, j)].append(params.live_cells[(x, y)])                

    # Apply rules of life
    next_generation = dict()
    # We only need to check cells that have alive neighbors
    for cell, count in neighbor_counts.items():
        if ((cell in params.live_cells     and (count == 2 or count == 3)) or
            (cell not in params.live_cells and count == 3)):
            if cell in params.live_cells:
                # Cell survives, keep its color
                next_generation.setdefault(cell, params.live_cells[cell])
            else:
                # New cell is born, choose color by majority vote
                most_common_color = Counter(color_accumulator[cell]).most_common(1)[0][0]
                next_generation.setdefault(cell, most_common_color)
                if (params.cursor_pos[0]/params.PX_SIZE - (params.cursor_size+1) // 2 <= cell[0] < params.cursor_pos[0]/params.PX_SIZE + (params.cursor_size+1) // 2 
                and params.cursor_pos[1]/params.PX_SIZE - (params.cursor_size+1) // 2 <= cell[1] < params.cursor_pos[1]/params.PX_SIZE + (params.cursor_size+1) // 2):
                    params.sound_posedge.add(cell)  # Mark this cell as newly born for sound processing, we only care about births inside the viewport

    params.live_cells = next_generation
    process_sound(params)

def render_nocap(params: Nocap_params):
    if params.force_full_redraw:
        # Draw the entire viewport from scratch
        params.screen.fill(params.BASE_COLOR) # Background
        for x in range(params.WIDTH):
            for y in range(params.HEIGHT):
                rect = pygame.Rect(x*params.PX_SIZE, y*params.PX_SIZE, params.PX_SIZE-1, params.PX_SIZE-1)
                # if xy is a key in live_cells, draw ALIVE_COLOR else DEAD_COLOR
                if (x, y) in params.live_cells:
                    pygame.draw.rect(params.screen, params.ALIVE_COLOR[params.live_cells[(x, y)]], rect)
                else:
                    pygame.draw.rect(params.screen, params.DEAD_COLOR, rect)
        params.force_full_redraw = False # only do this once
    else:
        # Optimized: Only draw cells that changed state
        
        cells_that_died = set(params.prev_live_cells) - set(params.live_cells)
        cells_that_were_born = set(params.live_cells) - set(params.prev_live_cells)
        cells_to_redraw = cells_that_died.union(cells_that_were_born)

        for (x, y) in cells_to_redraw:
            # Only draw if the cell is inside our viewport
            if 0 <= x < params.WIDTH and 0 <= y < params.HEIGHT:
                rect = pygame.Rect(x*params.PX_SIZE, y*params.PX_SIZE, params.PX_SIZE-1, params.PX_SIZE-1)
                if (x, y) in params.live_cells: # Cell was born
                    pygame.draw.rect(params.screen, params.ALIVE_COLOR[params.live_cells[(x, y)]], rect)
                else: # Cell died
                    pygame.draw.rect(params.screen, params.DEAD_COLOR, rect)

    params.prev_live_cells = params.live_cells.copy() # Store state for next frame's diff

def render_withcap(params: Withcap_params):
    # Safety Check: Make sure a frame actually exists
    if params.frame_with_lm_drawn is None:
        return

    # 1. --- Get Dimensions from params.current_frame ---
    frame = params.frame_with_lm_drawn
    img_height, img_width = frame.shape[0], frame.shape[1]
    screen_width, screen_height = params.screen.get_size()

    # 2. --- Compare Aspect Ratios (Same as before) ---
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

    # 3. --- Convert for Pygame ---
    # Remember: params.current_frame is BGR (OpenCV standard)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # ROTATE 90 degrees for Pygame
    frame_rgb = np.rot90(frame_rgb) 
    
    wbcm = surfarray.make_surface(frame_rgb)
    webcam_surface = pygame.transform.smoothscale(wbcm, (scaled_width, scaled_height))

    # 4. --- Blit ---
    params.screen.blit(webcam_surface, (blit_x, blit_y))
    if params.grid_surface:
        params.screen.blit(params.grid_surface, (0, 0))

    # Draw only live cells
    for (x, y) in params.live_cells:
        if 0 <= x < params.WIDTH and 0 <= y < params.HEIGHT:
            rect = pygame.Rect(x*params.PX_SIZE, y*params.PX_SIZE, params.PX_SIZE-1, params.PX_SIZE-1)
            pygame.draw.rect(params.screen, params.ALIVE_COLOR[params.live_cells[(x, y)]], rect)
    
    # draw hand cursor
    cx, cy = params.cursor_pos
    if cx != -1 and cy != -1:
        cursor_color = (0, 0, 255) # Blue
        if params.hand_drawing:
            cursor_color = (0, 255, 0) # Green
        elif params.hand_erasing:
            cursor_color = (255, 0, 0) # Red
            
        # --- NEW: Dynamic Cursor Size ---
        # Calculate pixel radius: (Grid Radius * Pixel Size) + (Half a cell for centering)
        visual_radius = (params.cursor_size * params.PX_SIZE) + (params.PX_SIZE // 2)
        
        # Draw the main circle
        pygame.draw.circle(params.screen, cursor_color, (cx, cy), visual_radius, 2) # Thickness 2 looks nice
        
        # Optional: Draw a tiny dot in the exact center for precision
        pygame.draw.circle(params.screen, cursor_color, (cx, cy), 3)

def draw_hud(params, fps: float):
    screen = params.screen
    
    # 1. --- DATA COLLECTION ---
    # Memory: RSS (Resident Set Size) is the non-swapped physical memory a process has used
    mem_info = PROCESS.memory_info()
    mem_usage_mb = mem_info.rss / 1024 / 1024 
    
    num_cells = len(params.live_cells)
    
    # 2. --- DEFINE TEXT LINES ---
    # List of (Text, Color) tuples
    lines = []
    
    # > FPS & MEMORY
    lines.append((f"FPS: {int(fps)}  |  RAM: {mem_usage_mb:.1f} MB", (200, 200, 200)))
    
    # > CELL COUNT
    lines.append((f"Cells: {num_cells}", (200, 200, 200)))
    
    # > GAME STATE (Running/Paused)
    if params.working:
        state_text = "STATE: RUNNING"
        state_color = (0, 255, 0) # Green
    else:
        state_text = "STATE: PAUSED"
        state_color = (255, 50, 50) # Red
    lines.append((state_text, state_color))
    
    # > CURSOR INFO
    if isinstance(params, Withcap_params):
        cursor_text = f"Cursor Size: {params.cursor_size}"
        lines.append((cursor_text, (255, 255, 0))) # Yellow
    
        # > HAND ACTION
        if params.hand_drawing:
            action = "[ DRAWING ]"
            action_color = (0, 255, 0)
        elif params.hand_erasing:
            action = "[ ERASING ]"
            action_color = (255, 0, 0)
        else:
            action = "[ HOVERING ]"
            action_color = (200, 200, 200)
        lines.append((action, action_color))

    # 3. --- DRAW BACKGROUND PANEL ---
    # We draw a semi-transparent black box so text is readable over the webcam
    # Box height depends on number of lines
    panel_width = 280
    panel_height = 10 + (len(lines) * 20)
    
    # Create a transparent surface
    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 180)) # Black with alpha=180
    
    # Draw a border
    pygame.draw.rect(panel, (100, 100, 100), panel.get_rect(), 1)
    
    # Blit panel to top-left of screen
    screen.blit(panel, (10, 10))

    # 4. --- DRAW TEXT ---
    x_offset = 20
    y_offset = 15
    
    for text_str, color in lines:
        text_surf = FONT_MAIN.render(text_str, True, color)
        screen.blit(text_surf, (x_offset, y_offset))
        y_offset += 20 # Move down for next line

    # 5. --- OPTIONAL: BOTTOM HELP BAR ---
    # A small strip at the bottom explaining controls
    help_text = "L-Hand: Pinch Index(Draw) Middle(Erase) Ring(Rnd) Pinky(Clr) | R-Hand: Pinch to Resize"
    help_surf = FONT_SMALL.render(help_text, True, (200, 200, 200))
    
    # Draw bottom background strip
    bottom_strip = pygame.Surface((params.WIDTH * params.PX_SIZE, 25), pygame.SRCALPHA)
    bottom_strip.fill((0, 0, 0, 150))
    screen.blit(bottom_strip, (0, params.HEIGHT * params.PX_SIZE - 25))
    
    # Center the help text
    screen_w = params.WIDTH * params.PX_SIZE
    text_w = help_surf.get_width()
    screen.blit(help_surf, ((screen_w - text_w) // 2, params.HEIGHT * params.PX_SIZE - 22))
