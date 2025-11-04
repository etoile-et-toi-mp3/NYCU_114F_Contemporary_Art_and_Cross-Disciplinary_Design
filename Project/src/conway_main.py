import pygame
import numpy as np
import signal, sys
import argparse
import cv2
import time
from conway_config import *
from conway_dataclass import *
from conway_utils import *

# signal handler for graceful exit
def graceful_shutdown(sig, frame):
    pygame.quit(); sys.exit(0)

def main():
    # register sighandler first
    signal.signal(signal.SIGINT, graceful_shutdown)

    # variables
    render = None
    params = None
    clock = pygame.time.Clock()
    working = 0
    fps = DRAWING_FPS

    # pygame setup
    pygame.init()
    pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONUP])
    pygame.display.set_caption("Conway's Game of Life")

    # parse args
    parser = argparse.ArgumentParser(description="Conway's Game of Life")
    parser.add_argument(
        '-f', '--fullscreen',
        action='store_true',
        help='Run in full-screen mode'
    )
    parser.add_argument(
        '-w', '--webcam',
        action='store_true',
        help='Use webcam as background'
    )
    args = parser.parse_args()

    if args.webcam:
        cap = cv2.VideoCapture(WEBCAM_INDEX)
        if not cap.isOpened():
            print("Error: Could not open webcam.")
            sys.exit(1)
            
        render = render_withcap
        params = Withcap_params()
    else:
        render = render_nocap
        params = Nocap_params()

    if args.fullscreen:
        # Get monitor's full resolution and create a fullscreen display
        info = pygame.display.Info()
        WIDTH_PX, HEIGHT_PX = info.current_w, info.current_h
        params.screen = pygame.display.set_mode((WIDTH_PX, HEIGHT_PX), pygame.FULLSCREEN)
        params.WIDTH = WIDTH_PX // PX_SIZE
        params.HEIGHT = HEIGHT_PX // PX_SIZE
    else:
        # Use fixed window size
        params.WIDTH = 100
        params.HEIGHT = 100
        params.screen = pygame.display.set_mode((params.WIDTH * PX_SIZE, params.HEIGHT * PX_SIZE))

    if args.webcam is False:
        params.screen.fill(BASE_COLOR)
    
    # initial render
    render(params)
    # main loop
    while True:
        # discrete events can be handled in this way
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                graceful_shutdown(None, None)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    graceful_shutdown(None, None)
                elif event.key == pygame.K_s:
                    working = 1; fps = WORKING_FPS
                elif event.key == pygame.K_p:
                    working = 0; fps = DRAWING_FPS
                elif working == 0:
                    # single-shot ops while paused, ofc can be handled here
                    if event.key == pygame.K_c:
                        params.live_cells.clear()
                        params.force_full_redraw = True
                    elif event.key == pygame.K_r:
                        params.live_cells.clear()
                        for x in range(params.WIDTH):
                            for y in range(params.HEIGHT):
                                if np.random.random() < 0.3:
                                    params.live_cells.add((x, y))
                        params.force_full_redraw = True

            if working == 0 and event.type == pygame.MOUSEBUTTONUP:
                pos = pygame.mouse.get_pos()
                gx = pos[0] // PX_SIZE
                gy = pos[1] // PX_SIZE
                if 0 <= gx < params.WIDTH and 0 <= gy < params.HEIGHT:
                    if (gx, gy) in params.live_cells:
                        params.live_cells.remove((gx, gy))
                    else:
                        params.live_cells.add((gx, gy))

        # continuous input handling
        if working == 0:
            key_pressed = pygame.key.get_pressed() # when continuous, we use this
            pos = pygame.mouse.get_pos()
            gx = pos[0] // PX_SIZE
            gy = pos[1] // PX_SIZE
            if 0 <= gx < params.WIDTH and 0 <= gy < params.HEIGHT:
                if key_pressed[pygame.K_e]:
                    params.live_cells.discard((gx, gy))  # Use discard() to avoid error if not in set
                elif key_pressed[pygame.K_w]:
                    params.live_cells.add((gx, gy))
                elif key_pressed[pygame.K_n]:
                    update(params)
                    time.sleep(0.08)  # TODO: find a smoother way to control speed
                render(params)
            
        if working == 1:
            update(params)
            render(params)

        pygame.display.update()
        clock.tick(fps)

if __name__ == "__main__":
    main()