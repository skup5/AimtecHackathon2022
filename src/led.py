import sched
import time

import RPi.GPIO as GPIO    # Import Raspberry Pi GPIO library
from time import sleep     # Import the sleep function from the time module
GPIO.setwarnings(False)    # Ignore warning for now
GPIO.setmode(GPIO.BOARD)   # Use physical pin numbering
GPIO.setup(8, GPIO.OUT, initial=GPIO.LOW)   # Set pin 8 to be an output pin and set initial value to low (off)

class LedController:

    def turn_on(self):
        GPIO.output(8, GPIO.HIGH) # Turn on


    def turn_off(self):
        GPIO.output(8, GPIO.LOW) # Turn off


