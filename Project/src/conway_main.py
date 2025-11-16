import pygame
import numpy as np
import signal, sys
import argparse
import cv2
import time
import mediapipe as mp
from conway_config import *
from conway_dataclass import *
from conway_utils import *
from conway_motiondetector import HandController

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
    hand_controller = HandController()

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
        render = render_withcap
        params = Withcap_params()
        params.cap = cv2.VideoCapture(WEBCAM_INDEX)
        if not params.cap.isOpened():
            print("Error: Could not open webcam.")
            sys.exit(1)
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
        params.WIDTH = WIDTH
        params.HEIGHT = HEIGHT
        params.screen = pygame.display.set_mode((params.WIDTH * PX_SIZE, params.HEIGHT * PX_SIZE))

    if args.webcam is False:
        params.screen.fill(BASE_COLOR)
    else:
        params.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920) # from obs settings
        params.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        params.grid_surface = pygame.Surface((params.WIDTH*PX_SIZE, params.HEIGHT*PX_SIZE), pygame.SRCALPHA)
        for x in range(0, params.WIDTH):
            pygame.draw.line(params.grid_surface, params.BASE_COLOR, (x*PX_SIZE-1, 0), (x*PX_SIZE-1, params.HEIGHT * PX_SIZE))
        for y in range(0, params.HEIGHT):
            pygame.draw.line(params.grid_surface, params.BASE_COLOR, (0, y*PX_SIZE-1), (params.WIDTH * PX_SIZE, y*PX_SIZE-1))

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
                    params.working = True; fps = WORKING_FPS
                elif event.key == pygame.K_p:
                    params.working = False; fps = DRAWING_FPS
                elif not params.working:
                    # single-shot ops while paused, ofc can be handled here
                    if event.key == pygame.K_c:
                        params.live_cells.clear()
                        params.force_full_redraw = True
                    elif event.key == pygame.K_r:
                        params.live_cells.clear()
                        for x in range(params.WIDTH):
                            for y in range(params.HEIGHT):
                                if np.random.random() < 0.3:
                                    params.live_cells[(x, y)] = np.random.randint(len(params.ALIVE_COLOR))
                        params.force_full_redraw = True

        # hand input
        if isinstance(params, Withcap_params):
            ret, frame = params.cap.read()
            if ret is not True:
                print("Error: Could not read frame from webcam.")
                sys.exit(1)
            # Process frame
            frame = cv2.flip(frame, 1) # Mirror image for more natural interaction
            frame = hand_controller.process(frame, params)
            params.frame_with_lm_drawn = cv2.flip(frame, 1) # Store mirrored frame for rendering
            if WORKING_DRAWABLE or not params.working:
                # Apply Drawing/Erasing from Cursor
                cx, cy = params.cursor_pos
                if cx != -1 and cy != -1:
                    gx = cx // PX_SIZE
                    gy = cy // PX_SIZE
                    
                    for dy in range(-params.cursor_size, params.cursor_size + 1):
                        for dx in range(-params.cursor_size, params.cursor_size + 1):
                            if dx*dx + dy*dy <= params.cursor_size*params.cursor_size:
                                
                                # Calculate the actual grid coordinate
                                nx = gx + dx
                                ny = gy + dy
                                
                                # CRITICAL: Check boundaries so we don't crash at the screen edge
                                if 0 <= nx < params.WIDTH and 0 <= ny < params.HEIGHT:
                                    if params.hand_drawing:
                                        params.live_cells.setdefault((nx, ny), np.random.randint(len(params.ALIVE_COLOR)))
                                    elif params.hand_erasing:
                                        params.live_cells.pop((nx, ny), None)

        if WORKING_DRAWABLE or not params.working:
            key_pressed = pygame.key.get_pressed() # when continuous, we use this
            pos = pygame.mouse.get_pos()
            gx = pos[0] // PX_SIZE
            gy = pos[1] // PX_SIZE
            if 0 <= gx < params.WIDTH and 0 <= gy < params.HEIGHT:
                if key_pressed[pygame.K_e]:
                    params.live_cells.pop((gx, gy), None)  # Use pop() to avoid error if not in dict
                elif key_pressed[pygame.K_w]:
                    params.live_cells[(gx, gy)] = np.random.randint(len(params.ALIVE_COLOR))

        if not params.working:
            if key_pressed[pygame.K_n]:
                update(params)
                time.sleep(0.08)  # TODO: find a smoother way to control speed
        else:
            update(params)
            
        render(params)
        pygame.display.update()
        clock.tick(fps)

if __name__ == "__main__":
    main()