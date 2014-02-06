# -*- coding: utf-8 -*-
"""
@author: Stefan Simis, Finnish Environment Institute SYKE 2014. Email firstname.lastname[_at_]environment.fi
Examples to illustrate the use of the PyTrios library.

updated 2014/02/06
"""

import PyTrios as ps
import matplotlib.pyplot as pp

"""general use"""
#open monitor on COM16
coms = ps.TMonitor(16)
#query the connected sensor(s)
ps.TCommandSend(coms[0],commandset=None,command='query')  
#set flag to temporarily stop monitoring (COM ports stay connected):
coms[0].threadactive.clear()
#set flag to continue monitoring:
coms[0].threadactive.set()
#close the listening threads and com ports 
ps.TClose(coms) 

"""SAM (spectrometer) examples"""
#query the connected sensor(s)
ps.TCommandSend(coms[0],commandset=None,command='query')    #general query module information

#start measurement on a SAM or SAMIP sensor:
#note first time a measurement starts on a SAMIP sensor it sends also the query results for each built-in module. SAM sensors do not do this.
ps.TCommandSend(coms[0],commandset='SAM',command='startIntAuto')            #measurement with automatic integration time and no additional addressing (i.e. SAM)
ps.TCommandSend(coms[0],commandset='SAM',par1='01',command='startIntSet')   #4ms int time #measurement with automatic integration time and no additional addressing (i.e. SAM)
#see the spectrum (pixels in the order received. UV/VIS sensors and UV sensors follow opposite pixel order, but we can't know what is connected)

addresses = coms[0].Tchannels.keys()
#to retrieve data, update the address below as necessary. Example for SAMIP connected directly to the COM port
pp.plot(coms[0].Tchannels['000080'].TSAM.lastRawSAM,marker='x')
pp.title(coms[0].Tchannels['000080'].TSAM.lastRawSAMTime)
#note that to calibrate SAM data, you still need to use the instrument calibration files provided by TriOS

ps.TClose(coms) #close the listening threads and com ports 

"""IPS examples"""
#query the connected sensor(s)
ps.TCommandSend(coms[0],commandset=None,command='query')     #general query module information which will trigger query on channels 1-4 automatically
addresses = coms[0].Tchannels.keys()
serialnumbers = [coms[0].Tchannels[i].TInfo.serialn for i in coms[0].Tchannels.keys()]
sensortypes = [coms[0].Tchannels[i].TInfo.ModuleType for i in coms[0].Tchannels.keys()]
print zip(addresses,serialnumbers,sensortypes)

ps.TClose(coms) #close the listening threads and com ports 

"""MicroFlu examples"""
#query the sensor, this example for a sensor on an IPS box, channel 3 
#for a MicroFlu sensor directly connected to a single COM port remove the ipschan argument
ps.TCommandSend(coms[0],commandset=None,command='query')
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='autoamp_on')             #
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='cont_on')  #stop continuous measurement
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='start')     #start one measurement

#Most MicroFlu sensors are configured to send data continuously on startup. 
#Set the verbose flag to display incoming measurements:
coms[0].verbose.set()
coms[0].verbose.clear() #to go silent again.

#some more commands
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='autoamp_on')             #
ps.TCommandSend(coms[0],ipschan='08',commandset='MicroFlu',command='autoamp_off')             #
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='lowamp_on')             #
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='lowamp_on')             #
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='cont_off')  #stop continuous measurement
#note that after a power cycle the settings are back to their default saved in the device EPROM

#inspect instrument properties from Tchannel attributes 
x = coms[0].TchannelDict['060000']
x.TMicroFlu #show some sensor info, you can also inspect the x.TMicroFlu.Settings attributes

#the startup defaults are saved in the ROMConfig attribute (you won't likely need any of this):
x = coms[0].TchannelDict['060000'].TMicroFlu.ROMConfig
x.Ampl, x.Auto, x.IntAvg #amplification, automatic or on demand sampling, internal averaging.

#data on address 060000:
coms[0].TchannelDict['060000'].TMicroFlu.lastFluRaw #format list [amplification,value]
coms[0].TchannelDict['060000'].TMicroFlu.lastFluCal #Calibrated output (according to calibration stored in sensor)
coms[0].TchannelDict['060000'].TMicroFlu.lastFluTime #Timestamp last measurement was received

#closing everything
ps.TClose(coms) #close the listening threads and com ports 
