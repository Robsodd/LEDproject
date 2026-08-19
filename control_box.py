import machine
import uasyncio as asyncio
import ujson as json
import uos as os
import time
import sys
import network
import espnow
import LEDTower1

# --- OTA Configuration (No Passwords Here) ---
MANIFEST_URL = "https://raw.githubusercontent.com/Robsodd/LEDproject/main/manifest.json"

# --- 1. Persistent Settings Logic ---
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "brightness": 0.3,
    "mainColor": [255, 255, 255],
    "animation_data": {},
    "last_anim": "",
    "wifi_ssid": "",
    "wifi_pass": "",
    "screen_flipped": False
}

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            # Ensure new keys exist if loading an older settings file
            for k, v in DEFAULT_SETTINGS.items():
                if k not in data:
                    data[k] = v
            return data
    except OSError:
        return DEFAULT_SETTINGS.copy()

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

user_data = load_settings()
global_brightness = user_data["brightness"]

# --- 2. Hardware Config ---
try:
    import sh1106
    i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=100000)
    display = sh1106.SH1106_I2C(128, 64, i2c)
    
    # Bulletproof screen flip function
    def apply_screen_flip(is_flipped):
        try:
            if hasattr(display, 'flip'):
                display.flip(is_flipped)
            elif hasattr(display, 'rotate'):
                display.rotate(1 if is_flipped else 0)
            else:
                # Raw hardware register commands for SH1106/SSD1306
                display.write_cmd(0xA1 if is_flipped else 0xA0) # Segment remap
                display.write_cmd(0xC8 if is_flipped else 0xC0) # COM Output Scan Direction
        except Exception as e:
            print("Could not flip screen:", e)
            
    # Apply the saved rotation state on boot
    apply_screen_flip(user_data.get("screen_flipped", False))
    
except Exception as e:
    print("OLED Error:", e)
    sys.exit(1)

# --- MicroPython Hardware Classes ---
class RotaryEncoder:
    def __init__(self, pin_a, pin_b, divisor=2):
        self._pin_a = machine.Pin(pin_a, machine.Pin.IN, machine.Pin.PULL_UP)
        self._pin_b = machine.Pin(pin_b, machine.Pin.IN, machine.Pin.PULL_UP)
        self._raw_steps = 0
        self.divisor = divisor
        self._last_a = self._pin_a.value()
        self._pin_a.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=self._cb)

    def _cb(self, pin):
        a = self._pin_a.value()
        b = self._pin_b.value()
        if a != self._last_a:
            if a != b:
                self._raw_steps += 1
            else:
                self._raw_steps -= 1
            self._last_a = a

    @property
    def steps(self):
        return self._raw_steps // self.divisor

    @steps.setter
    def steps(self, value):
        self._raw_steps = value * self.divisor

class Button:
    def __init__(self, pin):
        self._pin = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
    @property
    def is_pressed(self):
        return not self._pin.value()

class ButtonGroup:
    def __init__(self, pins):
        self.buttons = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in pins]
    @property
    def is_pressed(self):
        return any(not b.value() for b in self.buttons)

encoder = RotaryEncoder(25, 26)
btn_select = ButtonGroup([32, 27])
btn_bottom = Button(33)

# --- 3. State Variables ---
menu_mode = "MAIN" 
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
timer_edit_stage = 0 
timer_h, timer_m, timer_s = 0, 0, 0
alarm_anim_target = ""
alarm_theme_target = ""
TIMER_MODES = ["SLEEP", "HOURGLASS", "ALARM"]

def get_anim_settings(func):
    keys = [attr for attr in dir(func) if attr.startswith("attr_") and not attr.endswith("_choice")]
    display_opts = [k.replace('attr_', '').replace('list_', '').replace('bool_', '').replace('step_', '').replace('int_', '').replace('_', ' ').upper() for k in keys]
    return keys, display_opts + ["Global Brightness", "Back to List"]

