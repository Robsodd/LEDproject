import asyncio
import random
import colorsys
import math

# --- 1. NETWORK & MAPPING SETUP ---
S1 = list(range(0, 25))
S2 = list(range(49, 24, -1)) # Physically upside down
S3 = list(range(50, 75))
S4 = list(range(99, 74, -1)) # Physically upside down

FULL_PATH = S1 + S2 + S3 + S4
HEIGHTS = [list(step) for step in zip(S1, S2, S3, S4)]
NUM_PIXELS = 100

# --- 2. COLOR HELPERS (RGB TUPLE FOCUS) ---

def hsl_to_rgb(h, s, l):
    """Returns a (r, g, b) tuple 0-255."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return (int(r * 255), int(g * 255), int(b * 255))

def hex_to_rgb_tuple(hex_str):
    """Converts #RRGGBB to (R, G, B) tuple."""
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

# --- 3. ANIMATION LIBRARY ---

async def stop(set_led, set_led_multiple, color, speed):

    return 
stop.anim_speed = 0.05
stop.use_fader = True
stop.fader_speed = 0.75
stop.title = "- Stop animation"

async def plain_white(set_led, set_led_multiple, color, speed):
    """Fades in the entire tower to 50% white."""
    all_ids = [lid for floor in HEIGHTS for lid in floor]
    white_array = [(255, 255, 255)] * 100
    brightness = 0
    try:
        while brightness <= 1:
            brightness = brightness + 0.01
            await set_led_multiple(all_ids, white_array, brightness=brightness)
            ##await asyncio.sleep(getattr(plain_white, 'anim_speed', 0.01))
    except asyncio.CancelledError: pass
    # 
    #     for i in range(50):
    #         brightness = (i * 5) / 100.0
    #         await set_led_multiple(all_ids, white_array, brightness=brightness)
    #         await asyncio.sleep(getattr(plain_white, 'anim_speed', 0.1))
    #     while True: await asyncio.sleep(0.5)
    #except asyncio.CancelledError: pass
plain_white.title = "- Plain white"
plain_white.anim_speed = 0.1

async def rising_ring(set_led, set_led_multiple, color, speed):
    """A single ring that bounces up and down the tower."""
    print("attempting rising ring")
    if isinstance(color, str): color = hex_to_rgb_tuple(color)
    on_colors = [color] * 4
    off_colors = [(0, 0, 0)] * 4
    print(off_colors)
    try:
        print("attempting rising ring")
        while True:
            cur_speed = getattr(rising_ring, 'anim_speed', speed)
            # UP
            for floor in range(25):
                await set_led_multiple(HEIGHTS[floor], on_colors)
                await asyncio.sleep(cur_speed * 2)

            # DOWN
            for floor in range(23, 0, -1):
                await set_led_multiple(HEIGHTS[floor], on_colors)
                await asyncio.sleep(cur_speed * 2)

    except asyncio.CancelledError:
        print(f"\n[ERROR] asyncio.CancelledError in Rising_ring animation:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Details: {e}")
        pass
    except Exception as e:
        print(f"\n[ERROR] Exception in Rising_ring animation:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Details: {e}")

rising_ring.anim_speed = 0.05
rising_ring.use_fader = True
rising_ring.fader_speed = 0.75
rising_ring.title = "- Rising Ring"

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
            await asyncio.sleep(getattr(rainbow_stationary, 'anim_speed', speed))
    except asyncio.CancelledError: pass

rainbow_stationary.title = "- Rainbow"

async def fire_tower(set_led, set_led_multiple, color, speed):
    """Hottest at base, flickers towards middle."""
    fire_palette = [(0,0,0), (255,0,0), (255,68,0), (255,170,0), (255,255,255)]
    all_ids = [lid for floor in HEIGHTS for lid in floor]
    try:
        while True:
            frame_colors = []
            for floor in range(25):
                if floor < 15:
                    threshold = 0.8 - (floor * 0.05)
                    if random.random() < threshold:
                        idx = max(1, 4 - (floor // 3) - random.randint(0, 1))
                        f_color = fire_palette[min(idx, 4)]
                    else: f_color = (10, 10, 10)
                else: f_color = (0, 0, 0)
                frame_colors.extend([f_color] * 4)
            
            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(getattr(fire_tower, 'animation_speed', speed))
    except asyncio.CancelledError: pass

fire_tower.title = "- Flame"


async def sparkle(set_led, set_led_multiple, color, speed):
    """Randomly pops pixels on/off."""
    if isinstance(color, str): color = hex_to_rgb_tuple(color)
    async def flash_pixel(p):
        await set_led(p, color)
        await asyncio.sleep(speed / 2) 
        await set_led(p, (0, 0, 0))

    try:
        while True:
            asyncio.create_task(flash_pixel(random.randint(0, 99)))
            await asyncio.sleep(speed)
    except asyncio.CancelledError: pass

sparkle.title = "- Sparkle"

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
    """
    Maps a height (0-24) to the correct 4 LEDs. 
    Accounts for strips 2 and 4 being wired upside down.
    """
    return [
        h,           # Strip 1: Bottom is 0
        49 - h,      # Strip 2: Bottom is 49
        50 + h,      # Strip 3: Bottom is 50
        99 - h       # Strip 4: Bottom is 99
    ]

async def startup_sequence(set_led, set_led_multiple, color, speed):
    """
    Sweeps a color-changing ring up and down the tower, 
    then fades into a permanent 50% white glow.
    """
    num_pixels = 100
    all_ids = list(range(num_pixels))
    
    try:
        # 1. UPWARD RING
        for h in range(25):
            frame_colors = [(0, 0, 0)] * num_pixels
            # Change color slightly as it moves up
            ring_color = color_wheel((h * 10) % 256) 
            
            for idx in get_ring_indices(h):
                frame_colors[idx] = ring_color
                
            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(0.04) # Speed of the upward sweep

        # 2. DOWNWARD RING
        # Step backward from top (24) down to bottom (0)
        for h in range(24, -1, -1):
            frame_colors = [(0, 0, 0)] * num_pixels
            # Continue shifting the color on the way down
            ring_color = color_wheel((h * 10 + 128) % 256) 
            
            for idx in get_ring_indices(h):
                frame_colors[idx] = ring_color
                
            await set_led_multiple(all_ids, frame_colors)
            await asyncio.sleep(0.04) # Speed of the downward sweep

    except asyncio.CancelledError:
        pass

# --- TAGS & EXPORTS ---
rainbow_stationary.anim_speed = 0.05

fire_tower.animation_speed = 0.02


__all__ = ['plain_white', 'sparkle', 'fire_tower', 'rainbow_stationary', 'rising_ring', 'stop']