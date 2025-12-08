import random
from conway_config import *

def process_sound(params):
    if not params.osc_client: return

    # We need two separate lists now
    chaos_pitches = []
    chaos_pans = []
    
    stable_pitches = []
    stable_pans = []

    # Get the probed cells (from utils)
    probed_cells = list(params.live_cells.keys())

    for (x, y) in probed_cells:
        # Check Stability
        stability = params.cell_stability.get((x, y), 0)
        
        # Calculate Base Pitch/Pan (Same math as before)
        pan = (x / params.WIDTH) * 2.0 - 1.0
        norm_y = 1.0 - (y / params.HEIGHT)
        base_pitch = PITCH_MIN + (norm_y * (PITCH_MAX - PITCH_MIN))

        # --- ROUTING LOGIC ---
        if stability < 10: 
            # === CHAOS MODE ===
            # Shift pitch UP by 1 or 2 octaves for "craziness"
            chaos_pitches.append(base_pitch + 1.0) 
            chaos_pans.append(pan)
        else:
            # === STABLE MODE ===
            # Shift pitch DOWN by 1 or 2 octaves for "drone"
            stable_pitches.append(base_pitch - 1.0)
            stable_pans.append(pan)

    # Send Separate OSC Messages
    # Chaos Voice (High, Fast) -> VCV Channel 1/2
    if chaos_pitches:
        params.osc_client.send_message("/life/chaos/pitch", chaos_pitches)
        params.osc_client.send_message("/life/chaos/pan", chaos_pans)
        params.osc_client.send_message("/life/chaos/gate", [1.0] * len(chaos_pitches))
    else:
        params.osc_client.send_message("/life/chaos/gate", [0.0]) # Kill if empty

    # Stable Voice (Low, Slow) -> VCV Channel 3/4
    if stable_pitches:
        params.osc_client.send_message("/life/stable/pitch", stable_pitches)
        params.osc_client.send_message("/life/stable/pan", stable_pans)
        params.osc_client.send_message("/life/stable/gate", [1.0] * len(stable_pitches))
    else:
        params.osc_client.send_message("/life/stable/gate", [0.0])
