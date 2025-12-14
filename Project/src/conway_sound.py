import random
import math
from conway_config import *

def get_closest_chord_tone(raw_pitch):
    """STABLE: Snaps to Major 7th Chord (4 notes/octave)"""
    octave = int(raw_pitch)
    fraction = raw_pitch - octave
    chord_tones = [0.0, 4/12.0, 7/12.0, 11/12.0]
    closest = min(chord_tones, key=lambda x: abs(x - fraction))
    return octave + closest

def get_closest_scale_tone(raw_pitch):
    """CHAOS: Snaps to Major Scale (7 notes/octave)"""
    octave = int(raw_pitch)
    fraction = raw_pitch - octave
    scale_tones = [0.0, 2/12.0, 4/12.0, 5/12.0, 7/12.0, 9/12.0, 11/12.0]
    closest = min(scale_tones, key=lambda x: abs(x - fraction))
    return octave + closest

def process_sound(params):
    if not params.osc_client: return

    # Lists for Pitches, Pans, Gates, AND GAINS
    chaos_pitches = []
    chaos_pans = []
    chaos_gains = []
    
    stable_pitches = []
    stable_pans = []
    stable_gains = []

    # Get probed cells
    probed_cells = list(params.sound_posedge)
    
    if len(probed_cells) > MAX_VOICES:
        probed_cells = random.sample(probed_cells, MAX_VOICES)

    # --- PRE-CALCULATE CURSOR INFO ---
    # We need the cursor center (in grid units) to measure distance
    cursor_gx = params.cursor_pos[0] // params.PX_SIZE
    cursor_gy = params.cursor_pos[1] // params.PX_SIZE
    max_radius = params.cursor_size # The edge of the circle

    for (x, y) in probed_cells:
        # Check Stability
        stability = params.cell_stability.get((x, y), 0)
        
        # 1. Calculate Pitch & Pan
        pan = 5 * ((x / params.WIDTH) * 2.0 - 1.0)
        norm_y = 1.0 - (y / params.HEIGHT)
        base_pitch = PITCH_MIN + (norm_y * (PITCH_MAX - PITCH_MIN))

        # 2. --- CALCULATE GAIN (VOLUME) ---
        # Distance formula: sqrt(dx^2 + dy^2)
        dist = math.hypot(x - cursor_gx, y - cursor_gy)
        
        # Normalize: 0.0 (center) to 1.0 (edge)
        # Avoid division by zero if radius is tiny
        if max_radius > 0:
            norm_dist = dist / max_radius
        else:
            norm_dist = 0.0
            
        # Invert: Closer = Louder (1.0), Further = Quieter (0.0)
        # We clamp it to ensure we don't go below 0
        gain = max(0.0, 1.0 - norm_dist)
        
        # Optional: Curve the gain so it falls off faster (more natural)
        gain = gain * gain 

        # --- ROUTING LOGIC ---
        
        if stability < 10: 
            # CHAOS
            quantized = get_closest_scale_tone(base_pitch)
            chaos_pitches.append(quantized + 2.0)
            chaos_pans.append(pan)
            chaos_gains.append(gain) # Store Gain
        else:
            # STABLE
            quantized = get_closest_chord_tone(base_pitch)
            stable_pitches.append(quantized)
            stable_pans.append(pan)
            stable_gains.append(gain) # Store Gain

    # --- SEND MESSAGES ---

    # 1. Chaos Voice
    if chaos_pitches:
        params.osc_client.send_message("/life/chaos/pitch", chaos_pitches)
        params.osc_client.send_message("/life/chaos/pan", chaos_pans)
        params.osc_client.send_message("/life/chaos/gate", [1.0] * len(chaos_pitches))
        params.osc_client.send_message("/life/chaos/gain", chaos_gains) # <--- NEW
    else:
        params.osc_client.send_message("/life/chaos/gate", [0.0])

    # 2. Stable Voice
    if stable_pitches:
        params.osc_client.send_message("/life/stable/pitch", stable_pitches)
        params.osc_client.send_message("/life/stable/pan", stable_pans)
        params.osc_client.send_message("/life/stable/gate", [1.0] * len(stable_pitches))
        params.osc_client.send_message("/life/stable/gain", stable_gains) # <--- NEW
    else:
        params.osc_client.send_message("/life/stable/gate", [0.0])