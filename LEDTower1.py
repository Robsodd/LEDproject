import asyncio
import random
import colorsys
import math

S1 = list(range(0, 25))
S2 = list(range(49, 24, -1))
S3 = list(range(50, 75))
S4 = list(range(99, 74, -1))

# The full 'snake' FULL_PATH (100 LEDs)
FULL_PATH = S1 + S2 + S3 + S4

# The 'Level' FULL_PATH (A list of 25 steps, each containing 4 LED IDs at the same height)
# Zip combines the sides so that HEIGHTS[0] = [0, 49, 50, 99] (all bottom LEDs)
HEIGHTS = [list(step) for step in zip(S1, S2, S3, S4)]

print(f"S1 Length: {len(S1)} | Max ID: {max(S1) if S1 else 'Empty'}")
print(f"S4 Length: {len(S2)} | Max ID: {max(S2) if S2 else 'Empty'}")
print(f"S3 Length: {len(S3)} | Max ID: {max(S3) if S3 else 'Empty'}")
print(f"S4 Length: {len(S4)} | Max ID: {max(S4) if S4 else 'Empty'}")
print(f"HEIGHTS Steps: {len(HEIGHTS)}")

# This is the "Golden Rule" check:
all_ids = S1 + S2 + S3 + S4
if any(idx >= 100 for idx in all_ids):
    print("!!! WARNING: Found an ID >= 100. This will cause IndexError !!!")
    print(f"Offending IDs: {[idx for idx in all_ids if idx >= 100]}")
else:
    print("Check Passed: All IDs are within 0-99.")
print("----------------------------------")

# Added 'rainbow_cycle' for fun!
__all__ = [
            'plain_white',
            'sparkle',
            'fire_flicker',
            'fire_tower',
            'breathing_pulse',
            'scanner_glow_ahead',
            'scanner_glow_ahead',
            'scanner_fade_in',
            'scanner',
            'comet_chase',
            'bounce_effect',
            'bounce_effect_single',
            'pulse_sync',
            'rainbow_comet',
            'rainbow_cycle',
            'rainbow_bounce',
            'rainbow_fall',
            'rainbow_stationary',
            'rainbow_stationary_top_bottom',
            'spinning_columns',
            'spinning_columns_fade',
            'stop',
            'rising_ring'
            ]

def get_path():
    s1 = list(range(0, 25))
    s2 = list(range(49, 24, -1))
    s3 = list(range(50, 75))
    s4 = list(range(99, 74, -1))
    return s1 + s2 + s3 + s4

async def stop(set_led, set_led_multiple, color, speed):
    # The fader in the HTML will handle the cleanup
    return 

async def plain_white(set_led, set_led_multiple, color, speed):
    """
    Fades in the entire tower to a steady white light at 50% brightness.
    """
    try:
        # Step 1: Fade In (0 to 10 steps)
        for i in range(11): 
            brightness = (i * 5) / 100.0  # Moves from 0.0 to 0.5
            current_white = dim_color("#ffffff", brightness)
            all_ids = []
            for led_id in range(25):
                # Corrected mapping for 100 LEDs (Sides 2 and 4 upside down)
                side1 = led_id
                side2 = 49 - led_id
                side3 = 50 + led_id
                side4 = 99 - led_id
                
                all_ids.extend([side1, side2, side3, side4])
                
            await set_led_multiple(all_ids, current_white)
            # Controls how fast the 'fade' happens
            await asyncio.sleep(plain_white.anim_speed)

        # Step 2: Hold steady
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        pass

plain_white.use_fader = False
plain_white.anim_speed = 0.10

async def comet_chase(set_led, set_led_multiple, color, speed):
    
    try:
        for led_id in FULL_PATH:
            await set_led(led_id, color)
            await asyncio.sleep(speed)
    except asyncio.CancelledError: pass

comet_chase.use_fader = True
comet_chase.fader_speed = 0.85
comet_chase.animation_speed = 0.50

async def bounce_effect_single(set_led, set_led_multiple, color, speed):
    
    try:
        path = FULL_PATH + list(reversed(FULL_PATH))
        for led_id in path:
            await set_led(led_id, color)
            await asyncio.sleep(speed)
    except asyncio.CancelledError: pass

bounce_effect_single.use_fader = True
bounce_effect_single.fader_speed = 0.85
bounce_effect_single.animation_speed = 0.50

