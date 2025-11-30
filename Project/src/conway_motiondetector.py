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
            min_tracking_confidence=0.5,
        )
        self.mp_draw = mp.solutions.drawing_utils

    def calculate_distance(self, p1, p2):
        return math.hypot(p2.x - p1.x, p2.y - p1.y)

    def process(self, frame, params: Withcap_params):
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)

        params.hand_drawing = False
        params.hand_erasing = False
        params.cursor_pos = (-1, -1)

        if results.multi_hand_landmarks:
            # ZIP landmarks and handedness together so we keep them paired
            hands_data = list(zip(results.multi_hand_landmarks, results.multi_handedness))
            
            # --- LOGIC START ---
            
            # CASE 1: Two Hands Detected - Use Relative Sorting
            if len(hands_data) == 2:
                # Sort by Wrist X coordinate (landmark 0)
                # Lower X = Left side of screen = Controller
                # Higher X = Right side of screen = Cursor
                hands_data.sort(key=lambda h: h[0].landmark[0].x)
                
                # Force assignment based on sorted order
                left_hand_data = hands_data[0]  # Controller
                right_hand_data = hands_data[1] # Cursor
                
                # Process them with forced roles
                self._process_controller_hand(frame, left_hand_data[0], params)
                self._process_cursor_hand(frame, right_hand_data[0], params)

            # CASE 2: One Hand Detected - Trust the Label
            elif len(hands_data) == 1:
                landmarks, handedness = hands_data[0]
                label = handedness.classification[0].label
                
                if label == "Right":
                    self._process_cursor_hand(frame, landmarks, params)
                else:
                    self._process_controller_hand(frame, landmarks, params)

            # --- VISUALIZATION ---
            # Draw skeletons for all hands (visual feedback is important)
            for landmarks, _ in hands_data:
                self.mp_draw.draw_landmarks(frame, landmarks, self.mp_hands.HAND_CONNECTIONS, 
                                            self.mp_draw.DrawingSpec(color=(0,0,255), thickness=2, circle_radius=2),
                                            self.mp_draw.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2))
        
        return frame

    def _process_cursor_hand(self, frame, hand_landmarks, params: Withcap_params):
        r_thumb = hand_landmarks.landmark[4]
        r_index = hand_landmarks.landmark[8]

        # 1. Calculate Midpoint (The new Cursor Position)
        # We average the X and Y of both fingers
        r_mid_x = (r_thumb.x + r_index.x) / 2
        r_mid_y = (r_thumb.y + r_index.y) / 2

        cx = int(r_mid_x * params.WIDTH * PX_SIZE)
        cy = int(r_mid_y * params.HEIGHT * PX_SIZE)
        params.cursor_pos = (cx, cy)

        # 2. Calculate Distance (The new Cursor Size)
        # Calculate Euclidean distance (0.0 to ~0.4 in normalized space)
        distance = math.hypot(r_index.x - r_thumb.x, r_index.y - r_thumb.y)

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
        tx, ty = int(r_thumb.x * w), int(r_thumb.y * h)
        ix, iy = int(r_index.x * w), int(r_index.y * h)
        cv2.line(
            frame, (tx, ty), (ix, iy), (255, 0, 255), 2
        )  # Magenta line

    def _process_controller_hand(self, frame, hand_landmarks, params: Withcap_params):
        l_thumb = hand_landmarks.landmark[4]
        l_index = hand_landmarks.landmark[8]
        l_middle = hand_landmarks.landmark[12]
        l_ring = hand_landmarks.landmark[16]
        l_pinky = hand_landmarks.landmark[20]

        # 0. Draw lines between thumb and other fingers for visualization
        # (Color is BGR: Blue=255, Green=255, Red=0)
        cv2.line(
            frame,
            (
                int(l_thumb.x * params.WIDTH * PX_SIZE),
                int(l_thumb.y * params.HEIGHT * PX_SIZE),
            ),
            (
                int(l_index.x * params.WIDTH * PX_SIZE),
                int(l_index.y * params.HEIGHT * PX_SIZE),
            ),
            (255, 255, 0),
            3,
        )

        # 1. DRAW (Thumb + Index Pinch)
        if self.calculate_distance(l_thumb, l_index) < 0.05:
            params.hand_erasing = False
            params.hand_drawing = True

        # 2. ERASE (Thumb + Middle Pinch)
        elif self.calculate_distance(l_thumb, l_middle) < 0.05:
            params.hand_drawing = False
            params.hand_erasing = True

        # 3. RANDOM (Thumb + Ring Pinch) - Needs Debounce (Wait 1 sec)
        elif self.calculate_distance(l_thumb, l_ring) < 0.05:
            current_time = time.time()
            if (
                current_time - params.last_random_time > 1.0
                and not params.working
            ):
                # Trigger Random Logic Here
                params.live_cells.clear()
                for x in range(params.WIDTH):
                    for y in range(params.HEIGHT):
                        if np.random.random() < 0.3:
                            params.live_cells[(x, y)] = np.random.randint(
                                len(params.ALIVE_COLOR)
                            )
                params.last_random_time = current_time

        # 4. CLEAR (Thumb + Pinky Pinch) - Needs Debounce
        elif self.calculate_distance(l_thumb, l_pinky) < 0.05:
            current_time = time.time()
            if (
                current_time - params.last_clear_time > 1.0
                and not params.working
            ):
                params.live_cells.clear()
                params.last_clear_time = current_time

        # 5. TOGGLE MODE (Fast Slope Change)
        # A. Calculate Angle (Better than slope)
        # atan2 returns radians, we convert to degrees (-180 to 180)
        dy = l_index.y - l_thumb.y
        dx = l_index.x - l_thumb.x
        angle = math.degrees(math.atan2(dy, dx))

        # B. Check if Hand is Horizontal
        # Horizontal is near 0 degrees (Thumb Left, Index Right)
        # OR near 180/-180 degrees (Thumb Right, Index Left)
        is_horizontal = abs(angle) < 25 or abs(angle) > 155

        # C. Check if Hand is OPEN (Not pinching)
        # We check if thumb-index distance is significantly large
        # (Larger than the length of the index finger's first bone is a good metric)
        is_open_hand = self.calculate_distance(
            l_thumb, l_index
        ) > self.calculate_distance(l_index, hand_landmarks.landmark[5])
        
        # D. Debounce Time Check
        current_time = time.time()
        time_passed = current_time - params.last_toggle_time

        # --- FINAL TRIGGER LOGIC ---
        if is_horizontal and is_open_hand and time_passed > 1.0:
            params.working = 1 - params.working  # Toggle 0/1
            params.last_toggle_time = current_time  # Reset timer
            print(f"Toggle! Angle: {int(angle)}°")

        # Optional: Visual Feedback for the Angle
        # Draw the line Green if horizontal, Yellow if not
        line_color = (0, 255, 0) if is_horizontal else (0, 255, 255)  # BGR

        # Draw line on frame to see it working
        h, w, _ = frame.shape
        cv2.line(
            frame,
            (int(l_thumb.x * w), int(l_thumb.y * h)),
            (int(l_index.x * w), int(l_index.y * h)),
            line_color,
            3,
        )
