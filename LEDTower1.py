import asyncio
import random
import colorsys
import math
import time

# --- 1. NETWORK & MAPPING SETUP ---
S1 = list(range(0, 25))
S2 = list(range(49, 24, -1)) # Physically upside down
S3 = list(range(50, 75))
S4 = list(range(99, 74, -1)) # Physically upside down

FULL_PATH = S1 + S2 + S3 + S4
HEIGHTS = [list(step) for step in zip(S1, S2, S3, S4)]
NUM_PIXELS = 100

# --- 2. COLOR HELPERS ---

def hsl_to_rgb(h, s, l):
    """Returns a (r, g, b) tuple 0-255."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return (int(r * 255), int(g * 255), int(b * 255))

def hex_to_rgb_tuple(hex_str):
    """Converts #RRGGBB to (R, G, B) tuple."""
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def color_wheel(pos):
    """Generates a smooth rainbow color based on a 0-255 position."""
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

def get_ring_indices(h):
    return [h, 49 - h, 50 + h, 99 - h]

# --- 3. ANIMATION LIBRARY ---

async def stop(set_led, set_led_multiple, color, speed):
    """Stops the animation: Instantly or with a randomized Power Down Dissolve."""
    all_ids = list(range(100))
    
    try:
        # 1. Grab attributes
        use_fader = getattr(stop, 'attr_bool_use_fader', True)
        fader_speed = getattr(stop, 'attr_int_fader_speed', 75)
        
        if not use_fader:
            # --- INSTANT OFF ---
            await set_led_multiple(all_ids, [(0, 0, 0)] * 100)
        else:
            # --- POWER DOWN DISSOLVE ---
            # Speed math: How many pixels turn off per frame (1 to 10)
            chunk_size = max(1, int(fader_speed / 10))
            # Speed math: How fast the frames update
            delay = max(0.02, 0.15 - (fader_speed * 0.001)) 
            
            # Create a list of all LEDs and shuffle them
            active_pixels = list(range(100))
            random.shuffle(active_pixels)
            
            # Fizzle them out a few at a time
            while active_pixels:
                to_turn_off = active_pixels[:chunk_size]
                active_pixels = active_pixels[chunk_size:] # Remove them from the active list
                
                await set_led_multiple(to_turn_off, [(0, 0, 0)] * len(to_turn_off))
                await asyncio.sleep(delay)
        
        # 2. The Holding Pattern
        # Once the tower is dark, we keep the task alive but sleeping 
        # so it doesn't instantly restart or exit.
        while True:
            await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        pass

# --- Attributes ---
stop.title = "Stop Animation"
stop.attr_bool_use_fader = True
stop.attr_int_fader_speed = 75

async def plain_white(set_led, set_led_multiple, color, speed):
    """Fades in the entire tower to 50% white."""
    all_ids = [lid for floor in HEIGHTS for lid in floor]
    white_array = [(255, 255, 255)] * 100
    brightness = 0
    try:
        while brightness <= 1:
            brightness += 0.01
            await set_led_multiple(all_ids, white_array, brightness=brightness)
            # Use the dynamic attribute for speed
            sleep_time = 0.11 - (getattr(plain_white, 'attr_step_speed', 5) * 0.01)
            await asyncio.sleep(max(0.01, sleep_time))
    except asyncio.CancelledError: pass

plain_white.title = "Plain White"
plain_white.attr_step_speed = 10

async def rainbow_stationary(set_led, set_led_multiple, color, speed):
    """4 independent morphing rings using RGB Vector Blending."""
    t = 0
    try:
        while True:
            targets = []
            for i in range(4):
                phase = i * 2.0
                r = 127.5 + 127.5 * math.sin(t * 0.3 + phase)
                g = 127.5 + 127.5 * math.sin(t * 0.5 + phase + 2)
                b = 127.5 + 127.5 * math.sin(t * 0.4 + phase + 4)
                targets.append((r, g, b))

            for h, step_ids in enumerate(HEIGHTS):
                raw_zone = h / 6.25 
                idx, idx_next = int(raw_zone), min(int(raw_zone) + 1, 3)
                blend = raw_zone - idx 
                c1, c2 = targets[idx], targets[idx_next]
                res_rgb = (
                    int(c1[0] + (c2[0] - c1[0]) * blend),
                    int(c1[1] + (c2[1] - c1[1]) * blend),
                    int(c1[2] + (c2[2] - c1[2]) * blend)
                )
                await set_led_multiple(step_ids, [res_rgb] * 4)
            
            t += 0.03 
            s_val = getattr(rainbow_stationary, 'attr_step_speed', 5)
            await asyncio.sleep(0.11 - (s_val * 0.01))
    except asyncio.CancelledError: pass

