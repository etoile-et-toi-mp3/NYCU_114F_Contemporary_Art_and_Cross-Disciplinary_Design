import pygame
from pygame import surfarray
import numpy as np
from collections import Counter
from conway_dataclass import *
import mediapipe as mp

def update(params):
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
    # We only need to check cells that have neighbors
    for cell, count in neighbor_counts.items():
        if ((cell in params.live_cells     and (count == 2 or count == 3)) or
            (cell not in params.live_cells and count == 3)):
            # color is the most voted among neighbors
            if cell in params.live_cells:
                next_generation.setdefault(cell, params.live_cells[cell])
            else:
                # New cell is born, choose color by majority vote
                if len(color_accumulator[cell]) > 0:
                    most_common_color = Counter(color_accumulator[cell]).most_common(1)[0][0]
                    next_generation.setdefault(cell, most_common_color)

    params.live_cells = next_generation

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
