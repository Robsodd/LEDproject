import board
import neopixel
import asyncio
import LEDTower1
import sys
import json
import os
import random # Added this for the dissolve transition!
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from gpiozero import RotaryEncoder, Button

# --- 1. Persistent Settings Logic ---
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "brightness": 0.3,
    "mainColor": [255, 255, 255],
    "animation_data": {},
    "last_anim": "" 
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                if "animation_data" not in data:
                    data["animation_data"] = {}
                if "last_anim" not in data:
                    data["last_anim"] = ""
                return data
        except: return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)

user_data = load_settings()

# --- 2. Hardware Config ---
PIXEL_PIN = board.D18
NUM_PIXELS = 100
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=user_data["brightness"], auto_write=False)

try:
    serial = i2c(port=1, address=0x3C)
    device = sh1106(serial) 
except Exception as e:
    print(f"OLED Error: {e}"); sys.exit(1)

encoder = RotaryEncoder(17, 27, wrap=True, max_steps=1000)
btn_select = Button(22)                    
btn_bottom = Button(25)                    

# --- 3. Reflection Helpers ---
def get_anim_settings(func):
    """Sniffs the function for attributes starting with 'attr_'."""
    keys = [attr for attr in dir(func) if attr.startswith("attr_") and not attr.endswith("_choice")]
    display = [k.replace('attr_', '').replace('list_', '').replace('bool_', '').replace('step_', '').replace('int_', '').replace('_', ' ').title() for k in keys]
    return keys, display + ["Global Brightness", "Back to List"]

# --- 4. State Variables ---
menu_mode = "MAIN" 
active_task = None
current_anim_name = ""
selected_anim_title = ""
live_menu_idx = 0
edit_attr_key = ""
edit_attr_name = ""
last_encoder_val = -1 

# --- 5. LED & Animation Logic ---
async def pi_set_led(led_id, color):
    try: pixels[led_id] = color; pixels.show()
    except: pass

async def pi_set_led_multiple(led_ids, color_array=None, brightness=1.0):
    try:
        if color_array is None: return
        for i, lid in enumerate(led_ids):
            if 0 <= lid < NUM_PIXELS:
                raw_color = color_array[i] if isinstance(color_array, (list, tuple)) and isinstance(color_array[0], (list, tuple)) else color_array
                pixels[lid] = tuple(int(c * brightness) for c in raw_color)
        pixels.show()
    except: pass

async def play_transition():
    """Reads the 'stop' settings and plays a dissolve effect between animations."""
    try:
        use_fader = getattr(LEDTower1.stop, 'attr_bool_use_fader', True)
        fader_speed = getattr(LEDTower1.stop, 'attr_int_fader_speed', 75)
        
        if not use_fader:
            pixels.fill((0, 0, 0))
            pixels.show()
            return

        chunk_size = max(1, int(fader_speed / 10))
        delay = max(0.01, 0.15 - (fader_speed * 0.001)) 
        
        active_ids = list(range(100))
        random.shuffle(active_ids)
        
        while active_ids:
            chunk = active_ids[:chunk_size]
            active_ids = active_ids[chunk_size:]
            
            for led_id in chunk:
                pixels[led_id] = (0, 0, 0)
            pixels.show()
            await asyncio.sleep(delay)
            
    except Exception as e:
        pixels.fill((0, 0, 0))
        pixels.show()

async def run_anim(name):
    global active_task, selected_anim_title, current_anim_name
    
    # 1. Gracefully stop current task and run transition
    if active_task: 
        active_task.cancel()
        try:
            await active_task
        except asyncio.CancelledError:
            pass
        
        await play_transition()
    
    # 2. Setup new animation
    current_anim_name = name
    func = getattr(LEDTower1, name)
    selected_anim_title = getattr(func, 'title', name.replace('_', ' ').title())
    
    if user_data.get("last_anim") != name:
        user_data["last_anim"] = name
        save_settings(user_data)

    if name not in user_data["animation_data"]:
        user_data["animation_data"][name] = {}

    saved = user_data["animation_data"][name]
    for key, val in saved.items():
        if hasattr(func, key): 
            original_attr = getattr(func, key)
            if isinstance(original_attr, list):
                setattr(func, key + "_choice", val)
            else:
                setattr(func, key, val)
    
    active_task = asyncio.create_task(func(pi_set_led, pi_set_led_multiple, tuple(user_data["mainColor"]), 0))

