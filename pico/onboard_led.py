from machine import Pin
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import _thread
led = Pin("LED", Pin.OUT)
    
async def flash_led(count=1):
    for i in range(count):
        led.on()
        await asyncio.sleep(0.2)
        led.off()
        await asyncio.sleep(0.2)