async def bounce_effect(set_led, set_led_multiple, color, speed):
    """
    Simultaneously bounces a light pulse up and down all four sides.
    Uses the pre-calculated HEIGHTS global for efficiency.
    """
    # Create the up-and-down loop: Floor -> Ceiling -> Floor
    # HEIGHTS provides the 4-pixel lists: [s1, s2, s3, s4]
    bounce_path = HEIGHTS + HEIGHTS[-2:0:-1]
    print(f"bounce_path Length: {len(bounce_path)}")
    print("--- Detailed Bounce Path ---")
    for i, step in enumerate(bounce_path):
        print(f"Step {i:02}: {step}")
    try:
        while True:
            for step_ids in bounce_path:
                # Use set_led_multiple to update all 4 sides at the exact same time
                await set_led_multiple(step_ids, color)
                
                # The 'anim_speed' tag controls the bounce velocity
                await asyncio.sleep(speed)
                
    except asyncio.CancelledError:
        pass

# TAGS
bounce_effect.use_fader = True
bounce_effect.fader_speed = 0.85
bounce_effect.anim_speed = 0.01

async def pulse_sync(set_led, set_led_multiple, color, speed):
    try:
        while True:
            for i in range(100): await set_led(i, color)
            await asyncio.sleep(speed * 10)
    except asyncio.CancelledError: pass

async def rainbow_comet(set_led, set_led_multiple, color, speed):
     # This gets your 100-LED FULL_PATH
    hue = 0
    
    try:
        while True:
            for led_id in FULL_PATH:
                # 1. Calculate current rainbow color
                current_hex = hsl_to_hex(hue, 100, 50)
                
                # 2. Light up the "head" of the comet
                await set_led(led_id, current_hex)
                
                # 3. Shift the color slightly for the next pixel
                hue = (hue + 2) % 360 
                
                # 4. Wait before moving to the next pixel
                await asyncio.sleep(speed)
                
    except asyncio.CancelledError:
        pass

# SETTINGS
rainbow_comet.use_fader = True     # This creates the "tail"
rainbow_comet.fader_speed = 0.85   # Higher = longer rainbow tail
rainbow_comet.anim_speed = 0.02    # Lower = faster moving comet

async def rainbow_bounce(set_led, set_led_multiple, color, speed):
    """
    Simultaneously bounces a rainbow-shifting pulse up and down all four sides.
    Uses pre-calculated HEIGHTS and batch updates.
    """
    hue = 0
    # Bounce path: Floor to Ceiling, then Ceiling down to Floor
    # This uses the HEIGHTS global [s1, s2, s3, s4] lists
    bounce_path = HEIGHTS + HEIGHTS[-2:0:-1]
    path_pairs = list(zip(bounce_path, bounce_path[1:] + [bounce_path[0]]))
    try:
        while True:
            for current_step, next_step in path_pairs:
                current_hex = hsl_to_hex(hue, 100, 50)
                # You now have both objects ready to use
                await set_led_multiple(next_step, current_hex, 0.5)
                await set_led_multiple(current_step, current_hex, 1)
                # ... do something with next_step ...
                hue = (hue + 5) % 360 
                
                await asyncio.sleep(speed)                
    except asyncio.CancelledError:
        pass

# TAGS
rainbow_bounce.use_fader = True
rainbow_bounce.fader_speed = 0.80  # Nice trail as it bounces
rainbow_bounce.anim_speed = 0.04   # Snappy movement


async def rainbow_cycle(set_led, set_led_multiple, color, speed):
    
    try:
        # We add an 'offset' so the rainbow actually moves over time
        offset = 0
        while True:
            for i, led_id in enumerate(FULL_PATH):
                # Calculate the hue based on position + time offset
                hue = (i * 10 + offset) % 360
                hex_color = hsl_to_hex(hue, 100, 50)
                await set_led(led_id, hex_color)
            
            # This makes the rainbow rotate!
            offset = (offset + 5) % 360
            
            # IMPORTANT: Put the sleep HERE, not inside the 'for' loop.
            # If it's inside the for loop, it will take 50 seconds to update the tower once!
            await asyncio.sleep(speed)
            
    except asyncio.CancelledError: 
        pass

rainbow_cycle.use_fader = False # Rainbows usually look better crisp!
rainbow_cycle.anim_speed = 0.05


