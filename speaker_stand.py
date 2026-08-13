import machine
import network
import espnow
import neopixel
import uasyncio as asyncio
import ujson as json
import time
import sys
import _thread
import LEDTower1

# --- 1. Hardware Config ---
PIXEL_PIN = 18 
NUM_PIXELS = 100

pixels = neopixel.NeoPixel(machine.Pin(PIXEL_PIN), NUM_PIXELS)

# --- 2. State & Settings ---
SETTINGS_FILE = "stand_settings.json"
active_task = None
active_fade_task = None
global_brightness = 0.3
current_anim_name = ""

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except OSError:
        return {"paired_brain_mac": None}

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

stand_settings = load_settings()

# --- 3. Network, ESP-NOW & Access Point Setup ---
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.config(channel=1) # Force channel 1 for ESP-NOW and Web Server coexistence 
sta.disconnect()

my_mac = sta.config('mac')
broadcast_mac = b'\xff\xff\xff\xff\xff\xff'

e = espnow.ESPNow()
e.active(True)
e.add_peer(broadcast_mac)

if stand_settings.get("paired_brain_mac"):
    brain_mac = bytes.fromhex(stand_settings["paired_brain_mac"].replace(':', ''))
    try:
        e.add_peer(brain_mac)
    except Exception:
        pass 

def start_access_point():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    # Match channel 1 to keep ESP-NOW broadcasting simultaneously
    ap.config(essid="Rainbow_Stand", password="password123", authmode=network.AUTH_WPA_WPA2_PSK, channel=1)
    print("Access Point Active. Connect to 'Rainbow_Stand'. IP:", ap.ifconfig()[0])


# --- 4. Async Web Server Logic ---
async def handle_client(reader, writer):
    global current_anim_name, global_brightness, stand_settings
    
    try:
        request_line = await reader.readline()
        if not request_line:
            writer.close()
            await writer.wait_closed()
            return
            
        request_str = request_line.decode('utf-8').strip()
        
        while True:
            line = await reader.readline()
            if not line or line == b'\r\n':
                break

        # --- API ROUTING ---
        if "GET / " in request_str:
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
            try:
                # Stream the file line-by-line to save precious RAM
                with open("index.html", "r") as f:
                    for html_line in f:
                        if "<!-- INJECT_BUTTONS -->" in html_line:
                            writer.write(b'<div class="anim-grid">\n')
                            for anim in LEDTower1.__all__:
                                if anim == "stop":
                                    continue 
                                
                                display_name = anim.replace('_', ' ').upper()
                                btn_html = f'<button class="btn" onclick="playAnim(\'{anim}\')">{display_name}</button>\n'
                                writer.write(btn_html.encode('utf-8'))
                                
                            writer.write(b'</div>\n')
                        else:
                            writer.write(html_line.encode('utf-8'))
                            
                        await writer.drain() 
            except OSError:
                writer.write(b"<h1>Error: index.html not found on device.</h1>")
                
        elif "GET /api/anim?name=" in request_str:
            anim = request_str.split("name=")[1].split(" ")[0]
            await execute_animation(anim, {}, global_brightness)
            writer.write(b"HTTP/1.1 200 OK\r\n\r\nOK")
            
        elif "GET /api/brightness?val=" in request_str:
            val_str = request_str.split("val=")[1].split(" ")[0]
            global_brightness = float(val_str)
            writer.write(b"HTTP/1.1 200 OK\r\n\r\nOK")
            
        elif "GET /api/reset" in request_str:
            stand_settings["paired_brain_mac"] = None
            save_settings(stand_settings)
            writer.write(b"HTTP/1.1 200 OK\r\n\r\nRESET_SUCCESS")
            await writer.drain()
            await asyncio.sleep(0.5)
            machine.reset() 
            
        else:
            writer.write(b"HTTP/1.1 404 Not Found\r\n\r\n")

        await writer.drain()
        writer.close()
        await writer.wait_closed()
        
    except Exception as err:
        print("Web server error:", err)
        writer.close()
        try:
            await writer.wait_closed()
        except:
            pass

