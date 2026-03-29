import board
import neopixel
import asyncio
import LEDTower1
import sys
import json
import os
import random
import time
from datetime import datetime
from PIL import ImageFont
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
                if "animation_data" not in data: data["animation_data"] = {}
                if "last_anim" not in data: data["last_anim"] = ""
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

# --- 2b. Load Local Project Fonts ---
try:
    font_time = ImageFont.truetype("DejaVuSans.ttf", 24)
    font_date = ImageFont.truetype("DejaVuSans.ttf", 12)
except Exception as e:
    font_time = ImageFont.load_default()
    font_date = ImageFont.load_default()

encoder = RotaryEncoder(17, 27, wrap=True, max_steps=1000)
btn_select = Button(22)                    
btn_bottom = Button(25)                    

# --- 3. State Variables ---
menu_mode = "MAIN" 
active_task = None
active_fade_task = None
current_anim_name = ""
selected_anim_title = ""
live_menu_idx = 0
edit_attr_key = ""
edit_attr_name = ""
last_encoder_val = -1 

# --- TIMER GLOBALS ---
timer_active = False
timer_end_time = 0
timer_duration_sec = 0
timer_mode = "SLEEP" 
timer_task_ref = None

# Multi-stage timer setup variables
timer_edit_stage = 0 
timer_h = 0
timer_m = 0
timer_s = 0
alarm_anim_target = ""
alarm_theme_target = ""
TIMER_MODES = ["SLEEP", "HOURGLASS", "ALARM"]

def get_anim_settings(func):
    keys = [attr for attr in dir(func) if attr.startswith("attr_") and not attr.endswith("_choice")]
    display = [k.replace('attr_', '').replace('list_', '').replace('bool_', '').replace('step_', '').replace('int_', '').replace('_', ' ').title() for k in keys]
    return keys, display + ["Global Brightness", "Back to List"]

# --- 4. LED & Animation Logic ---
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

async def fade_in_routine(target_b):
    try:
        steps = 20
        for i in range(1, steps + 1):
            pixels.brightness = (i / steps) * target_b
            pixels.show()
            await asyncio.sleep(0.04)
        pixels.brightness = target_b
        pixels.show()
    except asyncio.CancelledError:
        pixels.brightness = target_b
        pixels.show()

async def play_transition():
    try:
        use_fader = getattr(LEDTower1.stop, 'attr_bool_use_fader', True)
        fader_speed = getattr(LEDTower1.stop, 'attr_int_fader_speed', 75)
        if not use_fader:
            pixels.fill((0, 0, 0)); pixels.show()
            return

        chunk_size = max(1, int(fader_speed / 10))
        delay = max(0.01, 0.15 - (fader_speed * 0.001)) 
        active_ids = list(range(100))
        random.shuffle(active_ids)
        
        while active_ids:
            chunk = active_ids[:chunk_size]
            active_ids = active_ids[chunk_size:]
            for led_id in chunk: pixels[led_id] = (0, 0, 0)
            pixels.show()
            await asyncio.sleep(delay)
    except Exception as e:
        pixels.fill((0, 0, 0)); pixels.show()

