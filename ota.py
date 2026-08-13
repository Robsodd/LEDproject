import network
import time
import urequests
import gc
import ujson
import uos

def ensure_directory(file_path):
    """Safely creates missing folders like /lib/"""
    parts = file_path.split('/')[:-1] 
    current_path = ""
    
    for part in parts:
        if current_path == "":
            current_path = part
        else:
            current_path += "/" + part
            
        try:
            uos.mkdir(current_path)
        except OSError:
            pass

def fetch_and_update(ssid, password, manifest_url, caller="control_box"):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(ssid, password)
    
    timeout = 15
    while not sta.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        
    if not sta.isconnected():
        sta.active(False)
        return "WIFI_FAIL" 
        
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        # 1. Fetch the unified master list (manifest.json)
        gc.collect()
        response = urequests.get(manifest_url, headers=headers)
        if response.status_code == 200:
            manifest_data = ujson.loads(response.text)
        else:
            response.close()
            return "MANIFEST_FAIL" 
        response.close()
        
        # 2. Extract the universal file list
        file_urls = manifest_data.get("files", {})
        if not file_urls:
            return "NO_FILES_IN_MANIFEST" 

        # 3. Download everything
        success_count = 0
        for filename, url in file_urls.items():
            gc.collect()
            
            # Create folders if needed
            ensure_directory(filename)
            
            dl_response = urequests.get(url, headers=headers)
            
            if dl_response.status_code == 200:
                with open(filename, 'w') as f:
                    while True:
                        chunk = dl_response.raw.read(512)
                        if not chunk:
                            break
                        f.write(chunk)
                success_count += 1
            dl_response.close()
            
        if success_count == len(file_urls):
            return True
        else:
            return "DOWNLOAD_FAIL" 
            
    except Exception as e:
        print("OTA Error:", e)
        return "EXCEPTION" 
    finally:
        sta.disconnect()
        sta.active(False)