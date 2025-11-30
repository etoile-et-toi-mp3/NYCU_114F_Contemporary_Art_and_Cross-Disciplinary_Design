# sound_system.py
import random
from conway_config import *

def process_sound(params):
    if not params.osc_client or not params.sound_posedge:
        return

    # 1. Prepare lists
    pitches = []
    pans = []

    # 2. Get Births
    births = list(params.sound_posedge)
    
    # 3. Limit to MAX_VOICES (e.g., 16)
    # If we have more than 16 births, random sample 16 of them
    if len(births) > MAX_VOICES:
        births = random.sample(births, MAX_VOICES)

    # 4. Fill the lists
    for (x, y) in births:
        # Calculate Pan
        pan_val = (x / params.WIDTH) * 2.0 - 1.0
        pans.append(float(pan_val))
        
        # Calculate Pitch
        ONE_SEMITONE = 1.0 / 12.0  # V/Oct
        # normalized_y = 1.0 - (y / params.HEIGHT)
        # pitch_val = PITCH_MIN + (normalized_y * (PITCH_MAX - PITCH_MIN))
        pitch_val = PITCH_MIN + ONE_SEMITONE * ( (params.HEIGHT - 1 - y) * ( (PITCH_MAX - PITCH_MIN) * 12.0 / params.HEIGHT ) )
        pitches.append(float(pitch_val))

    # 5. Send POLYPHONIC Messages
    # By passing a LIST, python-osc sends it as a multi-argument message.
    # trowaSoft cvOSCcv interprets this as a Polyphonic Signal.
    
    if pitches: # Only send if there are notes
        params.osc_client.send_message("/life/pitch", pitches)
        params.osc_client.send_message("/life/pan", pans)
