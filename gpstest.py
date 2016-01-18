#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

What documentation!

Created on Fri Jan 15 10:41:10 2016


user running this needs to be part of 'dialout' group, try:
sudo gpasswd --add ${USER} dialout


"""
__author__ = 'stsi'

import os
import numpy as np
import sys
from pytrios import gpslib
import serial
import time

ser = serial.Serial('COM7', baudrate=4800)  # open serial port
if not ser.isOpen:
    ser.open()
if not ser.isOpen:
    print("Could not open GPS serial port")
    # sys.exit(1)    

gps = gpslib.GPSManager()
gps.add_serial_port(ser)
gps.start()

for i in range(10):
    print gps.fix_type, gps.fix_quality, gps.old, gps.datetime, gps.lat, gps.lon, gps.speed
    time.sleep(1)

