import machine
import time
import uos

def do_safe_ota():
    print("OTA Flag found! Entering Safe Update Mode...")
    import ujson
    
    ssid, pwd, screen_flipped = "", "", False
    try:
        with open("settings.json", "r") as f:
            data = ujson.load(f)
            ssid = data.get("wifi_ssid", "")
            pwd = data.get("wifi_pass", "")
            screen_flipped = data.get("screen_flipped", False)
    except OSError:
        try:
            with open("stand_settings.json", "r") as f:
                data = ujson.load(f)
                ssid = data.get("wifi_ssid", "")
                pwd = data.get("wifi_pass", "")
        except OSError:
            pass
            
    if ssid:
        # --- Visual Feedback for Control Box (OLED) ---
        has_screen = False
        try:
            i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=100000)
            import sh1106
            display = sh1106.SH1106_I2C(128, 64, i2c)
            # Apply flip setting
            if hasattr(display, 'flip'): display.flip(screen_flipped)
            elif hasattr(display, 'rotate'): display.rotate(1 if screen_flipped else 0)
            else:
                display.write_cmd(0xA1 if screen_flipped else 0xA0)
                display.write_cmd(0xC8 if screen_flipped else 0xC0)
                
            display.fill(0)
            print("Downloading update files...")
            display.text("DOWNLOADING...", 10, 30, 1)
            display.show()
            has_screen = True
        except Exception:
            print("Exception initializing OLED display. Proceeding without visual feedback.")
            pass

        # --- Visual Feedback for Speaker Stands (NeoPixels) ---
        has_pixels = False
        try:
            import neopixel
            pixels = neopixel.NeoPixel(machine.Pin(18), 100)
            pixels.fill((0, 0, 50)) # Dim Blue
            pixels.write()
            has_pixels = True
        except Exception:
            pass
            
        # --- The Download ---
        import ota
        MANIFEST = "https://cdn.jsdelivr.net/gh/Robsodd/LEDproject@main/manifest.json"
        
        print("Starting safe mode download...")
        success = ota.fetch_and_update(ssid, pwd, MANIFEST, caller="unified")
        print("OTA RESULT:", success) 
        
        # --- Show Results ---
        if has_screen:
            display.fill(0)
            if success is True:
                display.text("OTA SUCCESS!", 15, 30, 1)
            else:
                display.text("FAILED: " + str(success), 0, 30, 1)
            display.show()
            
        if has_pixels:
            pixels.fill((0, 50, 0) if success is True else (50, 0, 0))
            pixels.write()
            
        time.sleep(2)
        
        # Cleanup pixels before reboot
        if has_pixels:
            pixels.fill((0, 0, 0))
            pixels.write()
            
    # ALWAYS delete the flag so we don't get stuck in a boot loop
    try:
        uos.remove("ota_pending.txt")
    except OSError:
        pass
        
    print("Rebooting into normal mode...")
    time.sleep(0.5)
    machine.reset()


def boot_device():
    # 1. Check for OTA flag first, before memory gets fragmented
    try:
        uos.stat("ota_pending.txt")
        do_safe_ota()
    except OSError:
        pass 
        
    print("Detecting hardware role...")
    try:
        i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=100000)
        time.sleep(0.1)
        devices = i2c.scan()
        
        if devices:
            print(f"OLED Detected at {devices}! Booting Control Box...")
            import control_box
            control_box.start()
            return
    except Exception as e:
        print("I2C scan failed (likely no screen attached).", e)
        
    print("No OLED Detected. Booting Speaker Stand...")
    import speaker_stand
    speaker_stand.start()

if __name__ == "__main__":
    boot_device()