async def rainbow_fall(set_led, set_led_multiple, color, speed):
    """
    Creates 4 distinct rings of color that blend into each other.
    The rings move vertically up the tower.
    """
    offset = 0
    num_rings = 4
    # Spacing determines how 'stretched' the rings are (360 / 4 rings = 90 degrees apart)
    spacing = 360 / num_rings 
    
    try:
        while True:
            for h, step_ids in enumerate(HEIGHTS):
                # 1. Calculate the hue for this specific 'ring' level
                # (h / 25) spreads one full 360 loop across the 25 pixels
                # multiplying by num_rings (4) creates the 4 distinct bands
                hue = (offset + (h / 25) * 360 * (num_rings / 4)) % 360
                
                current_hex = hsl_to_hex(hue, 100, 50)
                
                # 2. Update all 4 LEDs at this height simultaneously
                # This ensures the 'ring' is perfectly level across all sides
                await set_led_multiple(step_ids, current_hex)
            
            # 3. Shift the rings upward
            offset = (offset + 5) % 360
            await asyncio.sleep(speed)
            
    except asyncio.CancelledError:
        pass

rainbow_fall.anim_speed = 0.05

def rgb_to_hex_rainbow(r, g, b):
    """
    Converts 3 separate RGB floats/ints into a single Hex string.
    Added guards to ensure values stay between 0-255.
    """
    # Clamp values to 0-255 and convert to int
    r_int = max(0, min(255, int(r)))
    g_int = max(0, min(255, int(g)))
    b_int = max(0, min(255, int(b)))
    return '#{:02x}{:02x}{:02x}'.format(r_int, g_int, b_int)

async def rainbow_stationary(set_led, set_led_multiple, color, speed):
    """
    4 independent rings using RGB Vector Blending. 
    Corrected function signature to prevent TypeError.
    """
    t = 0
    try:
        while True:
            # 1. Generate 4 'Target' colors that pulse independently
            targets = []
            for i in range(4):
                phase = i * 2.0  # Spread the starting colors out
                r = 127.5 + 127.5 * math.sin(t * 0.3 + phase)
                g = 127.5 + 127.5 * math.sin(t * 0.5 + phase + 2)
                b = 127.5 + 127.5 * math.sin(t * 0.4 + phase + 4)
                targets.append((r, g, b))

            # 2. Vertical Blend using HEIGHTS global
            for h, step_ids in enumerate(HEIGHTS):
                # 25 rows / 4 zones = ~6.25 rows per zone
                raw_zone = h / 6.25 
                idx = int(raw_zone)
                idx_next = min(idx + 1, 3)
                blend = raw_zone - idx 

                # Linear Interpolation (LERP) between the two closest rings
                c1 = targets[idx]
                c2 = targets[idx_next]
                
                res_r = c1[0] + (c2[0] - c1[0]) * blend
                res_g = c1[1] + (c2[1] - c1[1]) * blend
                res_b = c1[2] + (c2[2] - c1[2]) * blend
                
                # Pass 3 separate arguments to match the new rgb_to_hex signature
                hex_color = rgb_to_hex_rainbow(res_r, res_g, res_b)
                await set_led_multiple(step_ids, hex_color)
            
            # Control the speed of the color 'morphing'
            t += 0.03 
            await asyncio.sleep(speed)
            
    except asyncio.CancelledError:
        pass

rainbow_stationary.anim_speed = 0.05


def rgb_to_hex_rainbow_rainbow(r, g, b):
    """Safety-clamped RGB to Hex converter."""
    r_int = max(0, min(255, int(r)))
    g_int = max(0, min(255, int(g)))
    b_int = max(0, min(255, int(b)))
    return '#{:02x}{:02x}{:02x}'.format(r_int, g_int, b_int)

