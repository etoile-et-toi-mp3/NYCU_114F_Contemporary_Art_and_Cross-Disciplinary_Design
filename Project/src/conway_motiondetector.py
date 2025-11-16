# motion.py
import cv2
import mediapipe as mp
from conway_dataclass import Withcap_params
import math
import time
import numpy as np
from conway_config import PX_SIZE

class HandController:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils

    def calculate_distance(self, p1, p2):
        return math.hypot(p2.x - p1.x, p2.y - p1.y)

    def process(self, frame, params: Withcap_params):
        # Convert to RGB for MediaPipe
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)

        # Reset transient flags every frame
        params.hand_drawing = False
        params.hand_erasing = False
        params.cursor_pos = (-1, -1)

        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                self.mp_draw.draw_landmarks(frame, hand_landmarks, 
                                            self.mp_hands.HAND_CONNECTIONS,
                                            self.mp_draw.DrawingSpec(color=(0,0,255), thickness=2, circle_radius=2), # Red dots
                                            self.mp_draw.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2)) # Green lines
                # MediaPipe assumes mirrored input usually, so:
                # "Right" label usually means the user's Right hand in webcam view
                label = handedness.classification[0].label 
                
                # --- Right HAND (as seen on screen): CURSOR ---
                # (In MediaPipe "Right" label often appears as Right hand on screen due to mirroring)
                if label == "Right": 
                    thumb = hand_landmarks.landmark[4]
                    index = hand_landmarks.landmark[8]
                    
                    # 1. Calculate Midpoint (The new Cursor Position)
                    # We average the X and Y of both fingers
                    mid_x = (thumb.x + index.x) / 2
                    mid_y = (thumb.y + index.y) / 2
                    
                    cx = int(mid_x * params.WIDTH * PX_SIZE)
                    cy = int(mid_y * params.HEIGHT * PX_SIZE)
                    params.cursor_pos = (cx, cy)

                    # 2. Calculate Distance (The new Cursor Size)
                    # Calculate Euclidean distance (0.0 to ~0.4 in normalized space)
                    distance = math.hypot(index.x - thumb.x, index.y - thumb.y)
                    
                    # 3. Map Distance to Grid Size
                    # Sensitivity factor: 40. 
                    # If distance is 0.02 (pinched), size ~ 1. 
                    # If distance is 0.30 (wide open), size ~ 12.
                    raw_size = int(distance * 40) 
                    
                    # Clamp the size so it doesn't get too huge or vanish
                    # Min size 1, Max size 15 grid cells
                    params.cursor_size = max(1, min(raw_size, 15))

                    # --- OPTIONAL: Draw visual line on the frame for feedback ---
                    h, w, _ = frame.shape
                    tx, ty = int(thumb.x * w), int(thumb.y * h)
                    ix, iy = int(index.x * w), int(index.y * h)
                    cv2.line(frame, (tx, ty), (ix, iy), (255, 0, 255), 2) # Magenta line

                # --- Right HAND (as seen on screen): CONTROLLER ---
                else: 
                    # Get landmarks for Thumb(4), Index(8), Middle(12), Ring(16), Pinky(20)
                    thumb = hand_landmarks.landmark[4]
                    index = hand_landmarks.landmark[8]
                    middle = hand_landmarks.landmark[12]
                    ring = hand_landmarks.landmark[16]
                    pinky = hand_landmarks.landmark[20]
                    
                    # 0. Draw lines between thumb and other fingers for visualization
                    # (Color is BGR: Blue=255, Green=255, Red=0)
                    cv2.line(frame, (int(thumb.x * params.WIDTH * PX_SIZE), int(thumb.y * params.HEIGHT * PX_SIZE)),
                             (int(index.x * params.WIDTH * PX_SIZE), int(index.y * params.HEIGHT * PX_SIZE)), (255, 255, 0), 3)

                    # 1. DRAW (Thumb + Index Pinch)
                    if self.calculate_distance(thumb, index) < 0.05:
                        params.hand_erasing = False
                        params.hand_drawing = True

                    # 2. ERASE (Thumb + Middle Pinch)
                    elif self.calculate_distance(thumb, middle) < 0.05:
                        params.hand_drawing = False
                        params.hand_erasing = True

                    # 3. RANDOM (Thumb + Ring Pinch) - Needs Debounce (Wait 1 sec)
                    elif self.calculate_distance(thumb, ring) < 0.05:
                        current_time = time.time()
                        if current_time - params.last_random_time > 1.0 and not params.working:
                            # Trigger Random Logic Here
                            import numpy as np # Lazy import or pass it
                            params.live_cells.clear()
                            for x in range(params.WIDTH):
                                for y in range(params.HEIGHT):
                                    if np.random.random() < 0.3:
                                        params.live_cells[(x, y)] = np.random.randint(len(params.ALIVE_COLOR))
                            params.last_random_time = current_time

                    # 4. CLEAR (Thumb + Pinky Pinch) - Needs Debounce
                    elif self.calculate_distance(thumb, pinky) < 0.05:
                        current_time = time.time()
                        if current_time - params.last_clear_time > 1.0 and not params.working:
                            params.live_cells.clear()
                            params.last_clear_time = current_time

                    # 5. TOGGLE MODE (Fast Slope Change)
                    # Calculate slope between thumb and index
                    try:
                        slope = (index.y - thumb.y) / (index.x - thumb.x)
                    except ZeroDivisionError:
                        slope = None
                        
                    print("Slope:", slope)
                    if slope is not None and -1 < slope < 0.5 and self.calculate_distance(thumb, index) > self.calculate_distance(index, hand_landmarks.landmark[5]): # Check the fingers distance longer than the index finger length
                        current_time = time.time()
                        if current_time - params.last_toggle_time > 1.0:
                            params.last_toggle_time = current_time
                            params.working = 1 if params.working == 0 else 0

        return frame