import asyncio
import random

# Added 'rainbow_cycle' for fun!
__all__ = ['scanner_glow_ahead', 'scanner_glow_ahead', 'scanner_fade_in', 'scanner', 'comet_chase', 'bounce_effect', 'pulse_sync', 'rainbow_cycle', 'stop', 'sparkle', 'rising_ring']

def get_path():
    s1 = list(range(0, 25))
    s2 = list(range(49, 24, -1))
    s3 = list(range(50, 75))
    s4 = list(range(99, 74, -1))
    return s1 + s2 + s3 + s4

async def stop(set_led, color, speed):
    # The fader in the HTML will handle the cleanup
    return 

async def comet_chase(set_led, color, speed):
    path = get_path()
    try:
        for led_id in path:
            await set_led(led_id, color)
            await asyncio.sleep(speed)
    except asyncio.CancelledError: pass

async def bounce_effect(set_led, color, speed):
    path = get_path()
    try:
        full_path = path + list(reversed(path))
        for led_id in full_path:
            await set_led(led_id, color)
            await asyncio.sleep(speed)
    except asyncio.CancelledError: pass

async def pulse_sync(set_led, color, speed):
    try:
        while True:
            for i in range(100): await set_led(i, color)
            await asyncio.sleep(speed * 10)
    except asyncio.CancelledError: pass

async def rainbow_cycle(set_led, color, speed):
    path = get_path()
    try:
        while True:
            for i, led_id in enumerate(path):
                hue = (i * 10) % 360
                await set_led(led_id, f"hsl({hue}, 100%, 50%)")
                await asyncio.sleep(speed)
    except asyncio.CancelledError: pass


async def sparkle(set_led, color, speed):
    try:
        while True:
            # Pick a random LED ID between 0 and 99
            led_id = random.randint(0, 99)
            
            # Light it up!
            await set_led(led_id, color)
            
            # The 'speed' slider now controls how "dense" the sparkles are
            await asyncio.sleep(speed)
    except asyncio.CancelledError:
        pass


async def rising_ring(set_led, color, speed):
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


async def scanner(set_led, color, speed):
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

async def scanner_fade_in(set_led, color, speed):
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

async def scanner_glow_ahead(set_led, color, speed):
    try:
        while True:
            # --- GOING UP ---
            # Range starts early so the scouts can "enter" the bottom of the stand
            for f in range(-4, 25):
                # 1. The Far Scout (3 steps ahead, 25% brightness)
                await set_floor(set_led, f + 3, dim_color(color, 0.10))
                
                # 2. The Mid Scout (2 steps ahead, 40% brightness)
                await set_floor(set_led, f + 2, dim_color(color, 0.30))
                
                # 3. The Near Scout (1 step ahead, 60% brightness)
                await set_floor(set_led, f + 1, dim_color(color, 0.70))
                
                # 4. The Lead Pixel (100% brightness)
                await set_floor(set_led, f, color)
                await set_floor(set_led, f - 1, dim_color(color, 0.70))
                await set_floor(set_led, f - 2, dim_color(color, 0.30))
                await set_floor(set_led, f - 3, dim_color(color, 0.10))
                
                # 5. Cleanup (Turn off the floor we just left)
                # await set_floor(set_led, f - 1, "#333")
                
                await asyncio.sleep(speed)

            # --- GOING DOWN ---
            for f in range(28, -5, -1):
                # When going down, "ahead" means subtracting from the floor
                await set_floor(set_led, f - 3, dim_color(color, 0.10))
                await set_floor(set_led, f - 2, dim_color(color, 0.30))
                await set_floor(set_led, f - 1, dim_color(color, 0.70))
                await set_floor(set_led, f, color)
                await set_floor(set_led, f + 1, dim_color(color, 0.70))
                await set_floor(set_led, f + 2, dim_color(color, 0.30))
                await set_floor(set_led, f + 3, dim_color(color, 0.10))
                
                # Cleanup (The floor above us)
                await set_floor(set_led, f + 1, "#333")
                
                await asyncio.sleep(speed)
    except asyncio.CancelledError:
        pass

async def set_floor(set_led, floor_height, color):
    """Bridge to light all 4 pillars at a specific height safely"""
    if 0 <= floor_height < 25:
        # This handles the serpentine math for you!
        ids = [floor_height, 49 - floor_height, 50 + floor_height, 99 - floor_height]
        for led_id in ids:
            await set_led(led_id, color)

async def set_floor(set_led, floor_height, color):
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


async def scanner_glow_ahead(set_led, color, speed):
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
                asyncio.create_task(set_floor(set_led, pos + offset, dim_color(color, brightness)))
            
            # 2. Clear the edges of the window
            asyncio.create_task(set_floor(set_led, pos - 4 if direction == 1 else pos + 4, "#333"))
            
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