def sync_time_uk():
    ssid = user_data.get("wifi_ssid", "")
    pwd = user_data.get("wifi_pass", "")
    
    if not ssid:
        return # Can't sync without Wi-Fi setup
        
    print("Syncing time via NTP...")
    sta.active(True)
    sta.connect(ssid, pwd)
    
    timeout = 10
    while not sta.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        
    if sta.isconnected():
        try:
            import ntptime
            ntptime.settime() # Pulls atomic time and sets ESP32 to UTC
            
            # UK Daylight Savings (BST) Calculation
            year, month, mday, hour, min, sec, weekday, yearday = time.localtime()
            
            is_dst = False
            if 4 <= month <= 9:
                is_dst = True
            elif month == 3:
                # BST starts last Sunday in March
                last_sunday = 31 - (time.localtime(time.mktime((year, 3, 31, 0, 0, 0, 0, 0)))[6] + 1) % 7
                if mday >= last_sunday: is_dst = True
            elif month == 10:
                # BST ends last Sunday in October
                last_sunday = 31 - (time.localtime(time.mktime((year, 10, 31, 0, 0, 0, 0, 0)))[6] + 1) % 7
                if mday < last_sunday: is_dst = True
                
            if is_dst:
                # If we are in BST, shift the hardware clock forward by 1 hour (3600 sec)
                tm = time.localtime(time.time() + 3600)
                # RTC requires: (year, month, day, weekday, hours, minutes, seconds, subseconds)
                machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
                
            print("UK Time synced successfully!")
        except Exception as e:
            print("NTP sync failed:", e)
            
    # Disconnect so Wi-Fi doesn't interfere with ESP-NOW
    sta.disconnect()
    sta.active(True) 
    
    # Force the radio back to Channel 1 so it can talk to the stands again
    sta.config(channel=1)
    print("Time sync complete. Reverted to ESP-NOW Channel 1.")


# --- 4. Network & ESP-NOW Setup ---
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.config(channel=1) 
sta.disconnect()

ap_if = network.WLAN(network.AP_IF)
ap_if.active(False)
web_server_task = None

e = espnow.ESPNow()
e.active(True)
broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
e.add_peer(broadcast_mac)

found_mac_bytes = None
found_mac_str = ""

def broadcast_to_stands(command, payload=None):
    msg = json.dumps({"cmd": command, "payload": payload})
    try:
        e.send(broadcast_mac, msg.encode('utf-8'))
    except Exception:
        pass

# --- 5. Async Web Server (Captive Portal) ---
def url_decode(s):
    s = s.replace('+', ' ')
    res = ""
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            res += chr(int(s[i+1:i+3], 16))
            i += 3
        else:
            res += s[i]
            i += 1
    return res

async def web_request_handler(reader, writer):
    global user_data, menu_mode, last_encoder_val
    try:
        req = await reader.read(1024)
        req_str = req.decode('utf-8', 'ignore')
        
        if "POST" in req_str:
            body = req_str.split("\r\n\r\n")[-1]
            data = {}
            for pair in body.split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    data[k] = url_decode(v)
            
            if 's' in data:
                user_data["wifi_ssid"] = data['s']
                user_data["wifi_pass"] = data.get('p', '')
                save_settings(user_data)
                
                broadcast_to_stands("SAVE_WIFI", {"ssid": user_data["wifi_ssid"], "pass": user_data["wifi_pass"]})
                
                res = "HTTP/1.0 200 OK\r\n\r\n<html><body style='font-family:sans-serif; text-align:center; padding:20px;'><h2>Saved!</h2><p>Credentials synced to stands.</p><p>You may now close this page and exit AP mode on the controller.</p></body></html>"
                writer.write(res.encode())
                await writer.drain()
                sync_time_uk()

                menu_mode = "MAIN"
                last_encoder_val = -1
                # Schedule the AP to shut down in the background
                asyncio.create_task(stop_ap_mode())
        else:
            current_ssid = user_data.get("wifi_ssid", "")
            html = """HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n
            <html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="font-family:sans-serif; padding:20px; max-width:400px; margin:auto;">
            <h2>WiFi Setup</h2>
            <form action="/" method="POST">
            <p><strong>SSID:</strong><br><input type="text" name="s" value="{}" style="width:100%; padding:8px;"></p>
            <p><strong>Password:</strong><br><input type="password" name="p" style="width:100%; padding:8px;"></p>
            <input type="submit" value="Save & Sync" style="width:100%; padding:15px; background:#007BFF; color:white; border:none; border-radius:5px; font-size:16px;">
            </form></body></html>
            """.format(current_ssid)
            writer.write(html.encode())
            await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()
        await writer.wait_closed()

