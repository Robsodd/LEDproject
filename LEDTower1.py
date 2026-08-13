import uasyncio as asyncio
import random
import math
import time
import colorsys

# --- Pre-calculated Sine Table (0-255) ---
SIN_TABLE = [math.sin(i * 2 * math.pi / 256) for i in range(256)]

def fast_sin(angle_rad):
    # Converts radians to an index in our 256-step table
    idx = int(angle_rad * 40.7436) % 256
    return SIN_TABLE[idx]

# --- 1. NETWORK & MAPPING SETUP ---
S1 = list(range(0, 25))
S2 = list(range(49, 24, -1)) 
S3 = list(range(50, 75))
S4 = list(range(99, 74, -1)) 

FULL_PATH = S1 + S2 + S3 + S4
HEIGHTS = [list(step) for step in zip(S1, S2, S3, S4)]
NUM_PIXELS = 100

# --- 2. MICROPYTHON FUNCTION WRAPPER ---
# This class wraps our locked MicroPython functions so they can hold our menu attributes!
class Anim:
    def __init__(self, func):
        self.func = func
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

# --- 3. COLOR HELPERS ---
def hex_to_rgb_tuple(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def color_wheel(pos):
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

# --- 4. ANIMATION LIBRARY ---

@Anim
async def stop(set_led, set_led_multiple, color, speed):
    """Stops the animation: Instantly or with a randomized Power Down Dissolve."""
    all_ids = list(range(100))
    try:
        use_fader = getattr(stop, 'attr_bool_use_fader', True)
        fader_speed = getattr(stop, 'attr_int_fader_speed', 75)
        
        if not use_fader:
            await set_led_multiple(all_ids, [(0, 0, 0)] * 100)
        else:
            chunk_size = max(1, int(fader_speed / 10))
            delay = max(0.02, 0.15 - (fader_speed * 0.001)) 
            
            active_pixels = list(range(100))
            random.shuffle(active_pixels)
            
            while active_pixels:
                to_turn_off = active_pixels[:chunk_size]
                active_pixels = active_pixels[chunk_size:] 
                await set_led_multiple(to_turn_off, [(0, 0, 0)] * len(to_turn_off))
                await asyncio.sleep(delay)
        
        while True:
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass

stop.title = "Stop Animation"
stop.attr_bool_use_fader = True
stop.attr_int_fader_speed = 75

@Anim
async def plain_white(set_led, set_led_multiple, color, speed):
    """Fades in the entire tower to 50% white."""
    all_ids = [lid for floor in HEIGHTS for lid in floor]
    white_array = [(255, 255, 255)] * 100
    brightness = 0
    try:
        while brightness <= 1:
            brightness += 0.01
            await set_led_multiple(all_ids, white_array, brightness=brightness)
            sleep_time = 0.11 - (getattr(plain_white, 'attr_step_speed', 5) * 0.01)
            await asyncio.sleep(max(0.01, sleep_time))
    except asyncio.CancelledError: pass

plain_white.title = "Plain White"
plain_white.attr_step_speed = 10

@Anim
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

@Anim
async def fire_tower(set_led, set_led_multiple, color, speed):
    """Fire Tower"""
    T_WHITE  = 240
    T_YELLOW = 200
    T_GOLD   = 135
    T_ORANGE = 80
    T_RED    = 35
    T_EMBER  = 5

    heat = [0.0] * 25
    all_ids = [lid for floor in HEIGHTS for lid in floor]

    try:
        while True:
            s_val = getattr(fire_tower, 'attr_step_speed', 8)       
            v_val = getattr(fire_tower, 'attr_step_velocity', 5)    
            step_height = getattr(fire_tower, 'attr_step_height', 5) 
            step_sparking = getattr(fire_tower, 'attr_step_sparking', 5) 
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
fire_tower.attr_list_theme = ["Classic Red", "Ice Blue", "Toxic Green", "Plasma Purple"]

@Anim
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

@Anim
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

@Anim
async def matrix_rain(set_led, set_led_multiple, color, speed):
    """Matrix Rain"""
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
            s_val = getattr(matrix_rain, 'attr_step_speed', 7)
            density = getattr(matrix_rain, 'attr_step_density', 5)
            theme = getattr(matrix_rain, 'attr_list_theme_choice', 'Rainbow Rain')
            
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

            frame_colors = [(0, 0, 0)] * 100
            
            for col in range(num_cols):
                for f in range(num_floors):
                    b = trails[col][f]
                    if b < 0.1: continue 
                    
                    is_head = (f == heads[col])
                    
                    if theme == "Code Green":
                        r, g, b_val = (200, 255, 200) if is_head else (0, 255, 0)
                    elif theme == "Cyber Red":
                        r, g, b_val = (255, 200, 200) if is_head else (255, 0, 0)
                    elif theme == "Deep Sea":
                        r, g, b_val = (200, 200, 255) if is_head else (0, 80, 255)
                    else: 
                        current_hue = drop_hues[col] + (f * 3) 
                        r, g, b_val = wheel(current_hue)

                    final_rgb = (int(r * b), int(g * b), int(b_val * b))
                    led_id = HEIGHTS[f][col]
                    frame_colors[led_id] = final_rgb

            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(max(0.05, 0.2 - (s_val * 0.015)))

    except asyncio.CancelledError:
        pass

matrix_rain.title = "Matrix Rain"
matrix_rain.attr_step_speed = 7
matrix_rain.attr_step_density = 5
matrix_rain.attr_list_theme = ["Rainbow Rain", "Code Green", "Cyber Red", "Deep Sea"]

@Anim
async def lava_lamp(set_led, set_led_multiple, color, speed):
    all_ids = list(range(100))
    # Pre-allocate static frame buffer to avoid garbage collection churn
    frame_colors = [(0, 0, 0)] * 100
    
    # Cache local attributes outside the tight loop
    last_s_val = -1
    last_visc = -1
    last_theme = ""
    bg, lava = (40, 0, 0), (255, 100, 0)
    freq = 0.1
    
    try:
        while True:
            # Only pull config changes if needed, or keep it lightweight
            s_val = getattr(lava_lamp, 'attr_step_speed', 3)
            visc = getattr(lava_lamp, 'attr_step_viscosity', 5)
            theme = getattr(lava_lamp, 'attr_list_theme_choice', '70s Orange')
            
            # Update theme colors only when theme changes
            if theme != last_theme:
                last_theme = theme
                if theme == "70s Orange": bg, lava = (40, 0, 0), (255, 100, 0)
                elif theme == "Deep Space Violet": bg, lava = (10, 0, 40), (200, 0, 255)
                elif theme == "Oceanic": bg, lava = (0, 10, 40), (0, 200, 255)
                else: bg, lava = (0, 20, 0), (150, 255, 0)

            if visc != last_visc:
                last_visc = visc
                freq = 0.1 + (visc * 0.02)

            t = time.time() * (s_val * 0.3)
            
            bg_r, bg_g, bg_b = bg
            lr_r, lr_g, lr_b = lava
            r_diff = lr_r - bg_r
            g_diff = lr_g - bg_g
            b_diff = lr_b - bg_b

            for col in range(4):
                col_offset = col * 2.5 
                col_base = col * 25
                for f in range(25):
                    w1 = fast_sin((f * freq) - t + col_offset)
                    w2 = fast_sin((f * freq * 1.3) - (t * 0.7) + col_offset)
                    
                    intensity = ((w1 + w2 + 2) * 0.25) ** 3
                    
                    led_id = HEIGHTS[f][col]
                    frame_colors[led_id] = (
                        int(bg_r + r_diff * intensity),
                        int(bg_g + g_diff * intensity),
                        int(bg_b + b_diff * intensity)
                    )

            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(0) # Yield control immediately without artificial lag
    except asyncio.CancelledError:
        pass

lava_lamp.title = "Lava Lamp"
lava_lamp.attr_step_speed = 3
lava_lamp.attr_step_viscosity = 5
lava_lamp.attr_list_theme = ["70s Orange", "Deep Space Violet", "Oceanic", "Radioactive"]

@Anim
async def helix_spin(set_led, set_led_multiple, color, speed):
    """Helix Spin"""
    num_floors = 25
    num_cols = 4
    all_ids = list(range(100))

    try:
        while True:
            s_val = getattr(helix_spin, 'attr_step_speed', 5)
            width = getattr(helix_spin, 'attr_step_width', 5)  
            theme = getattr(helix_spin, 'attr_list_theme_choice', 'Bio-Green')
            
            if theme == "Bio-Green":
                c1, c2, bg = (0, 255, 50), (0, 100, 255), (0, 10, 0)
            elif theme == "Neon Barber":
                c1, c2, bg = (255, 0, 0), (255, 255, 255), (0, 0, 20)
            elif theme == "Ice Swirl":
                c1, c2, bg = (0, 200, 255), (200, 0, 255), (0, 0, 10)
            else: 
                c1, c2, bg = (255, 0, 150), (0, 255, 255), (10, 0, 10)

            t = time.time() * (s_val * 0.8)
            twist = 0.5  
            width_factor = 1.0 + ((10 - width) * 0.3) 

            frame_colors = [(0, 0, 0)] * 100
            
            for f in range(num_floors):
                angle1 = t + (f * twist)
                angle2 = angle1 + math.pi 

                for col in range(num_cols):
                    col_angle = col * (math.pi / 2)
                    diff1 = math.cos(col_angle - angle1)
                    diff2 = math.cos(col_angle - angle2)
                    
                    b1 = max(0.0, diff1) ** width_factor
                    b2 = max(0.0, diff2) ** width_factor
                    
                    r = int((c1[0] * b1) + (c2[0] * b2) + bg[0])
                    g = int((c1[1] * b1) + (c2[1] * b2) + bg[1])
                    b_val = int((c1[2] * b1) + (c2[2] * b2) + bg[2])
                    
                    r, g, b_val = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b_val))
                    
                    led_id = HEIGHTS[f][col]
                    frame_colors[led_id] = (r, g, b_val)

            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(0.05)

    except asyncio.CancelledError:
        pass