def hex_to_rgb_tuple(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

async def rainbow_stationary_top_bottom(set_led, set_led_multiple, color, speed):
    """
    Two complementary rings (180° apart) using RGB Vector blending.
    This eliminates the 'Green Flash' caused by Hue-based math.
    """
    t = 0
    try:
        while True:
            # 1. Calculate the 'Anchor' Hue
            hue_base = (180 + 180 * math.sin(t * 0.2)) % 360
            
            # 2. Convert HSL to RGB for both Top and Bottom
            # Bottom is our base, Top is +180 (Opposite)
            rgb_bottom = hex_to_rgb_tuple(hsl_to_hex(hue_base, 100, 50))
            rgb_top = hex_to_rgb_tuple(hsl_to_hex((hue_base + 180) % 360, 100, 50))

            for h, step_ids in enumerate(HEIGHTS):
                # blend is 0.0 at bottom, 1.0 at top
                blend = h / 24.0 

                # 3. LERP (Linear Interpolation) in RGB space
                # This 'slides' the color from Bottom to Top without 
                # swinging around the color wheel into 'Green' territory.
                r = rgb_bottom[0] + (rgb_top[0] - rgb_bottom[0]) * blend
                g = rgb_bottom[1] + (rgb_top[1] - rgb_bottom[1]) * blend
                b = rgb_bottom[2] + (rgb_top[2] - rgb_bottom[2]) * blend
                
                await set_led_multiple(step_ids, rgb_to_hex_rainbow_rainbow(r, g, b))
            
            t += 0.03
            await asyncio.sleep(speed)
            
    except asyncio.CancelledError:
        pass

rainbow_stationary_top_bottom.anim_speed = 0.05

async def sparkle(set_led, set_led_multiple, color, speed):
    async def flash_pixel(p):
        await set_led(p, color)
        # How long the 'blink' lasts (half the speed)
        await asyncio.sleep(speed / 2) 
        await set_led(p, "#000000") # Turn it off

    try:
        while True:
            # Pick a random LED ID between 0 and 99
            led_id = random.randint(0, 99)
            
            # Light it up!
            asyncio.create_task(flash_pixel(led_id))
            
            # The 'speed' slider now controls how "dense" the sparkles are
            await asyncio.sleep(speed)
    except asyncio.CancelledError:
        pass
sparkle.use_fader = False
sparkle.fader_speed = 1
sparkle.animation_speed = 0.05

async def rising_ring(set_led, set_led_multiple, color, speed):
    try:
        while True:
            # Go Up (Floor 0 to 24)
            for floor in range(25):
                # Light up the corresponding LED on all 4 strips at once
                # Strip 1: floor
                # Strip 2: 49 - floor (because it's wired top-to-bottom)
                # Strip 3: 50 + floor
                # Strip 4: 99 - floor (because it's wired top-to-bottom)
                
                await set_led(floor, color)
                await set_led(49 - floor, color)
                await set_led(50 + floor, color)
                await set_led(99 - floor, color)
                
                await asyncio.sleep(speed * 2) # Slightly slower for the ring
            
            # Go Down (Floor 23 to 1)
            for floor in range(23, 0, -1):
                await set_led(floor, color)
                await set_led(49 - floor, color)
                await set_led(50 + floor, color)
                await set_led(99 - floor, color)
                
                await asyncio.sleep(speed * 2)
    except asyncio.CancelledError:
        pass


async def scanner(set_led, set_led_multiple, color, speed):
    try:
        while True:
            # The range(25) handles the height
            for floor in range(25):
                # We reuse the ring logic math
                await set_led(floor, color)
                await set_led(49 - floor, color)
                await set_led(50 + floor, color)
                await set_led(99 - floor, color)
                await asyncio.sleep(speed)

            for floor in range(23, 0, -1):
                await set_led(floor, color)
                await set_led(49 - floor, color)
                await set_led(50 + floor, color)
                await set_led(99 - floor, color)
                await asyncio.sleep(speed)
    except asyncio.CancelledError:
        pass


def hex_to_rgb(hex_str):
    """Converts #RRGGBB to (R, G, B) tuple"""
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    """Converts (R, G, B) tuple to #RRGGBB"""
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

async def scanner_fade_in(set_led, set_led_multiple, color, speed):
    try:
        base_rgb = hex_to_rgb(color)
        
        # FADE IN PHASE: Increase brightness over 50 steps
        for step in range(51):
            # Calculate brightness percentage (0.0 to 1.0)
            percentage = step / 50.0
            
            # Apply percentage to each RGB channel
            current_rgb = (
                int(base_rgb[0] * percentage),
                int(base_rgb[1] * percentage),
                int(base_rgb[2] * percentage)
            )
            current_hex = rgb_to_hex(current_rgb)
            
            # Briefly flash the "floor" logic to show the ring at current brightness
            # We'll just do one quick pulse at floor 0 to show the fade
            for i in [0, 49, 50, 99]:
                await set_led(i, current_hex)
            
            await asyncio.sleep(0.02) # Fast fade in (approx 1 second)

        # ANIMATION PHASE: Standard scanner loop
        while True:
            for floor in range(25):
                for i in [floor, 49 - floor, 50 + floor, 99 - floor]:
                    await set_led(i, color)
                await asyncio.sleep(speed)

            for floor in range(23, 0, -1):
                for i in [floor, 49 - floor, 50 + floor, 99 - floor]:
                    await set_led(i, color)
                await asyncio.sleep(speed)
                
    except asyncio.CancelledError:
        pass

def dim_color(hex_str, factor):
    """
    Takes a hex color like "#00ffee" and dims it by a factor (0.0 to 1.0).
    0.0 = Black, 1.0 = Full Brightness.
    """
    # 1. Remove the '#' and convert hex to RGB integers
    hex_str = hex_str.lstrip('#')
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)

    # 2. Apply the dimming factor and ensure they are valid integers
    r = int(max(0, min(255, r * factor)))
    g = int(max(0, min(255, g * factor)))
    b = int(max(0, min(255, b * factor)))

    # 3. Convert back to hex string
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

