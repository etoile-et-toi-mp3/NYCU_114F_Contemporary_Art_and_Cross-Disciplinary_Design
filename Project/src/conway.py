import pygame
import numpy as np
import signal, sys

def on_sigint(sig, frame):
    pygame.quit(); sys.exit(0)
signal.signal(signal.SIGINT, on_sigint)

# game logic variables
clock = pygame.time.Clock()
working = 0
gameover = 0

# grid parameters
WIDTH = 200
HEIGHT = 200
grid = np.zeros((WIDTH, HEIGHT), dtype=np.uint8)     # 0 = dead, 1 = alive
prev_grid = np.full((WIDTH, HEIGHT),  1, dtype=np.int8)  # force full redraw initially

# UI parameters
WORKING_FPS = 15
DRAWING_FPS = 150
FPS = DRAWING_FPS
DEAD_COLOR = (50, 50, 50)
ALIVE_COLOR = (101, 243, 76)
PX_SIZE = 7
WIDTH_PX = WIDTH * PX_SIZE
HEIGHT_PX = HEIGHT * PX_SIZE

# screen setup
pygame.init()
pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONUP])
screen = pygame.display.set_mode((WIDTH_PX, HEIGHT_PX))
pygame.display.set_caption("Conway's Game of Life")
screen.fill((90, 90, 90))

def neighbor_counts_roll(g: np.ndarray) -> np.ndarray:  # g is uint8 or bool
    return (
        np.roll(g,  1, 0) + np.roll(g, -1, 0) +
        np.roll(g,  1, 1) + np.roll(g, -1, 1) +
        np.roll(np.roll(g,  1, 0),  1, 1) +
        np.roll(np.roll(g,  1, 0), -1, 1) +
        np.roll(np.roll(g, -1, 0),  1, 1) +
        np.roll(np.roll(g, -1, 0), -1, 1)
    ).astype(np.uint8)

# render: only redraw changed cells
def render():
    global prev_grid
    diff = (grid != prev_grid)
    
    for x in range(WIDTH):
        gx = grid[x]
        for y in range(HEIGHT):
            if diff[x, y]:
                rect = pygame.Rect(x*PX_SIZE, y*PX_SIZE, PX_SIZE-1, PX_SIZE-1)
                if gx[y] == 0:
                    pygame.draw.rect(screen, DEAD_COLOR, rect)
                else:
                    pygame.draw.rect(screen, ALIVE_COLOR, rect)
    prev_grid = grid.copy() # we won't copy until here!


# logic updater (now vectorized with convolution)
def update():
    neigh = neighbor_counts_roll(grid)
    next_alive = (neigh == 3) | ((grid == 1) & (neigh == 2))
    grid[:] = np.where(next_alive, 1, 0).astype(np.int8)

# main loop
while True:
    key_pressed = pygame.key.get_pressed()
    if key_pressed[pygame.K_s]:
        working = 1
        FPS = WORKING_FPS
    elif key_pressed[pygame.K_p]:
        working = 0
        FPS = DRAWING_FPS
    elif key_pressed[pygame.K_q]:
        break

    # detect events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameover = 1
            break

        if working == 0:
            pos = pygame.mouse.get_pos()
            gx = pos[0] // PX_SIZE
            gy = pos[1] // PX_SIZE
            if 0 <= gx < WIDTH and 0 <= gy < HEIGHT:
                if event.type == pygame.MOUSEBUTTONUP:
                    grid[gx, gy] ^= 1
                elif key_pressed[pygame.K_e]:
                    grid[gx, gy] = 0
                elif key_pressed[pygame.K_w]:
                    grid[gx, gy] = 1
                elif key_pressed[pygame.K_c]:
                    grid[:] = 0
                    prev_grid[:] = 1
                elif key_pressed[pygame.K_r]:
                    grid[:] = np.random.choice([0, 1], size=(WIDTH, HEIGHT), p=[0.7, 0.3])
                    prev_grid = 1 - grid
                elif key_pressed[pygame.K_n]:
                    update()
            render()
            
    if gameover:
        break

    if working == 1:
        update()
        render()

    pygame.display.update()
    clock.tick(FPS)

pygame.quit()
