import asyncio
import random

# Added 'rainbow_cycle' for fun!
__all__ = ['plain_white', 'fire_tower', 'breathing_pulse', 'fire_flicker', 'scanner_glow_ahead', 'scanner_glow_ahead', 'scanner_fade_in', 'scanner', 'comet_chase', 'bounce_effect', 'pulse_sync', 'rainbow_cycle', 'stop', 'sparkle', 'rising_ring']

def get_path():
    s1 = list(range(0, 25))
    s2 = list(range(49, 24, -1))
    s3 = list(range(50, 75))
    s4 = list(range(99, 74, -1))
    return s1 + s2 + s3 + s4

async def stop(set_led, color, speed):
    # The fader in the HTML will handle the cleanup
    return 

async def plain_white(set_led, color, speed):
    """
    Fades in the entire tower to a steady white light at 50% brightness.
    """
    try:
        # Step 1: Fade In
        # We move from 0% to 50% in 50 steps
        for i in range(51):
            brightness = i / 100.0  # Current brightness (0.00 to 0.50)
            current_white = dim_color("#ffffff", brightness)
            
            # Update all 100 LEDs
            for led_id in range(100):
                # We don't 'await' every single LED to keep it fast
                asyncio.create_task(set_led(led_id, current_white))
            
            # The speed of the fade (0.04 * 50 steps = 2 second fade)
            await asyncio.sleep(0.04)

        # Step 2: Hold
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        # Optional: You could add a Fade Out here if you wanted!
        pass

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


async def fire_flicker(set_led, color, speed):
    # We ignore the 'color' parameter and use fire colors: Red, Orange, Yellow
    fire_colors = ["#ff0000", "#ff4400", "#ff6600", "#ffaa00"]
    
    try:
        while True:
            # Pick a random pillar and a random height near the bottom (0-8)
            pillar_base = random.choice([0, 25, 50, 75])
            height = random.randint(0, 8)
            
            # Serpentine adjustment for the random height
            # (Simplified for the flicker effect)
            led_id = pillar_base + height 
            
            # Pick a random fire color and 'pop' it
            await set_led(led_id, random.choice(fire_colors))
            
            # The speed slider controls how "intense" the fire is
            await asyncio.sleep(speed)
    except asyncio.CancelledError:
        pass


async def breathing_pulse(set_led, color, speed):
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

async def fire_tower(set_led, color, speed):
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
                    await set_floor(set_led, floor, flicker_color)
                else:
                    # 4. If the flame doesn't reach here, keep it dark
                    await set_floor(set_led, floor, "#333")
            
            # Ensure the top half of the tower stays dark
            for floor in range(15, 25):
                await set_floor(set_led, floor, "#333")

            # Speed slider controls the flicker rate
            await asyncio.sleep(speed * 2)
            
    except asyncio.CancelledError:
        pass



async def startup_sequence(set_led, color, speed):
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