async def scanner_glow_ahead(set_led, set_led_multiple, color, speed):
    try:
        while True:
            # --- GOING UP ---
            # Range starts early so the scouts can "enter" the bottom of the stand
            for f in range(-4, 25):
                # 1. The Far Scout (3 steps ahead, 25% brightness)
                await set_floor(set_led, set_led_multiple, f + 3, dim_color(color, 0.10))
                
                # 2. The Mid Scout (2 steps ahead, 40% brightness)
                await set_floor(set_led, set_led_multiple, f + 2, dim_color(color, 0.30))
                
                # 3. The Near Scout (1 step ahead, 60% brightness)
                await set_floor(set_led, set_led_multiple, f + 1, dim_color(color, 0.70))
                
                # 4. The Lead Pixel (100% brightness)
                await set_floor(set_led, set_led_multiple, f, color)
                await set_floor(set_led, set_led_multiple, f - 1, dim_color(color, 0.70))
                await set_floor(set_led, set_led_multiple, f - 2, dim_color(color, 0.30))
                await set_floor(set_led, set_led_multiple, f - 3, dim_color(color, 0.10))
                
                # 5. Cleanup (Turn off the floor we just left)
                # await set_floor(set_led, set_led_multiple, f - 1, "#333")
                
                await asyncio.sleep(speed)

            # --- GOING DOWN ---
            for f in range(28, -5, -1):
                # When going down, "ahead" means subtracting from the floor
                await set_floor(set_led, set_led_multiple, f - 3, dim_color(color, 0.10))
                await set_floor(set_led, set_led_multiple, f - 2, dim_color(color, 0.30))
                await set_floor(set_led, set_led_multiple, f - 1, dim_color(color, 0.70))
                await set_floor(set_led, set_led_multiple, f, color)
                await set_floor(set_led, set_led_multiple, f + 1, dim_color(color, 0.70))
                await set_floor(set_led, set_led_multiple, f + 2, dim_color(color, 0.30))
                await set_floor(set_led, set_led_multiple, f + 3, dim_color(color, 0.10))
                
                # Cleanup (The floor above us)
                await set_floor(set_led, set_led_multiple, f + 1, "#333")
                
                await asyncio.sleep(speed)
    except asyncio.CancelledError:
        pass


async def set_floor(set_led, set_led_multiple, floor_height, color):
    """Lights up all 4 pillars at a specific height (0-24)"""
    if 0 <= floor_height < 25:
        ids = [
            floor_height,           # Pillar 0 (Up)
            49 - floor_height,      # Pillar 1 (Down)
            50 + floor_height,      # Pillar 2 (Up)
            99 - floor_height       # Pillar 3 (Down)
        ]
        for led_id in ids:
            await set_led(led_id, color)


async def scanner_glow_ahead(set_led, set_led_multiple, color, speed):
    try:
        offsets = [
            (3, 0.10), (2, 0.30), (1, 0.70), 
            (0, 1.0), 
            (-1, 0.70), (-2, 0.30), (-3, 0.10)
        ]
        
        pos = -4
        direction = 1
        
        while True:
            # 1. Update all LEDs in the "window" for this frame
            for offset, brightness in offsets:
                # We DON'T await these individually to prevent stutter
                # This prepares the 'frame'
                asyncio.create_task(set_floor(set_led, set_led_multiple, pos + offset, dim_color(color, brightness)))
            
            # 2. Clear the edges of the window
            asyncio.create_task(set_floor(set_led, set_led_multiple, pos - 4 if direction == 1 else pos + 4, "#333"))
            
            # 3. NOW we pause. This is the 'Frame Rate'
            await asyncio.sleep(speed)
            
            # 4. Move the position
            pos += direction
            
            # 5. Smooth Bounce Logic
            if pos >= 28:
                direction = -1
            elif pos <= -4:
                direction = 1
                
    except asyncio.CancelledError:
        pass


