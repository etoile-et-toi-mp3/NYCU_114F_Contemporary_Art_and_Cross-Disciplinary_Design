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
            hands_data = list(zip(results.multi_hand_landmarks, results.multi_handedness))
            
            # CASE 1: Two Hands
            if len(hands_data) == 2:
                # Sort by Wrist X: Lower X (Left) = Controller, Higher X (Right) = Cursor
                hands_data.sort(key=lambda h: h[0].landmark[0].x)
                self._process_controller_hand(frame, hands_data[0][0], params)
                self._process_cursor_hand(frame, hands_data[1][0], params)

            # CASE 2: One Hand
            elif len(hands_data) == 1:
                landmarks, handedness = hands_data[0]
                label = handedness.classification[0].label
                if label == "Right":
                    self._process_cursor_hand(frame, landmarks, params)
                else:
                    self._process_controller_hand(frame, landmarks, params)

            # Draw skeletons
            for landmarks, _ in hands_data:
                self.mp_draw.draw_landmarks(frame, landmarks, self.mp_hands.HAND_CONNECTIONS, 
                                            self.mp_draw.DrawingSpec(color=(0,0,255), thickness=2, circle_radius=2),
                                            self.mp_draw.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2))
        
        return frame

    def _process_cursor_hand(self, frame, hand_landmarks, params: Withcap_params):
        r_thumb = hand_landmarks.landmark[4]
        r_index = hand_landmarks.landmark[8]

        # 1. Pos
        r_mid_x = (r_thumb.x + r_index.x) / 2
        r_mid_y = (r_thumb.y + r_index.y) / 2
        cx = int(r_mid_x * params.WIDTH * PX_SIZE)
        cy = int(r_mid_y * params.HEIGHT * PX_SIZE)
        params.cursor_pos = (cx, cy)

        # 2. Size
        distance = math.hypot(r_index.x - r_thumb.x, r_index.y - r_thumb.y)
        raw_size = int(distance * 40)
        params.cursor_size = max(1, min(raw_size, 15))

        # Visual line (Use frame dimensions!)
        h, w, _ = frame.shape
        tx, ty = int(r_thumb.x * w), int(r_thumb.y * h)
        ix, iy = int(r_index.x * w), int(r_index.y * h)
        cv2.line(frame, (tx, ty), (ix, iy), (255, 0, 255), 2)

    def _process_controller_hand(self, frame, hand_landmarks, params: Withcap_params):
        l_thumb = hand_landmarks.landmark[4]
        l_index = hand_landmarks.landmark[8]
        l_middle = hand_landmarks.landmark[12]
        l_ring = hand_landmarks.landmark[16]
        l_pinky = hand_landmarks.landmark[20]

        # Visual Lines (Use frame dimensions!)
        h, w, _ = frame.shape
        cv2.line(frame, 
                 (int(l_thumb.x * w), int(l_thumb.y * h)), 
                 (int(l_index.x * w), int(l_index.y * h)), 
                 (255, 255, 0), 3)

        # 1. DRAW
        if self.calculate_distance(l_thumb, l_index) < 0.05:
            params.hand_drawing = True
        # 2. ERASE
        elif self.calculate_distance(l_thumb, l_middle) < 0.05:
            params.hand_erasing = True
        # 3. RANDOM
        elif self.calculate_distance(l_thumb, l_ring) < 0.05:
            current_time = time.time()
            if current_time - params.last_random_time > 1.0 and not params.working:
                params.live_cells.clear()
                for x in range(params.WIDTH):
                    for y in range(params.HEIGHT):
                        if np.random.random() < 0.3:
                            params.live_cells[(x, y)] = np.random.randint(len(params.ALIVE_COLOR))
                params.last_random_time = current_time
        # 4. CLEAR
        elif self.calculate_distance(l_thumb, l_pinky) < 0.05:
            current_time = time.time()
            if current_time - params.last_clear_time > 1.0 and not params.working:
                params.live_cells.clear()
                params.last_clear_time = current_time
        
        # 5. TOGGLE (Angle)
        dy = l_index.y - l_thumb.y
        dx = l_index.x - l_thumb.x
        angle = math.degrees(math.atan2(dy, dx))
        
        is_horizontal = abs(angle) < 25 or abs(angle) > 155
        is_open_hand = self.calculate_distance(l_thumb, l_index) > self.calculate_distance(l_index, hand_landmarks.landmark[5])

        current_time = time.time()
        if is_horizontal and is_open_hand and (current_time - params.last_toggle_time > 1.0):
            params.working = 1 - params.working
            params.last_toggle_time = current_time
            print(f"Toggle! Angle: {int(angle)}°")

            # Green Line for Toggle
            cv2.line(frame, 
                    (int(l_thumb.x * w), int(l_thumb.y * h)), 
                    (int(l_index.x * w), int(l_index.y * h)), 
                    (0, 255, 0), 3)