helix_spin.title = "Helix Spin"
helix_spin.attr_step_speed = 1
helix_spin.attr_step_width = 10
helix_spin.attr_list_theme = ["Bio-Green", "Neon Barber", "Ice Swirl", "Synthwave"]

@Anim
async def champagne(set_led, set_led_multiple, main_color, speed):
    """Champagne bubbles"""
    def get_pixel(x, y):
        if x % 2 != 0: return (x * 25) + (24 - y)
        else: return (x * 25) + y

    bubbles = []
    try:
        while True:
            spawn_rate = getattr(champagne, 'attr_int_spawn_rate', 4)
            move_speed = getattr(champagne, 'attr_step_speed', 5)
            palette = getattr(champagne, 'attr_list_color_palette_choice', "Classic Gold")
            
            if random.randint(1, 10) <= spawn_rate:
                col = random.randint(0, 3)
                velocity = random.uniform(0.1, 0.4) * move_speed 
                bubbles.append({'x': col, 'y': 0.0, 'speed': velocity})
                
            for b in bubbles:
                b['y'] += b['speed'] 
                if random.randint(1, 100) > 90:
                    direction = random.choice([-1, 1])
                    b['x'] = max(0, min(3, b['x'] + direction))
                    
            bubbles = [b for b in bubbles if b['y'] < 24.5]
            frame_colors = [(0, 0, 0)] * 100
            
            for b in bubbles:
                px_idx = get_pixel(int(b['x']), int(b['y']))
                if 0 <= px_idx < 100:
                    if palette == "Classic Gold": c = (255, 170, 40)
                    elif palette == "Deep Ocean": c = (0, 150, 255)
                    elif palette == "White Frost": c = (255, 255, 255)
                    else: c = random.choice([(255, 0, 100), (0, 255, 200), (150, 0, 255)])
                    frame_colors[px_idx] = c
                    
            await set_led_multiple(list(range(100)), frame_colors)
            await asyncio.sleep(0.04)
    except asyncio.CancelledError:
        pass

