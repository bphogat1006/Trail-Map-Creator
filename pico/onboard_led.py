from machine import Pin
from utime import sleep
import _thread
led = Pin("LED", Pin.OUT)

def flash(count):
    for i in range(count):
        led.on()
        sleep(0.2)
        led.off()
        sleep(0.2)
    
def flash_led(count=1, synchronous=True):
    if synchronous:
        flash(count)
    else:
        _thread.start_new_thread(flash, (count))
