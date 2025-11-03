# game.py

import pygame
import numpy as np # Still needed for np.random
import signal, sys
import argparse
import cv2

# Import our new modules
import game_utils
from config import * # Import all constants

def main():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Conway's Game of Life")
    parser.add_argument(
        '-f', '--fullscreen', action='store_true', help='Run in full-screen mode'
    )
    parser.add_argument(
        '-w', '--webcam', action='store_true', help='Use webcam as background'
    )
    args = parser.parse_args()
    
    # --- Pygame Setup ---
    pygame.init()
    pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONUP])

    # --- Screen Setup ---
    if args.fullscreen:
        info = pygame.display.Info()
        WIDTH_PX, HEIGHT_PX = info.current_w, info.current_h
        screen = pygame.display.set_mode((WIDTH_PX, HEIGHT_PX), pygame.FULLSCREEN)
        WIDTH = WIDTH_PX // PX_SIZE
        HEIGHT = HEIGHT_PX // PX_SIZE
    else:
        WIDTH = 100
        HEIGHT = 100
        WIDTH_PX = WIDTH * PX_SIZE
        HEIGHT_PX = HEIGHT * PX_SIZE
        screen = pygame.display.set_mode((WIDTH_PX, HEIGHT_PX))

    pygame.display.set_caption("Conway's Game of Life")
    screen.fill(BASE_COLOR)
    
    # --- Webcam Setup ---
    cap = None
    webcam_enabled = False
    if args.webcam:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open webcam. Running in standard mode.")
        else:
            webcam_enabled = True
            print("Webcam enabled.")

    # --- Game State Variables ---
    clock = pygame.time.Clock()
    working = 0
    FPS = DRAWING_FPS
    live_cells = set()
    
    # --- Shutdown Handler ---
    def graceful_shutdown(sig, frame):
        print("\nShutting down...")
        live_cells.clear()
        if cap:
            cap.release()
        pygame.quit()
        sys.exit(0)
    signal.signal(signal.SIGINT, graceful_shutdown)

    # --- Main Loop ---
    while True:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                graceful_shutdown(None, None)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    graceful_shutdown(None, None)
                elif event.key == pygame.K_s:
                    working = 1; FPS = WORKING_FPS
                elif event.key == pygame.K_p:
                    working = 0; FPS = DRAWING_FPS
                elif working == 0:
                    if event.key == pygame.K_c:
                        live_cells.clear()
                    elif event.key == pygame.K_r:
                        live_cells.clear()
                        for x in range(WIDTH):
                            for y in range(HEIGHT):
                                if np.random.random() < 0.3:
                                    live_cells.add((x, y))

            if working == 0 and event.type == pygame.MOUSEBUTTONUP:
                pos = pygame.mouse.get_pos()
                gx = pos[0] // PX_SIZE
                gy = pos[1] // PX_SIZE
                if 0 <= gx < WIDTH and 0 <= gy < HEIGHT:
                    if (gx, gy) in live_cells:
                        live_cells.remove((gx, gy))
                    else:
                        live_cells.add((gx, gy))
        
        # --- Continuous Input (Drawing) ---
        if working == 0:
            key_pressed = pygame.key.get_pressed()
            pos = pygame.mouse.get_pos()
            gx = pos[0] // PX_SIZE
            gy = pos[1] // PX_SIZE
            if 0 <= gx < WIDTH and 0 <= gy < HEIGHT:
                if key_pressed[pygame.K_e]:
                    live_cells.discard((gx, gy))
                elif key_pressed[pygame.K_w]:
                    live_cells.add((gx, gy))
                elif key_pressed[pygame.K_n]:
                    # Call the imported update function
                    live_cells = game_utils.update(live_cells)
            
            # Call the imported render function
            game_utils.render(screen, cap, live_cells, WIDTH, HEIGHT, webcam_enabled)
            
        # --- Simulation Running ---
        if working == 1:
            live_cells = game_utils.update(live_cells)
            game_utils.render(screen, cap, live_cells, WIDTH, HEIGHT, webcam_enabled)

        pygame.display.update()
        clock.tick(FPS)

if __name__ == "__main__":
    main()