# -*- coding: utf-8 -*-
"""
@author: Stefan Simis, Finnish Environment Institute SYKE 2014. Email firstname.lastname[_at_]environment.fi
Examples to illustrate the use of the PyTrios library.
"""

import PyTrios as ps
import matplotlib.pyplot as pp

"""general use"""
#open monitor on COM16
coms = ps.TMonitor(16)

ps.TCommandSend(coms[0],commandset=None,command='query')  #query module information

#set flag to temporarily stop monitoring (COM ports stay connected):
for c in coms:
    c.threadactive.clear()

#set flag to continue monitoring:
for c in coms:
    c.threadactive.set()

#closing monitoring threads for a clean exit:
for c in coms:
    c.threadactive.clear()
    c.threadlive.clear()

#close com ports 
ps.TClose(coms) 


"""SAM (spectrometer) examples"""
#query the sensor
ps.TCommandSend(coms[0],commandset=None,command='query')    #general query module information

#start measurement on a SAM or SAMIP sensor:
#note first time a measurement starts on a SAMIP sensor it sends also the query results for each built-in module. SAM sensors do not do this.
ps.TCommandSend(coms[0],commandset='SAM',command='startIntAuto')            #measurement with automatic integration time and no additional addressing (i.e. SAM)
ps.TCommandSend(coms[0],commandset='SAM',par1='01',command='startIntSet')   #4ms int time #measurement with automatic integration time and no additional addressing (i.e. SAM)
#see the spectrum (pixels in the order received. UV/VIS sensors and UV sensors follow opposite pixel order, but we can't know what is connected)
addresses = coms[0].TchannelDict.keys()
pp.plot(coms[0].TchannelDict['020030'].TlastRawdata,marker='x')  #update the address as necessary, this one is for a SAMIP on IPS box channel2.
pp.title(coms[0].TchannelDict['020030'].TlastTimestampPC)

#closing everything
for c in coms:
    c.threadactive.clear()
    c.threadlive.clear()

#close the com ports
ps.TClose(coms) 


"""IPS examples"""
#query the sensor
ps.TCommandSend(coms[0],commandset=None,command='query')     #general query module information which will trigger query on channels 1-4 automatically
addresses = coms[0].TchannelDict.keys()
serialnumbers = [coms[0].TchannelDict[i].Tserialn for i in coms[0].TchannelDict.keys()]
sensortypes = [coms[0].TchannelDict[i].TModuleType for i in coms[0].TchannelDict.keys()]
print zip(addresses,serialnumbers,sensortypes)

#closing everything
for c in coms:
    c.threadactive.clear()
    c.threadlive.clear()

ps.TClose(coms) #close the com ports

"""MicroFlu examples"""
#query the sensor, this example for a sensor on an IPS box, channel 3 
#for a MicroFlu sensor directly connected to a single COM port, remove the ipschan argument
ps.TCommandSend(coms[0],commandset=None,command='query')
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='autoamp_on')             #
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='cont_on')  #stop continuous measurement
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='start')     #start one measurement

#Most MicroFlu sensors are configured to send data continuously on startup. Set the verbose flag to display incoming measurements:
coms[0].verbose.set()
coms[0].verbose.clear() #to go silent again.

#some more commands
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='autoamp_on')             #
ps.TCommandSend(coms[0],ipschan='08',commandset='MicroFlu',command='autoamp_off')             #
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='lowamp_on')             #
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='lowamp_on')             #
ps.TCommandSend(coms[0],ipschan='06',commandset='MicroFlu',command='cont_off')  #stop continuous measurement
#note that after a reboot, the settings are back to their default saved in the device EPROM

#inspect instrument properties from Tchannel attributes 
x = coms[0].TchannelDict['060000']
x.TFtype      #MicroFlu type 1 is Chl, 2 is blue, 3 is CDOM
x.TSMit       #MicroFlu internal averaging
x.TCtlStart   #MicroFlu started/active
x.TCtlAnalog  #MicroFlu analog channel on
x.TCtlRange   #MicroFlu 0 = high gain, 1 = low gain
x.TCtlAutoR   #MicroFlu Autorange 1 on 0 off 
x.TCtlContn   #MicroFlu Datastream 0 On Demand / 1 Continuous
#the startup defaults are saved in the config attribute:
x = coms[0].TchannelDict['060000'].config
x.ROMAmpl, x.ROMAuto, x.ROMIntAvg #amplification, automatic or on demand sampling, internal averaging.

#data on address 060000:
coms[0].TchannelDict['060000'].TlastRawdata #format list [amplification,value]
coms[0].TchannelDict['060000'].TlastCaldata #format list [amplification,value]

#closing everything
for c in coms:
    c.threadactive.clear()
    c.threadlive.clear()

ps.TClose(coms) #close the com ports
