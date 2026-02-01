import board
import neopixel
import asyncio
import LEDTower1
import sys

# 1. Hardware Config
PIXEL_PIN = board.D18  # Typical GPIO pin for LEDs
NUM_PIXELS = 100
current_brightness = 0.3
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=current_brightness, auto_write=False)

# 2. The Bridge Function
# This takes the hex colors from your logic and gives them to the real LEDs
async def pi_set_led(led_id, color_hex):
    # SAFETY: If color_hex is empty, None, or too short, just turn the LED off
    if not color_hex or len(color_hex) < 7:
        pixels[led_id] = (0, 0, 0)
        pixels.show()
        return

    try:
        # Convert hex (#00ffee) to RGB tuple (0, 255, 238)
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        
        pixels[led_id] = (r, g, b)
        pixels.show()
    except ValueError:
        # If the hex code is garbled, just skip this frame
        pass

async def main():
    global current_brightness
    active_task = None
    
    # Run the startup sequence
    print("--- POWERING UP ---")
    await LEDTower1.startup_sequence(pi_set_led, "#ffffff", 0.05)

    while True:
        # 1. List the available options
        print("\n" + "="*30)
        print(" LED TOWER CONTROL MENU")
        print(f" LED TOWER (Brightness: {int(current_brightness * 100)}%)")
        print("="*30)
        # Automatically lists everything you exported in LEDTower1
        options = LEDTower1.__all__
        for i, opt in enumerate(options):
            print(f" [{i}] {opt}")
        print(" [B] Change Brightness (0-100)")
        print(" [Q] Quit")
        print("-" * 30)

        # 2. Get user input
        # We use run_in_executor so the terminal doesn't 'freeze' the LEDs
        loop = asyncio.get_event_loop()
        choice = await loop.run_in_executor(None, lambda: input("Select an option: ").strip().lower())

        # 3. Handle Quit
        if choice == 'q' or choice == 'quit':
            print("Shutting down LEDs...")
            if active_task: active_task.cancel()
            # Clear the LEDs before exiting
            for i in range(100): pixels[i] = (0,0,0)
            pixels.show()
            sys.exit()
        elif choice == 'b':
            b_input = await loop.run_in_executor(None, lambda: input("Enter brightness (0-100): "))
            try:
                # Convert 0-100 to 0.0-1.0
                new_b = float(b_input) / 100.0
                current_brightness = max(0.0, min(1.0, new_b))
                # Update the neopixel object directly
                pixels.brightness = current_brightness
                pixels.show()
                print(f"Brightness set to {int(current_brightness * 100)}%")
            except ValueError:
                print("Invalid number.")
        elif choice.isdigit() or choice in options:
            # 4. Run the Effect
            # Check if choice is a number or the name
            selected_effect = None
            if choice.isdigit():
                idx = int(choice)
                if idx < len(options):
                    selected_effect = options[idx]
            elif choice in options:
                selected_effect = choice

            if selected_effect:
                # Stop the previous animation
                if active_task and not active_task.done():
                    active_task.cancel()
                    try: await active_task
                    except asyncio.CancelledError: pass
                
                print(f"--- Running: {selected_effect} ---")
                # Default color and speed for the terminal mode
                effect_func = getattr(LEDTower1, selected_effect)
                active_task = asyncio.create_task(effect_func(pi_set_led, "#00ffee", 0.05))
            else:
                print("Invalid selection. Try again.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


    