rainbow_stationary.title = "Rainbow"
rainbow_stationary.attr_step_speed = 5

async def fire_tower(set_led, set_led_multiple, color, speed):
    """Fire Tower"""
    
    # --- 🎨 COLOR THRESHOLDS 🎨 ---
    T_WHITE  = 240
    T_YELLOW = 200
    T_GOLD   = 135
    T_ORANGE = 80
    T_RED    = 35
    T_EMBER  = 5
    # ------------------------------

    heat = [0.0] * 25
    all_ids = [lid for floor in HEIGHTS for lid in floor]

    try:
        while True:
            # 1. LIVE MENU ATTRIBUTES 
            s_val = getattr(fire_tower, 'attr_step_speed', 8)       
            v_val = getattr(fire_tower, 'attr_step_velocity', 5)    
            step_height = getattr(fire_tower, 'attr_step_height', 5) 
            step_sparking = getattr(fire_tower, 'attr_step_sparking', 5) 
            
            # --- 📝 TEXT LIST LOGIC 📝 ---
            # We look for the user's saved choice. If they haven't picked one yet, 
            # we default to the first item in the list!
            theme_name = getattr(fire_tower, 'attr_list_theme_choice', fire_tower.attr_list_theme[0])

            h_scale = step_height * 10
            base_sparking = (step_sparking * 20) + 40
            pierce_chance = step_sparking * 0.05 
            drift_divisor = 2.25 - (v_val * 0.04)
            current_sparking = base_sparking + (max(0, h_scale - 80) * 2) + (v_val * 4)
            base_cooling = 85 - (h_scale * 0.75) 
            ceiling_floor = 4 + int(h_scale * 0.14) 

            for i in range(25):
                c_factor = (base_cooling / 20.0)
                if i < 3: c_factor *= 0.4 
                if i > ceiling_floor:
                    penalty = 4.5 - (h_scale * 0.02) - (step_sparking * 0.15)
                    c_factor += (i - ceiling_floor) * max(0.8, penalty)
                heat[i] = max(0, heat[i] - random.uniform(0, c_factor))

            for k in range(24, 2, -1):
                divisor = drift_divisor 
                if k > ceiling_floor:
                    if random.random() < pierce_chance: divisor = 1.5 
                    else: divisor = 3.2 - (step_sparking * 0.08) 
                heat[k] = (heat[k-1] + heat[k-2]) / divisor

                if k > ceiling_floor + 1:
                    heat[k] = min(heat[k], T_GOLD - 1)

            if random.randint(0, 255) < current_sparking:
                heat[0] = min(255, heat[0] + random.randint(150, 255))
                heat[1] = min(255, heat[1] + random.randint(80, 150))
            
            heat[0] = max(185, heat[0]) 
            heat[1] = max(145, heat[1]) 
            heat[2] = max(115, heat[2]) 

            # 6. TEXT THEME MAPPING
            frame_colors = []
            for i, h_val in enumerate(heat):
                r, g, b = 0, 0, 0
                multiplier = 1.0 if i <= ceiling_floor else 0.5

                if theme_name == "Classic Red": 
                    if h_val > T_WHITE:   r, g, b = 255, 255, 200 
                    elif h_val > T_YELLOW: r, g, b = 255, 220, 0   
                    elif h_val > T_GOLD:   r, g, b = 255, 140, 0   
                    elif h_val > T_ORANGE: r, g, b = 255, 60, 0    
                    elif h_val > T_RED:    r, g, b = 210, 0, 0     
                    elif h_val > T_EMBER:  r, g, b = int(h_val * 2.5), 0, 0 
                
                elif theme_name == "Ice Blue": 
                    if h_val > T_WHITE:   r, g, b = 180, 255, 255
                    elif h_val > T_YELLOW: r, g, b = 0, 200, 255
                    elif h_val > T_GOLD:   r, g, b = 0, 120, 255
                    elif h_val > T_ORANGE: r, g, b = 0, 40, 255
                    elif h_val > T_EMBER:  r, g, b = 0, 0, int(h_val * 2.0)

                elif theme_name == "Toxic Green": 
                    if h_val > T_WHITE:   r, g, b = 200, 255, 180
                    elif h_val > T_YELLOW: r, g, b = 150, 255, 0
                    elif h_val > T_GOLD:   r, g, b = 80, 255, 0
                    elif h_val > T_ORANGE: r, g, b = 20, 200, 0
                    elif h_val > T_EMBER:  r, g, b = 0, int(h_val * 2.0), 0
                
                elif theme_name == "Plasma Purple": 
                    if h_val > T_WHITE:   r, g, b = 255, 180, 255
                    elif h_val > T_YELLOW: r, g, b = 200, 0, 255
                    elif h_val > T_GOLD:   r, g, b = 140, 0, 220
                    elif h_val > T_ORANGE: r, g, b = 80, 0, 180
                    elif h_val > T_EMBER:  r, g, b = int(h_val * 1.2), 0, int(h_val * 1.5)

                final_color = (int(r * multiplier), int(g * multiplier), int(b * multiplier))
                frame_colors.extend([final_color] * 4)

            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(0.12 - (s_val * 0.01))

    except asyncio.CancelledError: pass

