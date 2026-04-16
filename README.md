

[README_ORIGINAL](README_ORIGINAL.md)



Internet Radio for Orange Pi Zero 2w adopted from Raspberry Pi code

This is a quick and dirty adaptation of code, done with the help of AI.

Thanks to Bob Rathbone for his project.



find . -type f -name "*.py" -exec sed -i 's/import RPi\.GPIO as GPIO/import OPi.GPIO as GPIO/g' {} \;

find . -type f -name "*.py" -exec sed -i 's/GPIO\.setmode(GPIO\.BCM)/GPIO.setmode(GPIO.BOARD)/g' {} \;

