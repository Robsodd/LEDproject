import network
import time
import urequests
import gc

def fetch_and_update(ssid, password, file_urls, caller="control_box"):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(ssid, password)
    
    timeout = 15
    while not sta.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        
    if not sta.isconnected():
        sta.active(False)
        return "WIFI_FAIL" if caller == "speaker_stand" else False
        
    # GitHub requires a User-Agent header, or it may drop the request
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    success_count = 0
    
    try:
        for filename, url in file_urls.items():
            # Force garbage collection to ensure enough RAM for the HTTPS/SSL handshake
            gc.collect()
            
            response = urequests.get(url, headers=headers)
            
            if response.status_code == 200:
                with open(filename, 'w') as f:
                    # Stream in 512-byte chunks to prevent RAM exhaustion on large files
                    while True:
                        chunk = response.raw.read(512)
                        if not chunk:
                            break
                        f.write(chunk)
                success_count += 1
            response.close()
            
        if success_count == len(file_urls):
            return True
        else:
            return "DOWNLOAD_FAIL" if caller == "speaker_stand" else False
            
    except Exception as e:
        print("OTA Error:", e)
        return "EXCEPTION" if caller == "speaker_stand" else False
    finally:
        sta.disconnect()
        sta.active(False)