fire_tower.title = "Flame"
fire_tower.attr_step_speed = 8
fire_tower.attr_step_velocity = 5   
fire_tower.attr_step_height = 3   
fire_tower.attr_step_sparking = 3  
# NEW: The list of text options for the OLED menu!
fire_tower.attr_list_theme = ["Classic Red", "Ice Blue", "Toxic Green", "Plasma Purple"]

async def sparkle(set_led, set_led_multiple, color, speed):
    """Randomly pops pixels on/off."""
    if isinstance(color, str): color = hex_to_rgb_tuple(color)
    
    async def flash_pixel(p):
        s_val = getattr(sparkle, 'attr_step_speed', 5)
        local_speed = 0.11 - (s_val * 0.01)
        await set_led(p, color)
        await asyncio.sleep(local_speed / 2) 
        await set_led(p, (0, 0, 0))

    try:
        while True:
            s_val = getattr(sparkle, 'attr_step_speed', 5)
            asyncio.create_task(flash_pixel(random.randint(0, 99)))
            await asyncio.sleep(0.11 - (s_val * 0.01))
    except asyncio.CancelledError: pass

sparkle.title = "Sparkle"
sparkle.attr_step_speed = 5

async def startup_sequence(set_led, set_led_multiple, color, speed):
    num_pixels = 100
    all_ids = list(range(num_pixels))
    try:
        for h in range(25):
            frame_colors = [(0, 0, 0)] * num_pixels
            ring_color = color_wheel((h * 10) % 256) 
            for idx in get_ring_indices(h):
                frame_colors[idx] = ring_color
            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(0.04)

        for h in range(24, -1, -1):
            frame_colors = [(0, 0, 0)] * num_pixels
            ring_color = color_wheel((h * 10 + 128) % 256) 
            for idx in get_ring_indices(h):
                frame_colors[idx] = ring_color
            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(0.04)
    except asyncio.CancelledError: pass

