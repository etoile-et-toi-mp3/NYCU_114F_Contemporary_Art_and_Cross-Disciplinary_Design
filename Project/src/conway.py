import pygame
import numpy as np
import signal, sys
from collections import Counter

def on_sigint(sig, frame):
    live_cells.clear()
    prev_live_cells.clear()
    pygame.quit(); sys.exit(0)
signal.signal(signal.SIGINT, on_sigint)

# game logic variables
clock = pygame.time.Clock()
working = 0

# view parameters
WIDTH = 100
HEIGHT = 100
live_cells = set()
prev_live_cells = set()
force_full_redraw = True  # Flag to force a full screen render, not partial

# UI parameters
WORKING_FPS = 15
DRAWING_FPS = 150
FPS = DRAWING_FPS
DEAD_COLOR = (50, 50, 50)
ALIVE_COLOR = (101, 243, 76)
BASE_COLOR = (90, 90, 90)
PX_SIZE = 10
WIDTH_PX = WIDTH * PX_SIZE
HEIGHT_PX = HEIGHT * PX_SIZE

# screen setup
pygame.init()
pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONUP])
screen = pygame.display.set_mode((WIDTH_PX, HEIGHT_PX))
pygame.display.set_caption("Conway's Game of Life")
screen.fill(BASE_COLOR)

# render: only redraw changed cells, or redraw all if forced
def render():
    global prev_live_cells, force_full_redraw

    if force_full_redraw:
        # Draw the entire viewport from scratch
        screen.fill(BASE_COLOR) # Background
        for x in range(WIDTH):
            for y in range(HEIGHT):
                rect = pygame.Rect(x*PX_SIZE, y*PX_SIZE, PX_SIZE-1, PX_SIZE-1)
                if (x, y) in live_cells:
                    pygame.draw.rect(screen, ALIVE_COLOR, rect)
                else:
                    pygame.draw.rect(screen, DEAD_COLOR, rect)
        force_full_redraw = False # only do this once
    else:
        # Optimized: Only draw cells that changed state
        cells_that_died = prev_live_cells - live_cells
        cells_that_were_born = live_cells - prev_live_cells
        cells_to_redraw = cells_that_died.union(cells_that_were_born)

        for (x, y) in cells_to_redraw:
            # Only draw if the cell is inside our viewport
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                rect = pygame.Rect(x*PX_SIZE, y*PX_SIZE, PX_SIZE-1, PX_SIZE-1)
                if (x, y) in live_cells: # Cell was born
                    pygame.draw.rect(screen, ALIVE_COLOR, rect)
                else: # Cell died
                    pygame.draw.rect(screen, DEAD_COLOR, rect)
    
    prev_live_cells = live_cells.copy() # Store state for next frame's diff

# logic updater now uses sparse sets (the "infinite" way)
def update():
    global live_cells, prev_live_cells
    
    # Count neighbors of all live cells
    neighbor_counts = Counter()
    for (x, y) in live_cells:
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
        if ((cell in live_cells     and (count == 2 or count == 3)) or
            (cell not in live_cells and count == 3)):
            next_generation.add(cell)

    live_cells = next_generation

# initial render
render()
# main loop
while True:
    # discrete events can be handled in this way
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            live_cells.clear()
            prev_live_cells.clear()
            pygame.quit(); sys.exit(0)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                live_cells.clear()
                prev_live_cells.clear()
                pygame.quit(); sys.exit(0)
            elif event.key == pygame.K_s:
                working = 1; FPS = WORKING_FPS
            elif event.key == pygame.K_p:
                working = 0; FPS = DRAWING_FPS
            elif working == 0:
                # single-shot ops while paused, ofc can be handled here
                if event.key == pygame.K_c:
                    live_cells.clear()
                    force_full_redraw = True
                elif event.key == pygame.K_r:
                    live_cells.clear()
                    for x in range(WIDTH):
                        for y in range(HEIGHT):
                            if np.random.random() < 0.3:
                                live_cells.add((x, y))
                    force_full_redraw = True

        if working == 0 and event.type == pygame.MOUSEBUTTONUP:
            pos = pygame.mouse.get_pos()
            gx = pos[0] // PX_SIZE
            gy = pos[1] // PX_SIZE
            if 0 <= gx < WIDTH and 0 <= gy < HEIGHT:
                if (gx, gy) in live_cells:
                    live_cells.remove((gx, gy))
                else:
                    live_cells.add((gx, gy))

    # continuous input handling
    if working == 0:
        key_pressed = pygame.key.get_pressed() # when continuous, we use this
        pos = pygame.mouse.get_pos()
        gx = pos[0] // PX_SIZE
        gy = pos[1] // PX_SIZE
        if 0 <= gx < WIDTH and 0 <= gy < HEIGHT:
            if key_pressed[pygame.K_e]:
                live_cells.discard((gx, gy))  # Use discard() to avoid error if not in set
            elif key_pressed[pygame.K_w]:
                live_cells.add((gx, gy))
            elif key_pressed[pygame.K_n]:
                update()
            render()
        
    if working == 1:
        update()
        render()

    pygame.display.update()
    clock.tick(FPS)