# --- 5. LED Helper Functions ---
def apply_brightness(color_tuple):
    return (int(color_tuple[0] * global_brightness), 
            int(color_tuple[1] * global_brightness), 
            int(color_tuple[2] * global_brightness))

async def pi_set_led(led_id, color):
    try: 
        pixels[led_id] = apply_brightness(color)
        pixels.write()
    except Exception:
        pass

async def pi_set_led_multiple(led_ids, color_array=None, brightness=1.0):
    try:
        if color_array is None:
            return
        for i, lid in enumerate(led_ids):
            if 0 <= lid < NUM_PIXELS:
                raw_color = color_array[i] if isinstance(color_array[0], (list, tuple)) else color_array
                pixels[lid] = (int(raw_color[0] * global_brightness * brightness),
                               int(raw_color[1] * global_brightness * brightness),
                               int(raw_color[2] * global_brightness * brightness))
        pixels.write()
    except Exception:
        pass

# --- 6. Animation Triggers ---
async def play_transition():
    try:
        for i in range(10, -1, -1):
            factor = i / 10.0
            for p in range(NUM_PIXELS):
                c = pixels[p]
                pixels[p] = (int(c[0]*factor), int(c[1]*factor), int(c[2]*factor))
            pixels.write()
            await asyncio.sleep(0.02)
    except Exception:
        pass
    pixels.fill((0,0,0))
    pixels.write()

async def execute_animation(anim_name, config, target_brightness):
    global active_task, current_anim_name, global_brightness
    
    if active_task:
        active_task.cancel()
        try:
            await active_task
        except asyncio.CancelledError:
            pass
        await play_transition()

    current_anim_name = anim_name
    global_brightness = target_brightness
    
    if anim_name == "stop":
        pixels.fill((0,0,0))
        pixels.write()
        return

    func = getattr(LEDTower1, anim_name)
    
    for key, val in config.items():
        if hasattr(func, key):
            original_attr = getattr(func, key)
            if isinstance(original_attr, list):
                setattr(func, key + "_choice", val)
            else:
                setattr(func, key, val)

    active_task = asyncio.create_task(func(pi_set_led, pi_set_led_multiple, (255, 255, 255), 0))


# --- 7. OTA Background Worker & Scanner ---
ota_status = {"done": False, "result": None}

def ota_background_worker(ssid, pwd, urls, caller):
    import ota
    ota_status["result"] = ota.fetch_and_update(ssid, pwd, urls, caller=caller)
    ota_status["done"] = True

async def trigger_threaded_ota(ssid, pwd, urls, caller):
    global ota_status, active_task
    ota_status = {"done": False, "result": None}
    
    if active_task:
        active_task.cancel()
        
    _thread.start_new_thread(ota_background_worker, (ssid, pwd, urls, caller))
    
    pos = 0
    direction = 1
    
    while not ota_status["done"]:
        pixels.fill((0, 0, 15)) 
        
        for col in range(4):
            try:
                pixels[LEDTower1.HEIGHTS[pos][col]] = (0, 255, 255)
                
                if pos > 0:
                    pixels[LEDTower1.HEIGHTS[pos-1][col]] = (0, 100, 150)
                if pos < 24: 
                    pixels[LEDTower1.HEIGHTS[pos+1][col]] = (0, 100, 150)
            except (IndexError, AttributeError):
                pass
                
        pixels.write()
        
        pos += direction
        if pos >= 24 or pos <= 0:
            direction *= -1
            
        await asyncio.sleep(0.04)

    if ota_status["result"] is True:
        pixels.fill((0, 255, 0)) 
        pixels.write()
        await asyncio.sleep(1)
        machine.reset()
    else:
        print("OTA Failed:", ota_status["result"])
        pixels.fill((255, 0, 0)) 
        pixels.write()
        await asyncio.sleep(3)
        pixels.fill((0, 0, 0))
        pixels.write()
        
        e.active(True)
        req_msg = json.dumps({"cmd": "REQUEST_WIFI", "payload": None})
        try:
            e.send(broadcast_mac, req_msg.encode('utf-8'))
        except Exception:
            pass


