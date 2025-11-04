import pygame
from pygame import surfarray
import numpy as np
from collections import Counter
from conway_dataclass import *

def update(params):
    # Count neighbors of all live cells
    neighbor_counts = Counter()
    for (x, y) in params.live_cells:
        # Iterate over all 8 neighbors and increment their count
        for i in range(x - 1, x + 2):
            for j in range(y - 1, y + 2):
                if (i, j) == (x, y):
                    continue  # Don't count the cell itself
                neighbor_counts[(i, j)] += 1

    # Apply rules of life
    next_generation = set()
    # We only need to check cells that have neighbors
    for cell, count in neighbor_counts.items():
        if ((cell in params.live_cells     and (count == 2 or count == 3)) or
            (cell not in params.live_cells and count == 3)):
            next_generation.add(cell)

    params.live_cells = next_generation

def render_nocap(params: Nocap_params):
    if params.force_full_redraw:
        # Draw the entire viewport from scratch
        params.screen.fill(params.BASE_COLOR) # Background
        for x in range(params.WIDTH):
            for y in range(params.HEIGHT):
                rect = pygame.Rect(x*params.PX_SIZE, y*params.PX_SIZE, params.PX_SIZE-1, params.PX_SIZE-1)
                if (x, y) in params.live_cells:
                    pygame.draw.rect(params.screen, params.ALIVE_COLOR, rect)
                else:
                    pygame.draw.rect(params.screen, params.DEAD_COLOR, rect)
        params.force_full_redraw = False # only do this once
    else:
        # Optimized: Only draw cells that changed state
        cells_that_died = params.prev_live_cells - params.live_cells
        cells_that_were_born = params.live_cells - params.prev_live_cells
        cells_to_redraw = cells_that_died.union(cells_that_were_born)

        for (x, y) in cells_to_redraw:
            # Only draw if the cell is inside our viewport
            if 0 <= x < params.WIDTH and 0 <= y < params.HEIGHT:
                rect = pygame.Rect(x*params.PX_SIZE, y*params.PX_SIZE, params.PX_SIZE-1, params.PX_SIZE-1)
                if (x, y) in params.live_cells: # Cell was born
                    pygame.draw.rect(params.screen, params.ALIVE_COLOR, rect)
                else: # Cell died
                    pygame.draw.rect(params.screen, params.DEAD_COLOR, rect)

    params.prev_live_cells = params.live_cells.copy() # Store state for next frame's diff

def render_withcap(params: Withcap_params):
    ret, frame = params.cap.read()
    if not ret:
        print("Error: Webcam frame could not be read.")
        raise RuntimeError("Webcam frame read failure")
    else:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = cv2.flip(frame, 0)
        
        webcam_surface = surfarray.make_surface(frame)
        webcam_surface = pygame.transform.scale(webcam_surface, (params.WIDTH * PX_SIZE, params.HEIGHT * PX_SIZE))
        
        params.screen.blit(webcam_surface, (0, 0))

    # Draw only live cells
    for (x, y) in params.live_cells:
        if 0 <= x < params.WIDTH and 0 <= y < params.HEIGHT:
            rect = pygame.Rect(x*PX_SIZE, y*PX_SIZE, PX_SIZE-1, PX_SIZE-1)
            pygame.draw.rect(params.screen, params.ALIVE_COLOR, rect)
