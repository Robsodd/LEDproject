#include <TFT_eSPI.h>
#include <lvgl.h>
#include "driver/rtc_io.h" 
#include "ui.h"

// --- Global Touch Offsets ---
int touch_offset_x = 0;
int touch_offset_y = -20;

// Screen dimensions for 3.2" Display
static const uint16_t screenWidth  = 320;
static const uint16_t screenHeight = 240;

TFT_eSPI tft = TFT_eSPI(screenWidth, screenHeight); 

static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf[ screenWidth * screenHeight / 10 ];

// --- Graphics Flush Function ---
void my_disp_flush( lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p ) {
    uint32_t w = ( area->x2 - area->x1 + 1 );
    uint32_t h = ( area->y2 - area->y1 + 1 );
    tft.startWrite();
    tft.setAddrWindow( area->x1, area->y1, w, h );
    tft.pushColors( ( uint16_t * )&color_p->full, w * h, true );
    tft.endWrite();
    lv_disp_flush_ready( disp );
}

// --- TFT_eSPI Native Touch Reading Function ---
void my_touchpad_read( lv_indev_drv_t * indev_driver, lv_indev_data_t * data ) {
    uint16_t touchX, touchY;
    
    bool touched = tft.getTouch(&touchX, &touchY);

    if(touched) {
        data->state = LV_INDEV_STATE_PR;
        
        // --- MANUAL CALIBRATION OFFSET ---
        int16_t finalX = touchX + touch_offset_x;
        int16_t finalY = touchY + touch_offset_y; 

        // Safety check to prevent crashing LVGL
        if (finalX < 0) finalX = 0;
        if (finalX > screenWidth) finalX = screenWidth;
        if (finalY < 0) finalY = 0;
        if (finalY > screenHeight) finalY = screenHeight;

        data->point.x = finalX;
        data->point.y = finalY;
        
    } else {
        data->state = LV_INDEV_STATE_REL;
    }
}

void setup() {
    Serial.begin(115200);
    
    // Give the Serial Monitor 3 seconds to catch up
    delay(3000); 
    Serial.println("\n\n--- ESP32 BOOTING ---");

    Serial.println("Releasing RTC Pin...");
    rtc_gpio_deinit((gpio_num_t)27); 
    pinMode(27, OUTPUT);
    digitalWrite(27, HIGH); 

    Serial.println("Starting TFT...");
    tft.begin();
    tft.setRotation(1); 
    
    Serial.println("Setting Touch Cal...");
    uint16_t calData[5] = { 403, 3564, 223, 3671, 3 }; 
    tft.setTouch(calData);

    Serial.println("Init LVGL...");
    lv_init();
    lv_disp_draw_buf_init( &draw_buf, buf, NULL, screenWidth * screenHeight / 10 );
    static lv_disp_drv_t disp_drv;
    lv_disp_drv_init( &disp_drv );
    disp_drv.hor_res = screenWidth;
    disp_drv.ver_res = screenHeight;
    disp_drv.flush_cb = my_disp_flush;
    disp_drv.draw_buf = &draw_buf;
    lv_disp_drv_register( &disp_drv );

    Serial.println("Init Touch Input...");
    static lv_indev_drv_t indev_drv;
    lv_indev_drv_init( &indev_drv );
    indev_drv.type = LV_INDEV_TYPE_POINTER;
    indev_drv.read_cb = my_touchpad_read;
    
    // Capture the registered input device
    lv_indev_t * indev_touchpad = lv_indev_drv_register( &indev_drv );

    // --- CREATE THE CALIBRATION CURSOR ---
    lv_obj_t * cursor_obj = lv_obj_create(lv_layer_sys()); 
    lv_obj_set_size(cursor_obj, 10, 10);
    lv_obj_set_style_radius(cursor_obj, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(cursor_obj, lv_palette_main(LV_PALETTE_RED), 0);
    lv_obj_set_style_border_width(cursor_obj, 0, 0); 
    lv_obj_clear_flag(cursor_obj, LV_OBJ_FLAG_CLICKABLE); 
    
    lv_indev_set_cursor(indev_touchpad, cursor_obj);
    // -------------------------------------

    Serial.println("Starting UI...");
    ui_init(); 
    
    Serial.println("Setup Complete! Entering loop.");
}

void loop() {
    lv_tick_inc(5); 
    lv_timer_handler(); 
    delay(5);
}