# --- 8. The ESP-NOW Listener Loop ---
async def network_listener():
    global global_brightness, stand_settings
    
    last_broadcast_time = 0
    mac_str = ':'.join('%02x' % b for b in my_mac)

    while True:
        if not stand_settings.get("paired_brain_mac"):
            if time.time() - last_broadcast_time > 2:
                pairing_msg = json.dumps({"cmd": "PAIR_ME", "mac": mac_str})
                try:
                    e.send(broadcast_mac, pairing_msg)
                    print(f"Broadcasting for a Brain... My MAC: {mac_str}")
                except Exception as err:
                    pass
                last_broadcast_time = time.time()
        
        host, msg = e.recv(0)
        if msg:
            try:
                data = json.loads(msg.decode('utf-8'))
                cmd = data.get("cmd")
                payload = data.get("payload")
                
                if cmd == "YOU_ARE_PAIRED":
                    brain_mac_str = ':'.join('%02x' % b for b in host)
                    stand_settings["paired_brain_mac"] = brain_mac_str
                    save_settings(stand_settings)
                    e.add_peer(host) 
                    print(f"Successfully paired with Brain: {brain_mac_str}")
                    
                    pixels.fill((0, 255, 0))
                    pixels.write()
                    await asyncio.sleep(1)
                    pixels.fill((0, 0, 0))
                    pixels.write()
                    machine.reset() 

                elif cmd == "PLAY_ANIMATION":
                    if payload == "stop":
                        await execute_animation("stop", {}, 0)
                    else:
                        anim = payload.get("anim")
                        config = payload.get("config", {})
                        brightness = payload.get("brightness", 0.3)
                        await execute_animation(anim, config, brightness)
                
                elif cmd == "SET_BRIGHTNESS":
                    global_brightness = float(payload)
                
                elif cmd == "UPDATE_ATTRIBUTE":
                    attr = payload.get("attr")
                    val = payload.get("value")
                    func = getattr(LEDTower1, current_anim_name)
                    if hasattr(func, attr):
                        if isinstance(getattr(func, attr), list):
                            setattr(func, attr + "_choice", val)
                        else:
                            setattr(func, attr, val)

                elif cmd == "FLASH_RED_ALARM":
                    if active_task:
                        active_task.cancel()
                    for _ in range(5):
                        pixels.fill((255, 0, 0))
                        pixels.write()
                        await asyncio.sleep(0.5)
                        pixels.fill((0, 0, 0))
                        pixels.write()
                        await asyncio.sleep(0.5)
                        
                elif cmd == "SAVE_WIFI":
                    stand_settings["wifi_ssid"] = payload.get("ssid", "")
                    stand_settings["wifi_pass"] = payload.get("pass", "")
                    save_settings(stand_settings)
                    print("Wi-Fi credentials synced from controller!")
                    
                elif cmd == "START_OTA":
                    ssid = stand_settings.get("wifi_ssid", "")
                    pwd = stand_settings.get("wifi_pass", "")
                    
                    if ssid:
                        e.active(False) 
                        
                        stand_urls = {
                            "LEDTower1.py": "https://raw.githubusercontent.com/YOUR_USERNAME/rainbow_stationary/main/LEDTower1.py",
                            "speaker_stand.py": "https://raw.githubusercontent.com/YOUR_USERNAME/rainbow_stationary/main/speaker_stand.py"
                        } 
                        
                        asyncio.create_task(trigger_threaded_ota(ssid, pwd, stand_urls, "speaker_stand"))
                    else:
                        req_msg = json.dumps({"cmd": "REQUEST_WIFI", "payload": None})
                        try:
                            e.send(broadcast_mac, req_msg.encode('utf-8'))
                        except Exception:
                            pass
                        pixels.fill((255, 200, 0)) 
                        pixels.write()
                        
            except Exception as err:
                print("Bad message or parse error:", err)
        
        await asyncio.sleep(0.01) 

# --- 9. Main Boot Logic ---
async def main():
    print("Speaker Stand Initialized.")
    
    if not stand_settings.get("paired_brain_mac"):
        start_access_point()
        asyncio.create_task(asyncio.start_server(handle_client, "0.0.0.0", 80))
        print("Web server running in fallback mode.")
        
    await network_listener()

def start():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pixels.fill((0,0,0))
        pixels.write()