champagne.title = "Champagne"
champagne.attr_int_spawn_rate = 4
champagne.attr_step_speed = 5
champagne.attr_list_color_palette = ["Classic Gold", "Deep Ocean", "White Frost", "Synthwave"]

@Anim
async def sunrise(set_led, set_led_multiple, main_color, speed):
    """Sunrise"""
    start_time = time.time()
    SKY_STOPS = [(0.00, (0,0,0)), (0.20, (5,0,15)), (0.50, (30,10,50)), (0.80, (80,50,120)), (1.00, (120,180,255))]
    SUN_STOPS = [(0.00, (0,0,0)), (0.15, (150,0,0)), (0.40, (255,10,0)), (0.70, (255,35,0)), (0.90, (255,65,0)), (1.00, (255,90,0))]
    
    def get_color(stops, p):
        p = max(0.0, min(1.0, p))
        for i in range(len(stops)-1):
            if stops[i][0] <= p <= stops[i+1][0]:
                span = stops[i+1][0] - stops[i][0]
                local_p = (p - stops[i][0]) / span
                c1, c2 = stops[i][1], stops[i+1][1]
                return (
                    int(c1[0] + (c2[0] - c1[0]) * local_p),
                    int(c1[1] + (c2[1] - c1[1]) * local_p),
                    int(c1[2] + (c2[2] - c1[2]) * local_p)
                )
        return stops[-1][1]

    all_ids = list(range(100))
    tower_heights = globals().get('HEIGHTS', [])
    
    try:
        while True:
            mins = getattr(sunrise, 'attr_int_duration_mins', 15)
            fast_test = getattr(sunrise, 'attr_bool_fast_test_mode', False)
            
            duration_sec = 30.0 if fast_test else (mins * 60.0)
            elapsed = time.time() - start_time
            progress = min(1.0, elapsed / duration_sec)
            
            sun_y = progress * 12.0 
            core_radius = progress * 10.5 
            fade_distance = 2.0 
            
            sky_c = get_color(SKY_STOPS, progress)
            sun_c = get_color(SUN_STOPS, progress)
            
            frame = [(0, 0, 0)] * 100
            
            if tower_heights:
                for f in range(25):
                    dist = abs(f - sun_y)
                    if dist <= core_radius: intensity = 1.0
                    else: intensity = max(0.0, 1.0 - ((dist - core_radius) / fade_distance))
                    
                    r = int((sun_c[0] * intensity) + (sky_c[0] * (1.0 - intensity)))
                    g = int((sun_c[1] * intensity) + (sky_c[1] * (1.0 - intensity)))
                    b = int((sun_c[2] * intensity) + (sky_c[2] * (1.0 - intensity)))
                    
                    master_dim = min(1.0, progress * 10)
                    final_c = (int(r * master_dim), int(g * master_dim), int(b * master_dim))
                    
                    if f < len(tower_heights):
                        for lid in tower_heights[f]:
                            if 0 <= lid < 100:
                                frame[lid] = final_c
                        
            await set_led_multiple(all_ids, frame)
            
            if progress >= 1.0: await asyncio.sleep(1.0)
            else: await asyncio.sleep(0.05)
                
    except asyncio.CancelledError:
        pass

sunrise.title = "Sunrise Alarm"
sunrise.attr_int_duration_mins = 15
sunrise.attr_bool_fast_test_mode = True

__all__ = ['plain_white', 'sunrise', "champagne", "helix_spin", "lava_lamp", 'matrix_rain', 'sparkle', 'fire_tower', 'rainbow_stationary', 'stop']