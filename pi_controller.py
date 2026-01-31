import asyncio
import LEDTower1  # Your logic file
import board      # Raspberry Pi hardware library
import neopixel   # LED control library

# --- HARDWARE SETUP ---
PIXEL_PIN = board.D18
NUM_PIXELS = 100
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, auto_write=False)

# --- THE BRIDGE ---
async def pi_set_led(led_id, color_hex):
    # Convert "#00ffee" to (0, 255, 238) for the hardware
    color_hex = color_hex.lstrip('#')
    rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
    
    pixels[led_id] = rgb
    pixels.show()

# --- THE CONTROLLER LOOP ---
async def run_show():
    print("Starting LED Show...")
    while True:
        # Now we just call your existing functions!
        print("Running Comet...")
        await LEDTower1.comet_chase(pi_set_led, "#00ffee", 0.05)
        
        print("Running Sparkle...")
        await LEDTower1.sparkle(pi_set_led, "#ff00aa", 0.01)
        
        # Note: In a real Pi script, you'd need a way to 
        # break this loop (like a button press).

if __name__ == "__main__":
    asyncio.run(run_show())