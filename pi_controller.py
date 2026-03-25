import board
import neopixel
import asyncio
import LEDTower1
import sys
import json
import os
import signal
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from gpiozero import RotaryEncoder, Button

# --- 1. Persistent Settings Logic ---
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "brightness": 0.3,
    "mainColor": [255, 255, 255],
    "speed": 5 # Default speed (1-10)
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                # Ensure older settings files get the new speed key
                if "speed" not in data:
                    data["speed"] = 5
                return data
        except:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)

user_data = load_settings()

# --- 2. Hardware & LED Config ---
PIXEL_PIN = board.D18
NUM_PIXELS = 100
pixels = neopixel.NeoPixel(
    PIXEL_PIN, 
    NUM_PIXELS, 
    brightness=user_data["brightness"], 
    auto_write=False
)

# --- 3. OLED & Input Config ---
try:
    serial = i2c(port=1, address=0x3C)
    device = sh1106(serial)
except Exception as e:
    print(f"OLED Error: {e}")
    sys.exit(1)

encoder = RotaryEncoder(17, 27, wrap=True) 
btn_select = Button(22)                    
btn_top = Button(23, hold_time=3) 
btn_bottom = Button(25)                    

# --- 4. Global State & Dynamic Menu ---
animation_display_names = []
animation_func_names = []

for func_name in LEDTower1.__all__:
    func = getattr(LEDTower1, func_name)
    title = getattr(func, 'title', func_name.replace('_', ' ').title())
    animation_display_names.append(title)
    animation_func_names.append(func_name)

# Submenu Lists
settings_options = ["Change Color", "Brightness", "Animation Speed", "Back"]
system_options = ["Reboot Pi", "Shutdown Pi", "Back"]

# Main Menu Lists
full_menu_display = animation_display_names + ["Global Settings", "System Settings", "EXIT"]
full_menu_actions = animation_func_names + ["Global Settings", "System Settings", "EXIT"]

current_selection = 0
menu_mode = "MAIN" # MAIN, SETTINGS_MENU, COLOR, BRIGHTNESS, SPEED, SYSTEM
active_task = None
fader_active = False
current_fader_decay = 0.75

# --- 5. UI Rendering ---
def draw_ui(title, current_idx, options_list):
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="black")
        draw.text((10, 5), title.upper(), fill="white")
        draw.line((5, 18, 123, 18), fill="white")
        
        for i in range(-1, 2):
            idx = (current_idx + i) % len(options_list)
            prefix = "> " if i == 0 else "  "
            y_pos = 34 + (i * 12)
            draw.text((15, y_pos), f"{prefix}{options_list[idx]}", fill="white")

# --- 6. Core Logic Functions ---
def system_shutdown():
    pixels.fill((0,0,0))
    pixels.show()
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white")
        draw.text((20, 25), "SHUTTING DOWN...", fill="white")
    os.system("sudo shutdown -h now")

btn_top.when_held = system_shutdown

async def pi_set_led(led_id, color):
    try:
        pixels[led_id] = color
        pixels.show()
    except:
        pass

async def pi_set_led_multiple(led_ids, color_array=None, brightness=1.0):
    try:
        if color_array is None: return
        for i, lid in enumerate(led_ids):
            if 0 <= lid < NUM_PIXELS:
                if isinstance(color_array, (list, tuple)) and isinstance(color_array[0], (list, tuple)):
                    raw_color = color_array[i] if i < len(color_array) else color_array[-1]
                else:
                    raw_color = color_array
                
                if isinstance(raw_color, str):
                    c = raw_color.lstrip('#')
                    raw_color = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
                
                pixels[lid] = tuple(int(c * brightness) for c in raw_color)
        pixels.show()
    except Exception as e:
        print(f"LED Error: {e}")

async def auto_fader_loop():
    while True:
        if fader_active:
            pixels[:] = [(int(r*current_fader_decay), int(g*current_fader_decay), int(b*current_fader_decay)) for r,g,b in pixels]
            pixels.show()
        await asyncio.sleep(0.04)

async def handle_main_menu(selection):
    global menu_mode, active_task, fader_active, current_fader_decay
    
    if selection == "EXIT":
        pixels.fill((0,0,0))
        pixels.show()
        device.clear()
        sys.exit(0)
    elif selection == "Global Settings":
        menu_mode = "SETTINGS_MENU"
        encoder.steps = 0
    elif selection == "System Settings":
        menu_mode = "SYSTEM"
        encoder.steps = 0
    else:
        # Run Animation
        if active_task and not active_task.done():
            active_task.cancel()
            try: await active_task
            except asyncio.CancelledError: pass
        
        effect_func = getattr(LEDTower1, selection)
        fader_active = getattr(effect_func, 'use_fader', False)
        current_fader_decay = getattr(effect_func, 'fader_speed', 0.75)
        
        # Calculate speed delay (1 = 0.10s, 10 = 0.01s)
        delay = 0.11 - (user_data["speed"] * 0.01)
        
        active_task = asyncio.create_task(
            effect_func(pi_set_led, pi_set_led_multiple, tuple(user_data["mainColor"]), delay)
        )