async def matrix_rain(set_led, set_led_multiple, color, speed):
    """Matrix Rain: White heads for classic themes, pure color for Rainbow."""
    num_floors = 25
    num_cols = 4
    trails = [[0.0] * num_floors for _ in range(num_cols)]
    heads = [-1] * num_cols 
    
    drop_hues = [0] * num_cols 
    all_ids = list(range(100))

    def wheel(pos):
        pos = int(pos) % 256
        if pos < 85:
            return (255 - pos * 3, pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (0, 255 - pos * 3, pos * 3)
        else:
            pos -= 170
            return (pos * 3, 0, 255 - pos * 3)

    try:
        while True:
            # 1. Grab attributes
            s_val = getattr(matrix_rain, 'attr_step_speed', 7)
            density = getattr(matrix_rain, 'attr_step_density', 5)
            theme = getattr(matrix_rain, 'attr_list_theme_choice', 'Rainbow Rain')
            
            # 2. Physics Logic
            for col in range(num_cols):
                if heads[col] < 0:
                    if random.random() < (density * 0.05):
                        heads[col] = 24
                        drop_hues[col] = random.randint(0, 255)
                else:
                    heads[col] -= 1
                
                for f in range(num_floors):
                    trails[col][f] *= 0.65 
                    if heads[col] == f:
                        trails[col][f] = 1.0

            # 3. Optimized Color Mapping
            frame_colors = [(0, 0, 0)] * 100
            
            for col in range(num_cols):
                for f in range(num_floors):
                    b = trails[col][f]
                    if b < 0.1: continue 
                    
                    is_head = (f == heads[col])
                    
                    # --- RESTORED: White-hot heads for classic themes ---
                    if theme == "Code Green":
                        r, g, b_val = (200, 255, 200) if is_head else (0, 255, 0)
                    elif theme == "Cyber Red":
                        r, g, b_val = (255, 200, 200) if is_head else (255, 0, 0)
                    elif theme == "Deep Sea":
                        r, g, b_val = (200, 200, 255) if is_head else (0, 80, 255)
                    else: 
                        # --- KEPT: Pure color heads exclusively for Rainbow ---
                        current_hue = drop_hues[col] + (f * 3) 
                        r, g, b_val = wheel(current_hue)

                    final_rgb = (int(r * b), int(g * b), int(b_val * b))

                    # Map directly using your pre-flipped HEIGHTS map
                    led_id = HEIGHTS[f][col]
                    frame_colors[led_id] = final_rgb

            # 4. Update LEDs
            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(max(0.05, 0.2 - (s_val * 0.015)))

    except asyncio.CancelledError:
        pass

# --- Attributes ---
matrix_rain.title = "Matrix Rain"
matrix_rain.attr_step_speed = 7
matrix_rain.attr_step_density = 5
matrix_rain.attr_list_theme = ["Rainbow Rain", "Code Green", "Cyber Red", "Deep Sea"]


async def lava_lamp(set_led, set_led_multiple, color, speed):
    """Ambient Lava Lamp: Smooth, slow-moving blobs of color."""
    num_floors = 25
    num_cols = 4
    all_ids = list(range(100))

    try:
        while True:
            # 1. Grab attributes
            s_val = getattr(lava_lamp, 'attr_step_speed', 3)
            visc = getattr(lava_lamp, 'attr_step_viscosity', 5)
            theme = getattr(lava_lamp, 'attr_list_theme_choice', '70s Orange')
            
            # Setup colors based on theme (Background -> Lava Core)
            if theme == "70s Orange":
                bg = (40, 0, 0)
                lava = (255, 100, 0)
            elif theme == "Deep Space Violet":
                bg = (10, 0, 40)
                lava = (200, 0, 255)
            elif theme == "Oceanic":
                bg = (0, 10, 40)
                lava = (0, 200, 255)
            else: # Radioactive
                bg = (0, 20, 0)
                lava = (150, 255, 0)

            # 2. Time and Math Scaling
            # We use time to smoothly drive the sine waves upward
            t = time.time() * (s_val * 0.3)
            freq = 0.1 + (visc * 0.02) # Viscosity changes how "stretched" the blobs are

            frame_colors = [(0, 0, 0)] * 100
            
            # 3. Fluid Math
            for col in range(num_cols):
                # Offset each column slightly so the 4 sides don't look identical
                col_offset = col * 2.5 
                
                for f in range(num_floors):
                    # Combine two sine waves moving at different speeds to create
                    # the organic "blob splitting and merging" effect.
                    wave1 = math.sin((f * freq) - t + col_offset)
                    wave2 = math.sin((f * freq * 1.3) - (t * 0.7) + col_offset)
                    
                    # Normalize the result from roughly [-2, 2] to [0, 1]
                    combined = (wave1 + wave2 + 2) / 4.0
                    
                    # Apply a "power curve" to make distinct blobs instead of a soft wash
                    intensity = combined ** 3 
                    
                    # Interpolate between background and lava color
                    r = int(bg[0] + (lava[0] - bg[0]) * intensity)
                    g = int(bg[1] + (lava[1] - bg[1]) * intensity)
                    b_val = int(bg[2] + (lava[2] - bg[2]) * intensity)
                    
                    # Safety clamp to ensure we don't exceed max brightness
                    r = max(0, min(255, r))
                    g = max(0, min(255, g))
                    b_val = max(0, min(255, b_val))

                    # Map directly using your pre-flipped HEIGHTS map!
                    led_id = HEIGHTS[f][col]
                    frame_colors[led_id] = (r, g, b_val)

            # 4. Update LEDs
            await set_led_multiple(all_ids, frame_colors)
            
            # Lava lamps are slow! Keep the sleep generous to save CPU.
            await asyncio.sleep(0.05)

    except asyncio.CancelledError:
        pass

# --- Attributes ---
lava_lamp.title = "Lava Lamp"
lava_lamp.attr_step_speed = 3
lava_lamp.attr_step_viscosity = 5
lava_lamp.attr_list_theme = ["70s Orange", "Deep Space Violet", "Oceanic", "Radioactive"]

async def helix_spin(set_led, set_led_multiple, color, speed):
    """Helix Spin: True 3D rotation using smooth cosine waves to prevent gap flickering."""
    num_floors = 25
    num_cols = 4
    all_ids = list(range(100))

    try:
        while True:
            # 1. Grab attributes
            s_val = getattr(helix_spin, 'attr_step_speed', 5)
            width = getattr(helix_spin, 'attr_step_width', 5)  
            theme = getattr(helix_spin, 'attr_list_theme_choice', 'Bio-Green')
            
            if theme == "Bio-Green":
                c1, c2, bg = (0, 255, 50), (0, 100, 255), (0, 10, 0)
            elif theme == "Neon Barber":
                c1, c2, bg = (255, 0, 0), (255, 255, 255), (0, 0, 20)
            elif theme == "Ice Swirl":
                c1, c2, bg = (0, 200, 255), (200, 0, 255), (0, 0, 10)
            else: # Synthwave
                c1, c2, bg = (255, 0, 150), (0, 255, 255), (10, 0, 10)

            # 2. Time and Math Scaling
            t = time.time() * (s_val * 0.8)
            twist = 0.5  
            
            # Adjusted width factor so it pinches the light smoothly
            width_factor = 1.0 + ((10 - width) * 0.3) 

            frame_colors = [(0, 0, 0)] * 100
            
            # 3. True 3D Wrap-Around Math
            for f in range(num_floors):
                # Convert height and time into an angle (radians)
                angle1 = t + (f * twist)
                angle2 = angle1 + math.pi # Opposite side of the cylinder

                for col in range(num_cols):
                    # Each column is a 90-degree (pi/2) slice of the cylinder
                    col_angle = col * (math.pi / 2)
                    
                    # math.cos() gives us the perfect 3D distance (-1.0 to 1.0)
                    diff1 = math.cos(col_angle - angle1)
                    diff2 = math.cos(col_angle - angle2)
                    
                    # Ignore the negative side of the cylinder, and apply the width curve
                    b1 = max(0.0, diff1) ** width_factor
                    b2 = max(0.0, diff2) ** width_factor
                    
                    # Blend the colors together over the background
                    r = int((c1[0] * b1) + (c2[0] * b2) + bg[0])
                    g = int((c1[1] * b1) + (c2[1] * b2) + bg[1])
                    b_val = int((c1[2] * b1) + (c2[2] * b2) + bg[2])
                    
                    r = max(0, min(255, r))
                    g = max(0, min(255, g))
                    b_val = max(0, min(255, b_val))
                    
                    led_id = HEIGHTS[f][col]
                    frame_colors[led_id] = (r, g, b_val)

            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(0.05)

    except asyncio.CancelledError:
        pass

# --- Attributes ---
helix_spin.title = "Helix Spin"
helix_spin.attr_step_speed = 1
helix_spin.attr_step_width = 10
helix_spin.attr_list_theme = ["Bio-Green", "Neon Barber", "Ice Swirl", "Synthwave"]

__all__ = ['plain_white', "helix_spin", "lava_lamp", 'matrix_rain', 'sparkle', 'fire_tower', 'rainbow_stationary', 'stop']