from machine import Pin
import time

led = Pin("LED", Pin.OUT)
print("Pico 2W на связи")

for i in range(10):
    led.toggle()
    print(f"tick {i}")
    time.sleep(0.3)

led.off()
print("done")
