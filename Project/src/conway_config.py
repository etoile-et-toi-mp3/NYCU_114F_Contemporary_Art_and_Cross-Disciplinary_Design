# Read-Only Constants
WORKING_FPS = 15
DRAWING_FPS = 150
DEAD_COLOR = (50, 50, 50)

LIGHT_GREEN = [(101, 243, 76)]
LIGHT_BLUE = [(141, 186, 242)]
CYBER_SOFT = [(77, 210, 255), (255, 105, 180), (127, 255, 212)]
WARM_COLORS = [(255, 159, 67), (255, 215, 0), (255, 127, 80)]
VIBRANT_FLORAL = [ # vibrant floral colors
    (255, 105, 180),  # Hot Pink (Hibiscus)
    (255, 165, 0),    # Orange (Marigold)
    (255, 255, 0),    # Yellow (Sunflower)
    (138, 43, 226),   # Blue Violet (Iris)
    (220, 20, 60),    # Crimson (Rose)
    (0, 191, 255)     # Deep Sky Blue (Morning Glory)
]
FRUTIGER_AERO = [
    (18, 153, 202),
    (53, 188, 222),
    (111, 215, 236),
    (156, 239, 242),
    (241,255,205),
    (204,255,124),
    (159,225,29)
]
CYBERPUNK_NEON = [
    (110, 203, 245),
    (194, 82, 225),
    (224, 217, 246),
    (88, 106, 226),
    (42, 35, 86)
]

ALIVE_COLOR = VIBRANT_FLORAL

BASE_COLOR = (90, 90, 90)
WIDTH = 100
HEIGHT = 100
PX_SIZE = 10
WEBCAM_INDEX = 5
WORKING_DRAWABLE = True

# OSC section
OSC_IP = "127.0.0.1"
OSC_PORT = 9000  # VCV Rack default is often 9000 or 8000
MAX_VOICES = 16  # Limit how many notes play per frame to prevent crashing VCV
PITCH_MIN = -3.0 # -3 Octaves (C-3)
PITCH_MAX = 7.0  # 10 Octaves (C0 to C10)
