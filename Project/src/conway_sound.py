import random
from conway_config import *

def process_sound(params):
    if not params.osc_client:
        return

    # --- 1. HANDLE SILENCE ---
    # If no births, send a "Gate Off" to stop sustaining notes
    if not params.sound_posedge:
        params.osc_client.send_message("/life/gate", [0.0])
        return

    # 2. Prepare lists
    pitches = []
    pans = []
    gates = []

    # 3. Get Births
    births = list(params.sound_posedge)
    
    # 4. Limit to MAX_VOICES
    if len(births) > MAX_VOICES:
        births = random.sample(births, MAX_VOICES)

    # 5. Fill the lists
    for (x, y) in births:
        # Pan
        pan_val = (x / params.WIDTH) * 2.0 - 1.0
        pans.append(float(pan_val))
        
        # Pitch
        ONE_SEMITONE = 1.0 / 12.0 
        pitch_val = PITCH_MIN + ONE_SEMITONE * ( (params.HEIGHT - 1 - y) * ( (PITCH_MAX - PITCH_MIN) * 12.0 / params.HEIGHT ) )
        pitches.append(float(pitch_val))
        
        # Gate (Triggers the envelope)
        gates.append(1.0)

    # 6. Send POLYPHONIC Messages
    if pitches: 
        params.osc_client.send_message("/life/pitch", pitches)
        params.osc_client.send_message("/life/pan", pans)
        params.osc_client.send_message("/life/gate", gates)