async def start_ap_mode():
    global web_server_task
    ap_if.active(True)
    ap_if.config(essid="LED_Tower_Setup", authmode=0)
    web_server_task = await asyncio.start_server(web_request_handler, "0.0.0.0", 80)

async def stop_ap_mode():
    global web_server_task
    if web_server_task:
        web_server_task.close()
        #await web_server_task.wait_closed()
    ap_if.active(False)

# --- 6. TIMER BACKGROUND TASK ---
async def timer_manager():
    global timer_active, global_brightness
    try:
        if timer_mode == "SLEEP":
            start_b = user_data["brightness"]
            while time.time() < timer_end_time and timer_active:
                remaining = timer_end_time - time.time()
                progress = remaining / timer_duration_sec
                global_brightness = start_b * max(0.01, progress)
                broadcast_to_stands("SET_BRIGHTNESS", global_brightness)
                await asyncio.sleep(1)
            
            if timer_active:
                broadcast_to_stands("PLAY_ANIMATION", "stop")
                timer_active = False

        elif timer_mode == "HOURGLASS":
            global_brightness = user_data["brightness"]
            broadcast_to_stands("START_HOURGLASS", timer_duration_sec)
            
            while time.time() < timer_end_time and timer_active:
                await asyncio.sleep(1)
                
            if timer_active:
                broadcast_to_stands("FLASH_RED_ALARM", None)
                await asyncio.sleep(2)
                broadcast_to_stands("PLAY_ANIMATION", "stop")
                timer_active = False

        elif timer_mode == "ALARM":
            while time.time() < timer_end_time and timer_active:
                await asyncio.sleep(1)
                
            if timer_active:
                timer_active = False
                if alarm_anim_target:
                    func = getattr(LEDTower1, alarm_anim_target)
                    t_key = next((k for k in ['attr_list_theme', 'attr_list_color_palette', 'attr_list_color_theme'] if hasattr(func, k)), None)
                    if t_key and alarm_theme_target:
                        if alarm_anim_target not in user_data["animation_data"]:
                            user_data["animation_data"][alarm_anim_target] = {}
                        user_data["animation_data"][alarm_anim_target][t_key] = alarm_theme_target
                        save_settings(user_data)
                    trigger_anim(alarm_anim_target) 
                else:
                    trigger_anim('champagne') 
    except asyncio.CancelledError:
        pass

def start_the_timer():
    global timer_active, timer_end_time, timer_task_ref
    timer_end_time = time.time() + timer_duration_sec
    timer_active = True
    if timer_task_ref:
        timer_task_ref.cancel()
    timer_task_ref = asyncio.create_task(timer_manager())

def cancel_timer():
    global timer_active, timer_task_ref, global_brightness
    if timer_active:
        timer_active = False
        if timer_task_ref:
            timer_task_ref.cancel()
        global_brightness = user_data["brightness"]
        broadcast_to_stands("CANCEL_TIMER", None)