last_rendered_level = -1

async def hardware_loop():
    global current_selection, menu_mode, last_rendered_level
    while True:
        if menu_mode == "MAIN":
            current_selection = int(encoder.steps) % len(full_menu_display)
            draw_ui("Animations", current_selection, full_menu_display)
            if btn_select.is_pressed:
                await handle_main_menu(full_menu_actions[current_selection])
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        elif menu_mode == "SETTINGS_MENU":
            set_idx = int(encoder.steps) % len(settings_options)
            draw_ui("Global Settings", set_idx, settings_options)
            if btn_select.is_pressed:
                choice = settings_options[set_idx]
                if choice == "Change Color":
                    menu_mode = "COLOR"
                    encoder.steps = 0
                elif choice == "Brightness":
                    menu_mode = "BRIGHTNESS"
                    encoder.steps = int(user_data["brightness"] * 10)
                elif choice == "Animation Speed":
                    menu_mode = "SPEED"
                    encoder.steps = user_data["speed"]
                elif choice == "Back":
                    menu_mode = "MAIN"
                    encoder.steps = 0
                while btn_select.is_pressed: await asyncio.sleep(0.1)
        
        elif menu_mode == "COLOR":
            colors = ["Red", "Green", "Blue", "White", "Purple", "Gold", "BACK"]
            color_idx = int(encoder.steps) % len(colors)
            draw_ui("Select Color", color_idx, colors)
            if btn_select.is_pressed:
                choice = colors[color_idx]
                if choice != "BACK":
                    color_map = {"Red":[255,0,0], "Green":[0,255,0], "Blue":[0,0,255], "White":[255,255,255], "Purple":[128,0,128], "Gold":[255,215,0]}
                    user_data["mainColor"] = color_map[choice]
                    save_settings(user_data)
                menu_mode = "SETTINGS_MENU" # Return to sub-menu
                encoder.steps = 0
                while btn_select.is_pressed: await asyncio.sleep(0.1)
        elif menu_mode == "BRIGHTNESS":
            level = max(1, min(10, int(encoder.steps)))
            if level != last_rendered_level:
                pixels.brightness = level / 10.0
                pixels.show()
                last_rendered_level = level # Update the tracker
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="white", fill="black")
                draw.text((15, 10), "BRIGHTNESS", fill="white")
                draw.rectangle((20, 35, 20 + (level * 8), 45), outline="white", fill="white")
                draw.text((105, 35), f"{level * 10}%", fill="white")
            if btn_select.is_pressed:
                user_data["brightness"] = level / 10.0
                pixels.brightness = user_data["brightness"]
                save_settings(user_data)
                menu_mode = "SETTINGS_MENU" # Return to sub-menu
                encoder.steps = 0
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        elif menu_mode == "SPEED":
            level = max(1, min(10, int(encoder.steps)))
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="white", fill="black")
                draw.text((15, 10), "GLOBAL SPEED", fill="white")
                draw.rectangle((20, 35, 20 + (level * 8), 45), outline="white", fill="white")
                draw.text((105, 35), f"{level}", fill="white")
            if btn_select.is_pressed:
                user_data["speed"] = level
                save_settings(user_data)
                menu_mode = "SETTINGS_MENU" # Return to sub-menu
                encoder.steps = 0
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        elif menu_mode == "SYSTEM":
            sys_idx = int(encoder.steps) % len(system_options)
            draw_ui("System Settings", sys_idx, system_options)
            if btn_select.is_pressed:
                choice = system_options[sys_idx]
                if choice == "Back":
                    menu_mode = "MAIN"
                    encoder.steps = 0
                elif choice == "Reboot Pi":
                    os.system("sudo reboot")
                elif choice == "Shutdown Pi":
                    system_shutdown()
                while btn_select.is_pressed: await asyncio.sleep(0.1)

        if btn_bottom.is_pressed:
            if active_task: active_task.cancel()
            pixels.fill((0,0,0)); pixels.show()
            while btn_bottom.is_pressed: await asyncio.sleep(0.1)

        await asyncio.sleep(0.05)

async def main():
    global active_task, fader_active
    
    delay = 0.11 - (user_data["speed"] * 0.01)
    
    # 1. Start the fader loop in the background
    asyncio.create_task(auto_fader_loop())
    
    # 2. Run the startup sequence and WAIT for it to finish
    fader_active = True
    await LEDTower1.startup_sequence(pi_set_led, pi_set_led_multiple, tuple(user_data["mainColor"]), delay)
    
    # 3. Once startup is done, launch plain_white as the new active background task
    fader_active = False
    active_task = asyncio.create_task(
        LEDTower1.plain_white(pi_set_led, pi_set_led_multiple, tuple(user_data["mainColor"]), delay)
    )
    
    # 4. Start the menu listener
    await hardware_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pixels.fill((0,0,0)); pixels.show()
        sys.exit(0)