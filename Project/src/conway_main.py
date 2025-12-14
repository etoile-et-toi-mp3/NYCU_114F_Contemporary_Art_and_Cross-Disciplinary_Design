import pygame
import numpy as np
import signal, sys
import argparse
import cv2
import time
import mediapipe as mp
from pythonosc import udp_client
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
    fps = DRAWING_FPS
    hand_controller = HandController()

    # pygame setup
    pygame.init()
    pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONUP])
    pygame.display.set_caption("Conway's Game of Life")

    # parse args
    parser = argparse.ArgumentParser(description="Conway's Game of Life")
    parser.add_argument('-f', '--fullscreen', action='store_true', help='Run in full-screen mode')
    parser.add_argument('-w', '--webcam', action='store_true', help='Use webcam as background')
    args = parser.parse_args()

    if args.webcam:
        render = render_withcap
        params = Withcap_params()
        # NOTE: Ensure WEBCAM_INDEX matches your OBS Virtual Camera index
        params.cap = cv2.VideoCapture(WEBCAM_INDEX)
        if not params.cap.isOpened():
            print("Error: Could not open webcam.")
            sys.exit(1)
    else:
        render = render_nocap
        params = Nocap_params()

    if args.fullscreen:
        info = pygame.display.Info()
        WIDTH_PX, HEIGHT_PX = info.current_w, info.current_h
        params.screen = pygame.display.set_mode((WIDTH_PX, HEIGHT_PX), pygame.FULLSCREEN)
        params.WIDTH = WIDTH_PX // PX_SIZE
        params.HEIGHT = HEIGHT_PX // PX_SIZE
    else:
        params.WIDTH = WIDTH
        params.HEIGHT = HEIGHT
        params.screen = pygame.display.set_mode((params.WIDTH * PX_SIZE, params.HEIGHT * PX_SIZE))

    if args.webcam is False:
        params.screen.fill(BASE_COLOR)
    else:
        # Request HD resolution from OBS/Camera
        params.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        params.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        # Create Grid
        params.grid_surface = pygame.Surface((params.WIDTH*PX_SIZE, params.HEIGHT*PX_SIZE), pygame.SRCALPHA)
        # Use a slightly transparent color for grid lines
        grid_color = (params.BASE_COLOR[0], params.BASE_COLOR[1], params.BASE_COLOR[2], 100) 
        for x in range(0, params.WIDTH):
            pygame.draw.line(params.grid_surface, grid_color, (x*PX_SIZE, 0), (x*PX_SIZE, params.HEIGHT * PX_SIZE))
        for y in range(0, params.HEIGHT):
            pygame.draw.line(params.grid_surface, grid_color, (0, y*PX_SIZE), (params.WIDTH * PX_SIZE, y*PX_SIZE))

    client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)
    params.osc_client = client
    
    # main loop
    while True:
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
                    # Kill sound on pause
                    if params.osc_client:
                        params.osc_client.send_message("/life/gate", [0.0])
                elif not params.working:
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
            if not ret:
                print("Error: Could not read frame from webcam.")
                sys.exit(1)
            
            # 1. Flip ONCE (Mirror Effect)
            frame = cv2.flip(frame, 1) 
            
            # 2. Process (Draws landmarks directly on 'frame')
            # We don't need to assign the return value if process modifies 'frame' in place,
            # but your process returns 'frame', so we assign it.
            frame = hand_controller.process(frame, params)
            
            # 3. Store the MIRRORED frame. Do NOT flip back!
            params.frame_with_lm_drawn = frame 

            if WORKING_DRAWABLE or not params.working:
                # Apply Drawing/Erasing from Cursor
                cx, cy = params.cursor_pos
                if cx != -1 and cy != -1:
                    gx = cx // PX_SIZE
                    gy = cy // PX_SIZE
                    
                    for dy in range(-params.cursor_size, params.cursor_size + 1):
                        for dx in range(-params.cursor_size, params.cursor_size + 1):
                            if dx*dx + dy*dy <= params.cursor_size*params.cursor_size:
                                nx = gx + dx
                                ny = gy + dy
                                if 0 <= nx < params.WIDTH and 0 <= ny < params.HEIGHT:
                                    if params.hand_drawing:
                                        params.live_cells.setdefault((nx, ny), np.random.randint(len(params.ALIVE_COLOR)))
                                    elif params.hand_erasing:
                                        params.live_cells.pop((nx, ny), None)

        if WORKING_DRAWABLE or not params.working:
            key_pressed = pygame.key.get_pressed()
            pos = pygame.mouse.get_pos()
            gx = pos[0] // PX_SIZE
            gy = pos[1] // PX_SIZE
            if 0 <= gx < params.WIDTH and 0 <= gy < params.HEIGHT:
                if key_pressed[pygame.K_e]:
                    params.live_cells.pop((gx, gy), None)
                elif key_pressed[pygame.K_w]:
                    params.live_cells[(gx, gy)] = np.random.randint(len(params.ALIVE_COLOR))

        # --- GAME LOGIC (Simulation) ---
        if not params.working:
            # Single-step manual advance
            if key_pressed[pygame.K_n]:
                update_game_logic(params)
                time.sleep(0.08)
        else:
            # Automatic advance
            update_game_logic(params)
            
        # --- SOUND LOGIC (Always Run) ---
        # This ensures we can hear static cells when paused,
        # AND ensures sound stops (Gate 0) if we move the hand away.
        update_sound_probe(params)
            
        render(params)
        draw_hud(params, clock.get_fps())
        pygame.display.update()
        clock.tick(fps)

if __name__ == "__main__":
    main()