def trigger_anim(name):
    global selected_anim_title, current_anim_name
    
    if timer_active and timer_mode == "HOURGLASS":
        cancel_timer() 
        
    current_anim_name = name
    func = getattr(LEDTower1, name)
    selected_anim_title = getattr(func, 'title', name.replace('_', ' ').upper())
    
    if user_data.get("last_anim") != name:
        user_data["last_anim"] = name
        save_settings(user_data)

    if name not in user_data["animation_data"]:
        user_data["animation_data"][name] = {}

    anim_config = user_data["animation_data"][name]
    
    payload = {
        "anim": name,
        "config": anim_config,
        "brightness": user_data["brightness"]
    }
    broadcast_to_stands("PLAY_ANIMATION", payload)


# --- 7. Hardware Loop ---
async def hardware_loop():
    global menu_mode, live_menu_idx, edit_attr_key, edit_attr_name, last_encoder_val
    global timer_active, timer_duration_sec, timer_end_time, timer_mode, timer_task_ref
    global timer_edit_stage, timer_h, timer_m, timer_s, alarm_anim_target, alarm_theme_target
    global global_brightness, found_mac_bytes, found_mac_str

    last_interaction_time = time.time()
    is_screensaver = False
    screensaver_timeout = 30.0  
    last_drawn_second = -1
    last_drawn_minute = -1
    last_encoder_steps = int(encoder.steps)

    while True:
        current_time = time.time()
        current_steps = int(encoder.steps)

        # --- GLOBAL ESP-NOW LISTENER ---
        host, msg = e.recv(0)
        if msg:
            try:
                data = json.loads(msg.decode('utf-8'))
                cmd = data.get("cmd")
                
                if cmd == "PAIR_ME" and menu_mode == "PAIRING_SEARCH":
                    found_mac_str = data.get("mac")
                    found_mac_bytes = host
                    menu_mode = "PAIRING_FOUND"
                    last_encoder_val = -1
                    
                elif cmd == "REQUEST_WIFI":
                    stored_ssid = user_data.get("wifi_ssid", "")
                    stored_pwd = user_data.get("wifi_pass", "")
                    if stored_ssid:
                        broadcast_to_stands("SAVE_WIFI", {"ssid": stored_ssid, "pass": stored_pwd})
            except Exception:
                pass

        activity_detected = False
        if current_steps != last_encoder_steps:
            activity_detected = True
            last_encoder_steps = current_steps
            
        if btn_select.is_pressed or btn_bottom.is_pressed:
            activity_detected = True

        if activity_detected:
            last_interaction_time = current_time
            if is_screensaver:
                is_screensaver = False
                last_encoder_val = -1 

        if not is_screensaver and (current_time - last_interaction_time > screensaver_timeout):
            if menu_mode not in ["TIMER_SETUP", "PAIRING_SEARCH", "PAIRING_FOUND", "WIFI_SETUP"]:
                is_screensaver = True
                last_drawn_second = -1 
                last_drawn_minute = -1 

        if is_screensaver:
            now = time.localtime() 
            n_hr, n_min, n_sec = now[3], now[4], now[5]
            
            needs_redraw = False
            if timer_active and n_sec != last_drawn_second:
                needs_redraw = True
                last_drawn_second = n_sec
            elif not timer_active and n_min != last_drawn_minute:
                needs_redraw = True
                last_drawn_minute = n_min

            if needs_redraw:
                display.fill(0)
                if timer_active:
                    time_str = "{:02d}:{:02d}".format(n_hr, n_min)
                    rem = max(0, timer_end_time - time.time())
                    hours, rem = divmod(int(rem), 3600)
                    mins, secs = divmod(rem, 60)
                    display.text(time_str, 45, 10, 1)
                    display.text("{:02d}:{:02d}:{:02d}".format(hours, mins, secs), 30, 40, 1)
                else:
                    time_str = "{:02d}:{:02d}".format(n_hr, n_min)
                    date_str = "{:02d}/{:02d}/{:04d}".format(now[2], now[1], now[0])
                    display.text(time_str, 45, 20, 1)
                    display.text(date_str, 25, 40, 1)
                display.show()
                        
            await asyncio.sleep(0.05)
            continue

        if menu_mode == "MAIN":
            anim_funcs = [f for f in LEDTower1.__all__ if f != "stop"]
            timer_text = "CANCEL TIMER" if timer_active else "NEW TIMER"
            
            full_menu_display = [getattr(getattr(LEDTower1, f), 'title', f.replace('_', ' ').upper()) for f in anim_funcs] + [timer_text, "PAIR NEW STAND", "WIFI SETUP", "FLIP SCREEN", "UPDATE CONTROLLER", "UPDATE STANDS", "SOFT REBOOT"]

            idx = max(0, min(int(encoder.steps), len(full_menu_display) - 1))
            encoder.steps = idx 
            
            if idx != last_encoder_val:
                display.fill(0)
                display.text("MAIN MENU", 5, 2, 1)
                display.hline(0, 15, 128, 1)
                for i in range(-1, 2):
                    curr = idx + i
                    if 0 <= curr < len(full_menu_display):
                        prefix = "> " if i == 0 else "  "
                        display.text("{}{}".format(prefix, full_menu_display[curr]), 10, 25 + (i * 12), 1)
                display.show()
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
                elif choice == "PAIR NEW STAND":
                    menu_mode = "PAIRING_SEARCH"
                    encoder.steps = 0
                    last_encoder_val = -1
                elif choice == "WIFI SETUP":
                    await start_ap_mode()
                    menu_mode = "WIFI_SETUP"
                    last_encoder_val = -1
                elif choice == "FLIP SCREEN":
                    user_data["screen_flipped"] = not user_data.get("screen_flipped", False)
                    save_settings(user_data)
                    apply_screen_flip(user_data["screen_flipped"])
                    
                    display.fill(0)
                    display.text("SCREEN FLIPPED", 10, 30, 1)
                    display.show()
                    time.sleep(1)
                    last_encoder_val = -1
                elif choice == "SOFT REBOOT":
                    cancel_timer()
                    broadcast_to_stands("PLAY_ANIMATION", "stop")
                    display.fill(0)
                    display.text("REBOOTING...", 25, 25, 1)
                    display.show()
                    machine.reset()
                elif choice == "UPDATE CONTROLLER":
                    ssid = user_data.get("wifi_ssid", "")
                    if not ssid:
                        display.fill(0)
                        display.text("SETUP WIFI FIRST", 5, 30, 1)
                        display.show()
                        time.sleep(2)
                    else:
                        display.fill(0)
                        display.text("PREPARING OTA", 15, 25, 1)
                        display.text("Rebooting...", 20, 40, 1)
                        display.show()
                        
                        # Set the flag and reboot into Safe Mode
                        with open("ota_pending.txt", "w") as f:
                            f.write("1")
                        time.sleep(1)
                        machine.reset()

                elif choice == "UPDATE STANDS":
                    display.fill(0)
                    display.text("SENDING OTA", 20, 25, 1)
                    display.text("COMMAND...", 25, 40, 1)
                    display.show()
                    
                    broadcast_to_stands("START_OTA", None)
                    time.sleep(1.5)
                    
                    menu_mode = "MAIN"
                    encoder.steps = 0
                    last_encoder_val = -1
                else:
                    trigger_anim(anim_funcs[idx])
                    menu_mode = "ANIM_MENU"
                    encoder.steps = 0
                    last_encoder_val = -1
                
                while btn_select.is_pressed:
                    await asyncio.sleep(0.1)

        elif menu_mode == "WIFI_SETUP":
            if last_encoder_val != 1:
                display.fill(0)
                display.text("AP: LED_Tower_Setup", 0, 10, 1)
                display.text("IP: 192.168.4.1", 0, 25, 1)
                display.text("Connect on phone", 0, 40, 1)
                display.text("> Press Bottom to exit", 0, 55, 1)
                display.show()
                last_encoder_val = 1
                
            if btn_bottom.is_pressed:
                asyncio.create_task(stop_ap_mode())
                menu_mode = "MAIN"
                last_encoder_val = -1
                encoder.steps = 0
                while btn_bottom.is_pressed:
                    await asyncio.sleep(0.1)

        elif menu_mode == "PAIRING_SEARCH":
            if last_encoder_val != 2:
                display.fill(0)
                display.text("SEARCHING...", 5, 10, 1)
                display.text("Ensure stand is", 5, 25, 1)
                display.text("in pairing mode", 5, 35, 1)
                display.text("> Press to exit", 5, 55, 1)
                display.show()
                last_encoder_val = 2
                    
            # NEW: Listen for BOTH the encoder click and the bottom button
            if btn_bottom.is_pressed or btn_select.is_pressed:
                menu_mode = "MAIN"
                last_encoder_val = -1
                encoder.steps = 0
                while btn_bottom.is_pressed or btn_select.is_pressed:
                    await asyncio.sleep(0.1)

        elif menu_mode == "PAIRING_FOUND":
            display.fill(0)
            display.text("STAND FOUND!", 5, 10, 1)
            display.text(found_mac_str, 5, 25, 1)
            display.text("> Press to Pair", 5, 45, 1)
            display.show()
            
            if btn_select.is_pressed:
                try:
                    e.add_peer(found_mac_bytes)
                except Exception:
                    pass
                
                confirm_msg = json.dumps({"cmd": "YOU_ARE_PAIRED", "payload": None})
                e.send(found_mac_bytes, confirm_msg.encode('utf-8'))
                
                display.fill(0)
                display.text("PAIRED!", 35, 30, 1)
                display.show()
                await asyncio.sleep(1.5)
                
                menu_mode = "MAIN"
                last_encoder_val = -1
                encoder.steps = 0
                while btn_select.is_pressed:
                    await asyncio.sleep(0.1)
                    
            if btn_bottom.is_pressed:
                menu_mode = "MAIN"
                last_encoder_val = -1
                encoder.steps = 0
                while btn_bottom.is_pressed:
                    await asyncio.sleep(0.1)

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

            display.fill(0)
            display.text("SET DURATION", 5, 2, 1)
            display.hline(0, 15, 128, 1)
            
            time_str = ""
            if timer_edit_stage != 0 or blink_on:
                time_str += "{:02d}:".format(timer_h)
            else:
                time_str += "   :"
            
            if timer_edit_stage != 1 or blink_on:
                time_str += "{:02d}:".format(timer_m)
            else:
                time_str += "   :"
                
            if timer_edit_stage != 2 or blink_on:
                time_str += "{:02d}".format(timer_s)
            else:
                time_str += "  "
            
            display.text(time_str, 35, 30, 1)
            labels = ["HOURS", "MINUTES", "SECONDS"]
            display.text(labels[timer_edit_stage], 40, 50, 1)
            display.show()
                
            last_encoder_val = val
            
            if btn_select.is_pressed:
                if timer_edit_stage < 2:
                    timer_edit_stage += 1
                    if timer_edit_stage == 1:
                        encoder.steps = timer_m
                    if timer_edit_stage == 2:
                        encoder.steps = timer_s
                else:
                    timer_duration_sec = (timer_h * 3600) + (timer_m * 60) + timer_s
                    if timer_duration_sec > 0:
                        menu_mode = "TIMER_MODE"
                    else:
                        menu_mode = "MAIN"
                    encoder.steps = 0
                    
                last_encoder_val = -1
                while btn_select.is_pressed:
                    await asyncio.sleep(0.1)

        elif menu_mode == "TIMER_MODE":
            idx = max(0, min(2, int(encoder.steps)))
            encoder.steps = idx
            
            if idx != last_encoder_val:
                display.fill(0)
                display.text("TIMER ACTION", 5, 2, 1)
                display.hline(0, 15, 128, 1)
                for i in range(-1, 2):
                    curr = idx + i
                    if 0 <= curr < len(TIMER_MODES):
                        prefix = "> " if i == 0 else "  "
                        display.text("{}{}".format(prefix, TIMER_MODES[curr]), 10, 25 + (i * 12), 1)
                display.show()
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
                while btn_select.is_pressed:
                    await asyncio.sleep(0.1)

        elif menu_mode == "TIMER_ALARM_ANIM":
            anims = [f for f in LEDTower1.__all__ if f not in ['stop', 'plain_white']]
            idx = max(0, min(len(anims)-1, int(encoder.steps)))
            encoder.steps = idx
            
            if idx != last_encoder_val:
                display.fill(0)
                display.text("WAKE WITH?", 5, 2, 1)
                display.hline(0, 15, 128, 1)
                display.text("> {}".format(getattr(getattr(LEDTower1, anims[idx]), 'title', anims[idx].replace('_', ' ').upper())), 10, 30, 1)
                display.show()
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
                while btn_select.is_pressed:
                    await asyncio.sleep(0.1)

        elif menu_mode == "TIMER_ALARM_THEME":
            func = getattr(LEDTower1, alarm_anim_target)
            t_key = next(k for k in ['attr_list_theme', 'attr_list_color_palette', 'attr_list_color_theme'] if hasattr(func, k))
            themes = getattr(func, t_key)
            
            idx = max(0, min(len(themes)-1, int(encoder.steps)))
            encoder.steps = idx
            
            if idx != last_encoder_val:
                display.fill(0)
                display.text("SELECT THEME", 5, 2, 1)
                display.hline(0, 15, 128, 1)
                display.text("> {}".format(themes[idx]), 10, 30, 1)
                display.show()
                last_encoder_val = idx
                
            if btn_select.is_pressed:
                alarm_theme_target = themes[idx]
                start_the_timer()
                menu_mode = "MAIN"
                last_encoder_val = -1
                while btn_select.is_pressed:
                    await asyncio.sleep(0.1)

        elif menu_mode == "ANIM_MENU":
            func = getattr(LEDTower1, current_anim_name)
            attr_keys, display_options = get_anim_settings(func)
            idx = max(0, min(int(encoder.steps), len(display_options) - 1))
            encoder.steps = idx

            if idx != last_encoder_val:
                display.fill(0)
                display.text(selected_anim_title[:16], 5, 2, 1)
                display.hline(0, 15, 128, 1)
                for i in range(-1, 2):
                    curr = idx + i
                    if 0 <= curr < len(display_options):
                        prefix = "> " if i == 0 else "  "
                        display.text("{}{}".format(prefix, display_options[curr]), 10, 25 + (i * 12), 1)
                display.show()
                last_encoder_val = idx

            if btn_select.is_pressed:
                choice = display_options[idx]
                if choice == "Back to List":
                    menu_mode = "MAIN"
                    encoder.steps = 0
                    last_encoder_val = -1
                elif choice == "Global Brightness":
                    menu_mode = "LIVE_EDIT"
                    edit_attr_key = "GLOBAL_BRIGHT"
                    edit_attr_name = choice
                    encoder.steps = int(user_data["brightness"] * 10)
                else:
                    edit_attr_key = attr_keys[idx]
                    edit_attr_name = choice
                    menu_mode = "LIVE_EDIT"
                    val = getattr(func, edit_attr_key)
                    if isinstance(val, list):
                        current_choice = getattr(func, edit_attr_key + "_choice", val[0])
                        try:
                            encoder.steps = val.index(current_choice)
                        except Exception:
                            encoder.steps = 0
                    else:
                        encoder.steps = 1 if isinstance(val, bool) and val else (0 if isinstance(val, bool) else int(val))
                
                last_encoder_val = -1 
                while btn_select.is_pressed:
                    await asyncio.sleep(0.1)

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
            elif is_step_type:
                val = max(1, min(10, int(encoder.steps)))
                encoder.steps = val
            else:
                val = max(1, min(100, int(encoder.steps)))
                encoder.steps = val

            if val != last_encoder_val:
                display.fill(0)
                display.text("EDIT: {}".format(edit_attr_name[:10]), 5, 2, 1)
                display.hline(0, 15, 128, 1)

                if is_list:
                    for i in range(-1, 2):
                        curr_opt_idx = idx + i
                        if 0 <= curr_opt_idx < len(options):
                            prefix = "> " if i == 0 else "  "
                            display.text("{}{}".format(prefix, options[curr_opt_idx]), 10, 25 + (i * 12), 1)
                elif is_bool:
                    status = "ON" if val else "OFF"
                    display.rect(30, 25, 60, 20, 1)
                    if val:
                        display.fill_rect(32, 27, 56, 16, 1)
                        display.text(status, 50, 31, 0)
                    else:
                        display.text(status, 50, 31, 1)
                else:
                    bar_w = val * 10 if is_step_type else val
                    display.rect(10, 25, 100, 10, 1)
                    display.fill_rect(10, 25, bar_w, 10, 1)
                    display.text("Value: {}".format(val), 10, 45, 1)
                
                display.show()
                last_encoder_val = val
                
                if edit_attr_key == "GLOBAL_BRIGHT":
                    user_data["brightness"] = val / 10.0
                    global_brightness = user_data["brightness"]
                    broadcast_to_stands("SET_BRIGHTNESS", global_brightness)
                elif is_list:
                    setattr(getattr(LEDTower1, current_anim_name), edit_attr_key + "_choice", val)
                else:
                    setattr(getattr(LEDTower1, current_anim_name), edit_attr_key, val)

            if btn_select.is_pressed:
                if current_anim_name not in user_data["animation_data"]:
                    user_data["animation_data"][current_anim_name] = {}
                    
                if edit_attr_key != "GLOBAL_BRIGHT":
                    # Only save and broadcast if it's a real animation attribute
                    user_data["animation_data"][current_anim_name][edit_attr_key] = val
                    save_settings(user_data)
                    
                    payload = {"attr": edit_attr_key, "value": val}
                    broadcast_to_stands("UPDATE_ATTRIBUTE", payload)
                else:
                    # It was just global brightness, so just save it without broadcasting an attribute update
                    save_settings(user_data)
                    
                # Go back up one menu level
                menu_mode = "ANIM_MENU"
                last_encoder_val = -1
                
                # Wait for the button to be released so we don't spam the network!
                while btn_select.is_pressed:
                    await asyncio.sleep(0.1)

        if btn_bottom.is_pressed and menu_mode not in ["WIFI_SETUP"]:
            if timer_active and timer_mode != "ALARM":
                cancel_timer()
                
            global_brightness = user_data["brightness"]
            broadcast_to_stands("PLAY_ANIMATION", "stop")
            
            menu_mode = "MAIN"
            last_encoder_val = -1
            encoder.steps = 0
            while btn_bottom.is_pressed:
                await asyncio.sleep(0.1)
            
        await asyncio.sleep(0.05)

async def run_control_box():
    # --- NEW: Sync time on boot ---
    display.fill(0)
    display.text("SYNCING CLOCK...", 5, 30, 1)
    display.show()
    #sync_time_uk()
    
    saved_anim = user_data.get("last_anim", "")
    if saved_anim and hasattr(LEDTower1, saved_anim):
        trigger_anim(saved_anim)
    elif LEDTower1.__all__:
        trigger_anim(LEDTower1.__all__[0])
        
    await hardware_loop()

def start():
    try:
        asyncio.run(run_control_box())
    except KeyboardInterrupt:
        broadcast_to_stands("PLAY_ANIMATION", "stop")