async def fire_flicker(set_led, set_led_multiple, color, speed):
    # We ignore the 'color' parameter and use fire colors: Red, Orange, Yellow
    fire_colors = ["#ff0000", "#ff4400", "#ff6600", "#ffaa00"]
    async def flash_pixel(p, colour):
        await set_led(p, colour)
        # How long the 'blink' lasts (half the speed)
        #await asyncio.sleep(speed / 2) 
        #await set_led(p, "#000000") # Turn it off
    
    try:
        while True:
            # Pick a random pillar and a random height near the bottom (0-8)
            pillar_base = random.choice([0, 25, 50, 75])
            height = random.randint(0, 24)
            
            # Serpentine adjustment for the random height
            # (Simplified for the flicker effect)
            led_id = pillar_base + height 
            
            # Pick a random fire color and 'pop' it
            asyncio.create_task(flash_pixel(led_id, random.choice(fire_colors)))
            
            # The 'speed' slider now controls how "dense" the sparkles are
            await asyncio.sleep(speed)

    except asyncio.CancelledError:
        pass

fire_flicker.use_fader = True
fire_flicker.fader_speed = 0.9
fire_flicker.animation_speed = 0.10


async def breathing_pulse(set_led, set_led_multiple, color, speed):
    try:
        while True:
            # Fade In
            for i in range(101):
                brightness = i / 100.0
                current_color = dim_color(color, brightness)
                for led_id in range(100):
                    await set_led(led_id, current_color)
                await asyncio.sleep(speed / 10)
            
            # Fade Out
            for i in range(100, -1, -1):
                brightness = i / 100.0
                current_color = dim_color(color, brightness)
                for led_id in range(100):
                    await set_led(led_id, current_color)
                await asyncio.sleep(speed / 10)
    except asyncio.CancelledError:
        pass

