from gpiozero import OutputDevice 
import time
pump = OutputDevice(23, active_high=False)
pump.on()
print("Pump on...")
time.sleep(24)
pump.off()
print("Pump Off...")