# --- 5. TIMER BACKGROUND TASK ---
async def timer_manager():
    global timer_active, active_task, active_fade_task
    try:
        if timer_mode == "SLEEP":
            start_b = user_data["brightness"]
            while time.time() < timer_end_time and timer_active:
                remaining = timer_end_time - time.time()
                progress = remaining / timer_duration_sec
                pixels.brightness = start_b * max(0.01, progress)
                pixels.show()
                await asyncio.sleep(1)
            
            if timer_active:
                if active_task: active_task.cancel()
                pixels.fill((0,0,0)); pixels.show()
                timer_active = False

        elif timer_mode == "HOURGLASS":
            if active_task: active_task.cancel()
            if active_fade_task: active_fade_task.cancel()
            pixels.brightness = user_data["brightness"]
            
            while time.time() < timer_end_time and timer_active:
                remaining = timer_end_time - time.time()
                progress = remaining / timer_duration_sec 
                
                floors_lit = max(0, min(25, int(25 * progress)))
                frame = [(0,0,0)] * 100
                
                for f in range(floors_lit):
                    for lid in LEDTower1.HEIGHTS[f]:
                        frame[lid] = (255, 140, 0) 
                        
                for i, c in enumerate(frame): pixels[i] = c
                pixels.show()
                await asyncio.sleep(0.5)
                
            if timer_active:
                pixels.fill((255,0,0)); pixels.show() 
                await asyncio.sleep(2)
                pixels.fill((0,0,0)); pixels.show()
                timer_active = False

        elif timer_mode == "ALARM":
            # FIX: We let the alarm wait quietly without killing the active animation!
            while time.time() < timer_end_time and timer_active:
                await asyncio.sleep(1)
                
            if timer_active:
                timer_active = False
                if alarm_anim_target:
                    func = getattr(LEDTower1, alarm_anim_target)
                    t_key = next((k for k in ['attr_list_theme', 'attr_list_color_palette', 'attr_list_color_theme'] if hasattr(func, k)), None)
                    
                    # FIX: Inject the target theme into the persistent save data 
                    # so run_anim doesn't accidentally overwrite it with the old save!
                    if t_key and alarm_theme_target:
                        if alarm_anim_target not in user_data["animation_data"]:
                            user_data["animation_data"][alarm_anim_target] = {}
                        user_data["animation_data"][alarm_anim_target][t_key] = alarm_theme_target
                        save_settings(user_data)
                        
                    await run_anim(alarm_anim_target) 
                else:
                    await run_anim('champagne') 
    except asyncio.CancelledError:
        pass

def start_the_timer():
    global timer_active, timer_end_time, timer_task_ref
    timer_end_time = time.time() + timer_duration_sec
    timer_active = True
    if timer_task_ref: timer_task_ref.cancel()
    timer_task_ref = asyncio.create_task(timer_manager())

def cancel_timer():
    global timer_active, timer_task_ref
    if timer_active:
        timer_active = False
        if timer_task_ref: timer_task_ref.cancel()
        pixels.brightness = user_data["brightness"]

async def run_anim(name):
    global active_task, selected_anim_title, current_anim_name, active_fade_task
    
    if timer_active and timer_mode == "HOURGLASS":
        cancel_timer() 
    
    if active_fade_task:
        active_fade_task.cancel()
        pixels.brightness = user_data["brightness"]
        
    if active_task: 
        active_task.cancel()
        try: await active_task
        except asyncio.CancelledError: pass
        await play_transition()
    
    target_brightness = user_data["brightness"]
    pixels.brightness = 0.0 
    
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
            if isinstance(original_attr, list): setattr(func, key + "_choice", val)
            else: setattr(func, key, val)
    
    active_task = asyncio.create_task(func(pi_set_led, pi_set_led_multiple, tuple(user_data["mainColor"]), 0))
    active_fade_task = asyncio.create_task(fade_in_routine(target_brightness))