async def fire_tower(set_led, set_led_multiple, color, speed):
    """
    Simulates a fire at the base of the tower.
    Heat is strongest at the bottom and flickers towards the middle (floor 12).
    """
    try:
        # Fire colors from hottest (base) to coolest (middle)
        colors = ["#333", "#ff0000", "#ff4400", "#ffaa00", "#ffffff"]
        
        while True:
            # We only care about the bottom half of the tower (floors 0 to 14)
            for floor in range(15):
                # 1. Calculate base probability of a flame reaching this height
                # Higher floors have a lower chance of being lit
                chance = random.random()
                threshold = 0.8 - (floor * 0.05) # Diminishing returns as we go up
                
                if chance < threshold:
                    # 2. Pick a color based on height + a bit of randomness
                    # Bottom floors get whites/yellows, middle gets reds
                    color_idx = max(1, 4 - (floor // 3) - random.randint(0, 1))
                    flicker_color = colors[min(color_idx, 4)]
                    
                    # 3. Apply to all 4 pillars at once to keep the 'ring' feel
                    await set_floor(set_led, set_led_multiple, floor, flicker_color)
                else:
                    # 4. If the flame doesn't reach here, keep it dark
                    await set_floor(set_led, set_led_multiple, floor, "#333")
            
            # Ensure the top half of the tower stays dark
            for floor in range(15, 25):
                await set_floor(set_led, set_led_multiple, floor, "#333")

            # Speed slider controls the flicker rate
            await asyncio.sleep(speed * 2)
            
    except asyncio.CancelledError:
        pass
fire_tower.use_fader = True
fire_tower.fader_speed = 0.8
fire_tower.animation_speed = 0.10


async def startup_sequence(set_led, set_led_multiple, color, speed):
    """
    Sparkles for 3 seconds, then fades into 50% white.
    """
    try:
        # 1. SPARKLE PHASE (3 seconds)
        # We run roughly 60 frames of sparkles
        for _ in range(60):
            # Pick 3 random LEDs to "pop" white
            for _ in range(3):
                random_led = random.randint(0, 99)
                # Flash a random LED bright white
                asyncio.create_task(set_led(random_led, "#ffffff"))
            
            # Brief pause for the sparkle effect
            await asyncio.sleep(0.05)
            
            # The 'tail_fader' or your cleanup logic will handle 
            # turning these off, or we can do a quick dim:
            for _ in range(3):
                random_led = random.randint(0, 99)
                asyncio.create_task(set_led(random_led, "#333"))

        # 2. TRANSITION: Quick clear before the white fade
        for i in range(100):
            asyncio.create_task(set_led(i, "#333"))
        await asyncio.sleep(0.5)

        # 3. PLAIN WHITE FADE-IN (To 50%)
        for i in range(51):
            brightness = i / 100.0
            current_white = dim_color("#ffffff", brightness)
            for led_id in range(100):
                asyncio.create_task(set_led(led_id, current_white))
            await asyncio.sleep(0.04)

        # Hold the white light
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        pass


async def spinning_columns(set_led, set_led_multiple, color, speed):
    side_length = 25
    
    try:
        while True:
            # 1. Pick two NEW colors at the start of every full rotation
            hue_primary = random.randint(0, 360)
            hue_secondary = (hue_primary + 120) % 360
            
            color_a = hsl_to_hex(hue_primary, 100, 50)
            color_b = hsl_to_hex(hue_secondary, 100, 50)

            # 2. Perform one full rotation (Side 0 -> 1 -> 2 -> 3)
            for side_index in range(4):
                # Clear the previous "active" look by setting colors
                # based on which pair the current side belongs to
                for s in range(4):
                    # Determine which color this side should be
                    # Sides 0 & 2 (1 & 3) = Color A | Sides 1 & 3 (2 & 4) = Color B
                    current_side_color = color_a if s % 2 == 0 else color_b
                    
                    # Only highlight the "Active" side by making others dimmer, 
                    # or keep them solid if you want the "blade" look.
                    # For now, let's keep the pairs solid:
                    for h in range(side_length):
                        # Use our flip logic for sides 2 and 4 (indices 1 and 3)
                        pixel_id = s * side_length + ((side_length - 1 - h) if s % 2 == 1 else h)
                        await set_led(pixel_id, current_side_color)
                
                # This sleep controls how long it stays on each side
                await asyncio.sleep(speed)
                
    except asyncio.CancelledError:
        pass

# TAGS
spinning_columns.use_fader = False
spinning_columns.anim_speed = 0.2

async def spinning_columns_fade(set_led, set_led_multiple, color, speed):
    side_length = 25
    hue_primary = random.randint(0, 360)
    hue_secondary = (hue_primary + 180) % 360  # Opposite colors
    
    # Track which pair is currently active
    # Pair A: Sides 1 & 3 | Pair B: Sides 2 & 4
    active_pair = 'A'

    def get_id(h, s):
        base = s * side_length
        if s % 2 == 1: # Sides 2 and 4 (indices 1 and 3)
            return base + (side_length - 1 - h)
        return base + h

    try:
        while True:
            # 1. Select the colors for the current rotation
            color_a = hsl_to_hex(hue_primary, 100, 50)
            color_b = hsl_to_hex(hue_secondary, 100, 50)

            # 2. Flash the columns based on the active pair
            # We only "set" the pixels for the active pair; the fader handles the rest
            if active_pair == 'A':
                for h in range(side_length):
                    await set_led(get_id(h, 0), color_a)
                    await set_led(get_id(h, 2), color_a)
                active_pair = 'B' # Swap for next step
            else:
                for h in range(side_length):
                    await set_led(get_id(h, 1), color_b)
                    await set_led(get_id(h, 3), color_b)
                active_pair = 'A' # Swap for next step

            # 3. Check if we need to change the colors (every 2 steps = 1 full pair swap)
            # You can increase this number to make the colors stay longer
            if random.random() < 0.05: # 5% chance to shift colors every pulse
                hue_primary = (hue_primary + 30) % 360
                hue_secondary = (hue_primary + 180) % 360

            await asyncio.sleep(speed)
            
    except asyncio.CancelledError:
        pass

# TAGS
spinning_columns_fade.use_fader = True
spinning_columns_fade.fader_speed = 0.70  # Lower number = shorter "memory" of the previous column
spinning_columns_fade.anim_speed = 0.2    # Controls how fast the columns swap

def hsl_to_hex(h, s, l):
    # Convert HSL (0-360, 0-100, 0-100) to RGB (0-1)
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    # Convert RGB (0-1) to Hex (#rrggbb)
    return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