# --- 6. Hardware Loop ---
async def hardware_loop():
    global menu_mode, live_menu_idx, edit_attr_key, edit_attr_name, last_encoder_val
    
    anim_funcs = [f for f in LEDTower1.__all__]
    full_menu_display = [getattr(getattr(LEDTower1, f), 'title', f.title()) for f in anim_funcs] + ["EXIT"]

    while True:
        # --- MODE: MAIN MENU ---
        if menu_mode == "MAIN":
            idx = max(0, min(int(encoder.steps), len(full_menu_display) - 1))
            encoder.steps = idx 
            
            if idx != last_encoder_val:
                with canvas(device) as draw:
                    draw.text((5, 2), "ANIMATIONS", fill="white")
                    draw.line((0, 15, 128, 15), fill="white")
                    for i in range(-1, 2):
                        curr = idx + i
                        if 0 <= curr < len(full_menu_display):
                            prefix = "> " if i == 0 else "  "
                            draw.text((10, 30 + (i * 12)), f"{prefix}{full_menu_display[curr]}", fill="white")
                last_encoder_val = idx

            if btn_select.is_pressed:
                if full_menu_display[idx] == "EXIT":
                    pixels.fill((0,0,0)); pixels.show(); sys.exit(0)
                await run_anim(anim_funcs[idx])
                menu_mode = "ANIM_MENU"; encoder.steps = 0; last_encoder_val = -1
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        # --- MODE: ANIMATION SETTINGS ---
        elif menu_mode == "ANIM_MENU":
            func = getattr(LEDTower1, current_anim_name)
            attr_keys, display_options = get_anim_settings(func)
            
            idx = max(0, min(int(encoder.steps), len(display_options) - 1))
            encoder.steps = idx

            if idx != last_encoder_val:
                with canvas(device) as draw:
                    draw.text((5, 2), selected_anim_title.upper(), fill="white")
                    draw.line((0, 15, 128, 15), fill="white")
                    for i in range(-1, 2):
                        curr = idx + i
                        if 0 <= curr < len(display_options):
                            prefix = "> " if i == 0 else "  "
                            draw.text((10, 30 + (i * 12)), f"{prefix}{display_options[curr]}", fill="white")
                last_encoder_val = idx

            if btn_select.is_pressed:
                choice = display_options[idx]
                if choice == "Back to List":
                    menu_mode = "MAIN"; encoder.steps = 0; last_encoder_val = -1
                elif choice == "Global Brightness":
                    menu_mode = "LIVE_EDIT"; edit_attr_key = "GLOBAL_BRIGHT"; edit_attr_name = choice
                    encoder.steps = int(user_data["brightness"] * 10)
                else:
                    edit_attr_key = attr_keys[idx]
                    edit_attr_name = choice
                    menu_mode = "LIVE_EDIT"
                    val = getattr(func, edit_attr_key)
                    
                    if isinstance(val, list):
                        current_choice = getattr(func, edit_attr_key + "_choice", val[0])
                        try: encoder.steps = val.index(current_choice)
                        except: encoder.steps = 0
                    else:
                        encoder.steps = 1 if isinstance(val, bool) and val else (0 if isinstance(val, bool) else int(val))
                
                last_encoder_val = -1 
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        # --- MODE: EDITING A SETTING ---
        elif menu_mode == "LIVE_EDIT":
            is_bool = "bool" in edit_attr_key
            is_step_type = "step" in edit_attr_key or edit_attr_key == "GLOBAL_BRIGHT"
            is_list = "list" in edit_attr_key
            
            if is_list:
                options = getattr(getattr(LEDTower1, current_anim_name), edit_attr_key)
                idx = max(0, min(int(encoder.steps), len(options) - 1))
                encoder.steps = idx
                val = options[idx]
            elif is_bool: 
                val = (int(encoder.steps) % 2 != 0)