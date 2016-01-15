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
from pytrios import gpslib

import serial
ser = serial.Serial('/dev/ttyUSB0')  # open serial port

gps = gpslib.GPSManager()
gps.add_serial_port(gps_serial_port)


gps.register_observer()