# --- 6. Hardware Loop ---
async def hardware_loop():
    global menu_mode, live_menu_idx, edit_attr_key, edit_attr_name, last_encoder_val
    global timer_active, timer_duration_sec, timer_end_time, timer_mode, timer_task_ref
    global timer_edit_stage, timer_h, timer_m, timer_s, alarm_anim_target, alarm_theme_target

    last_interaction_time = time.time()
    is_screensaver = False
    screensaver_timeout = 30.0  
    last_drawn_second = -1
    last_encoder_steps = int(encoder.steps)

    while True:
        current_time = time.time()
        current_steps = int(encoder.steps)

        # --- 1. DETECT ACTIVITY ---
        activity_detected = False
        if current_steps != last_encoder_steps:
            activity_detected = True; last_encoder_steps = current_steps
        if btn_select.is_pressed or btn_bottom.is_pressed:
            activity_detected = True

        if activity_detected:
            last_interaction_time = current_time
            if is_screensaver:
                is_screensaver = False; last_encoder_val = -1 

        if not is_screensaver and (current_time - last_interaction_time > screensaver_timeout):
            if menu_mode != "TIMER_SETUP":
                is_screensaver = True; last_drawn_second = -1 

        # --- 2. SCREENSAVER UI MODE ---
        if is_screensaver:
            now = datetime.now()
            if now.second != last_drawn_second:
                with canvas(device) as draw:
                    if timer_active:
                        time_str = now.strftime("%H:%M")
                        rem = max(0, timer_end_time - time.time())
                        hours, rem = divmod(int(rem), 3600)
                        mins, secs = divmod(rem, 60)
                        
                        draw.text((25, 0), time_str, font=font_time, fill="white")
                        draw.text((8, 30), f"{hours:02d}:{mins:02d}:{secs:02d}", font=font_time, fill="white")
                    else:
                        time_str = now.strftime("%H:%M:%S")
                        date_str = now.strftime("%d %b %Y")
                        draw.text((10, 10), time_str, font=font_time, fill="white")
                        draw.text((32, 42), date_str, font=font_date, fill="white")
                last_drawn_second = now.second
            await asyncio.sleep(0.05)
            continue 

        # --- MODE: MAIN MENU ---
        if menu_mode == "MAIN":
            anim_funcs = [f for f in LEDTower1.__all__ if f != "stop"]
            timer_text = "CANCEL TIMER" if timer_active else "NEW TIMER"
            full_menu_display = [getattr(getattr(LEDTower1, f), 'title', f.title()) for f in anim_funcs] + [timer_text, "SOFT REBOOT", "REBOOT PI", "SHUTDOWN PI"]

            idx = max(0, min(int(encoder.steps), len(full_menu_display) - 1))
            encoder.steps = idx 
            
            if idx != last_encoder_val:
                with canvas(device) as draw:
                    draw.text((5, 2), "MAIN MENU", fill="white")
                    draw.line((0, 15, 128, 15), fill="white")
                    for i in range(-1, 2):
                        curr = idx + i
                        if 0 <= curr < len(full_menu_display):
                            prefix = "> " if i == 0 else "  "
                            draw.text((10, 30 + (i * 12)), f"{prefix}{full_menu_display[curr]}", fill="white")
                last_encoder_val = idx

            if btn_select.is_pressed:
                choice = full_menu_display[idx]
                if choice == "NEW TIMER":
                    menu_mode = "TIMER_SETUP"
                    timer_edit_stage = 0
                    timer_h, timer_m, timer_s = 0, 0, 0
                    encoder.steps = 0
                    last_encoder_val = -1
                elif choice == "CANCEL TIMER":
                    cancel_timer()
                    last_encoder_val = -1
                elif choice == "SOFT REBOOT":
                    pixels.fill((0,0,0)); pixels.show(); sys.exit(0)
                elif choice == "REBOOT PI":
                    cancel_timer()
                    if active_task: active_task.cancel()
                    pixels.fill((0,0,0)); pixels.show()
                    with canvas(device) as draw: draw.text((25, 25), "REBOOTING...", fill="white")
                    os.system("sudo reboot"); sys.exit(0)
                elif choice == "SHUTDOWN PI":
                    cancel_timer()
                    if active_task: active_task.cancel()
                    pixels.fill((0,0,0)); pixels.show()
                    with canvas(device) as draw:
                        draw.text((15, 20), "SHUTTING DOWN...", fill="white")
                        draw.text((15, 40), "Safe to unplug", fill="white")
                    os.system("sudo shutdown -h now"); sys.exit(0)
                else:
                    await run_anim(anim_funcs[idx])
                    menu_mode = "ANIM_MENU"; encoder.steps = 0; last_encoder_val = -1
                
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        # --- MODE: FLASHING TIMER SETUP ---
        elif menu_mode == "TIMER_SETUP":
            if timer_edit_stage == 0:
                val = max(0, min(99, int(encoder.steps)))
                timer_h = val
            elif timer_edit_stage == 1:
                val = max(0, min(59, int(encoder.steps)))
                timer_m = val
            elif timer_edit_stage == 2:
                val = max(0, min(59, int(encoder.steps)))
                timer_s = val
                
            encoder.steps = val
            
            blink_on = (int(time.time() * 2) % 2 == 0)

            with canvas(device) as draw:
                draw.text((5, 2), "SET DURATION", fill="white")
                draw.line((0, 15, 128, 15), fill="white")
                
                if timer_edit_stage != 0 or blink_on:
                    draw.text((2, 25), f"{timer_h:02d}", font=font_time, fill="white")
                draw.text((36, 25), ":", font=font_time, fill="white")
                
                if timer_edit_stage != 1 or blink_on:
                    draw.text((46, 25), f"{timer_m:02d}", font=font_time, fill="white")
                draw.text((80, 25), ":", font=font_time, fill="white")
                
                if timer_edit_stage != 2 or blink_on:
                    draw.text((90, 25), f"{timer_s:02d}", font=font_time, fill="white")
                    
                labels = ["HOURS", "MINUTES", "SECONDS"]
                draw.text((40, 52), labels[timer_edit_stage], fill="white")
                
            last_encoder_val = val
            
            if btn_select.is_pressed:
                if timer_edit_stage < 2:
                    timer_edit_stage += 1
                    if timer_edit_stage == 1: encoder.steps = timer_m
                    if timer_edit_stage == 2: encoder.steps = timer_s
                else:
                    timer_duration_sec = (timer_h * 3600) + (timer_m * 60) + timer_s
                    if timer_duration_sec > 0:
                        menu_mode = "TIMER_MODE"
                    else:
                        menu_mode = "MAIN"
                    encoder.steps = 0
                    
                last_encoder_val = -1
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        # --- MODE: TIMER MODE SETUP ---
        elif menu_mode == "TIMER_MODE":
            idx = max(0, min(2, int(encoder.steps)))
            encoder.steps = idx
            
            if idx != last_encoder_val:
                with canvas(device) as draw:
                    draw.text((5, 2), "TIMER ACTION", fill="white")
                    draw.line((0, 15, 128, 15), fill="white")
                    for i in range(-1, 2):
                        curr = idx + i
                        if 0 <= curr < len(TIMER_MODES):
                            prefix = "> " if i == 0 else "  "
                            draw.text((10, 30 + (i * 12)), f"{prefix}{TIMER_MODES[curr]}", fill="white")
                last_encoder_val = idx
                
            if btn_select.is_pressed:
                timer_mode = TIMER_MODES[idx]
                if timer_mode == "ALARM":
                    menu_mode = "TIMER_ALARM_ANIM"
                    encoder.steps = 0
                else:
                    start_the_timer()
                    menu_mode = "MAIN"
                    encoder.steps = 0
                
                last_encoder_val = -1
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        # --- MODE: ALARM ANIMATION SELECT ---
        elif menu_mode == "TIMER_ALARM_ANIM":
            anims = [f for f in LEDTower1.__all__ if f not in ['stop', 'plain_white']]
            idx = max(0, min(len(anims)-1, int(encoder.steps)))
            encoder.steps = idx
            
            if idx != last_encoder_val:
                with canvas(device) as draw:
                    draw.text((5, 2), "WAKE WITH?", fill="white")
                    draw.line((0, 15, 128, 15), fill="white")
                    draw.text((10, 30), f"> {getattr(getattr(LEDTower1, anims[idx]), 'title', anims[idx].title())}", fill="white")
                last_encoder_val = idx
                
            if btn_select.is_pressed:
                alarm_anim_target = anims[idx]
                func = getattr(LEDTower1, alarm_anim_target)
                
                t_key = next((k for k in ['attr_list_theme', 'attr_list_color_palette', 'attr_list_color_theme'] if hasattr(func, k)), None)
                if t_key:
                    menu_mode = "TIMER_ALARM_THEME"
                    encoder.steps = 0
                else:
                    alarm_theme_target = ""
                    start_the_timer()
                    menu_mode = "MAIN"
                    
                last_encoder_val = -1
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        # --- MODE: ALARM THEME SELECT ---
        elif menu_mode == "TIMER_ALARM_THEME":
            func = getattr(LEDTower1, alarm_anim_target)
            t_key = next(k for k in ['attr_list_theme', 'attr_list_color_palette', 'attr_list_color_theme'] if hasattr(func, k))
            themes = getattr(func, t_key)
            
            idx = max(0, min(len(themes)-1, int(encoder.steps)))
            encoder.steps = idx
            
            if idx != last_encoder_val:
                with canvas(device) as draw:
                    draw.text((5, 2), "SELECT THEME", fill="white")
                    draw.line((0, 15, 128, 15), fill="white")
                    draw.text((10, 30), f"> {themes[idx]}", fill="white")
                last_encoder_val = idx
                
            if btn_select.is_pressed:
                alarm_theme_target = themes[idx]
                start_the_timer()
                menu_mode = "MAIN"
                last_encoder_val = -1
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
                    edit_attr_key = attr_keys[idx]; edit_attr_name = choice; menu_mode = "LIVE_EDIT"
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
            elif is_bool: val = (int(encoder.steps) % 2 != 0)
            elif is_step_type: val = max(1, min(10, int(encoder.steps))); encoder.steps = val
            else: val = max(1, min(100, int(encoder.steps))); encoder.steps = val

            if val != last_encoder_val:
                with canvas(device) as draw:
                    draw.text((5, 5), f"EDIT: {edit_attr_name}", fill="white")
                    draw.line((0, 15, 128, 15), fill="white")

                    if is_list:
                        for i in range(-1, 2):
                            curr_opt_idx = idx + i
                            if 0 <= curr_opt_idx < len(options):
                                prefix = "> " if i == 0 else "  "
                                draw.text((10, 32 + (i * 12)), f"{prefix}{options[curr_opt_idx]}", fill="white")
                    elif is_bool:
                        status = "ON" if val else "OFF"
                        draw.rectangle((30, 30, 90, 50), outline="white", fill="white" if val else "black")
                        draw.text((50, 35), status, fill="black" if val else "white")
                    else:
                        bar_w = val * 10 if is_step_type else val
                        draw.rectangle((10, 35, 10 + bar_w, 45), outline="white", fill="white")
                        draw.text((10, 50), f"Value: {val}", fill="white")
                
                last_encoder_val = val
                if edit_attr_key == "GLOBAL_BRIGHT":
                    user_data["brightness"] = val / 10.0
                    pixels.brightness = user_data["brightness"]; pixels.show()
                elif is_list: setattr(getattr(LEDTower1, current_anim_name), edit_attr_key + "_choice", val)
                else: setattr(getattr(LEDTower1, current_anim_name), edit_attr_key, val)

            if btn_select.is_pressed:
                if current_anim_name not in user_data["animation_data"]: user_data["animation_data"][current_anim_name] = {}
                if edit_attr_key != "GLOBAL_BRIGHT": user_data["animation_data"][current_anim_name][edit_attr_key] = val
                save_settings(user_data)
                menu_mode = "ANIM_MENU"; last_encoder_val = -1
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        # --- OFF BUTTON ---
        if btn_bottom.is_pressed:
            if timer_active and timer_mode != "ALARM":
                cancel_timer()
                
            if active_fade_task: active_fade_task.cancel(); pixels.brightness = user_data["brightness"]
            if active_task: 
                active_task.cancel()
                try: await active_task
                except asyncio.CancelledError: pass
            
            await play_transition() 
            menu_mode = "MAIN"; last_encoder_val = -1; encoder.steps = 0
            while btn_bottom.is_pressed: await asyncio.sleep(0.1)
            
        await asyncio.sleep(0.05)

async def main():
    saved_anim = user_data.get("last_anim", "")
    if saved_anim and hasattr(LEDTower1, saved_anim): await run_anim(saved_anim)
    elif LEDTower1.__all__: await run_anim(LEDTower1.__all__[0])
    await hardware_loop()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt:
        pixels.fill((0,0,0)); pixels.show()