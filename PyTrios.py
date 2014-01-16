# -*- coding: utf-8 -*-
"""
PyTrios implements serial communication with TriOS sensors in the Python language\n

Copyright (C) 2014  Stefan Simis for the Finnish Environment Institute SYKE\n
Email firstname.lastname[_at_]environment.fi

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

Note: PyTrios builds on the *serial* module by Chris Liechti

Tested on Python 2.7.3\n
Last update 16 Jan 2014\n

*For example use please see the enclosed PyTrios_Examples.py script.*

Basic use:
    
>>>import PyTriosSerial as ps\n
#monitor com port 16:
>>>coms = ps.TMonitor(16)\n
#verbose monitoring on:\n
>>>coms[0].verbose.set()\n 
#Query connected sensors:\n
>>>ps.TCommandSend(coms[0],commandset=None,command='query')\n
#sample on a SAM sensor connected directly to the COM port (i.e. without multichannel IPS interface):\n
>>>ps.TCommandSend(coms[0],commandset='SAM',command='startIntAuto')\n
#for a MicroFlu sensor:\n
#turn off continuous sampling in MicroFlu module:\n
>>>ps.TCommandSend(coms[0],commandset='MicroFlu','cont_off')\n
#single measurement in MicroFlu module:\n
>>>ps.TCommandSend(coms[0],commandset='MicroFlu','start')\n 
#pause monitoring: (does not close COM port)\n
>>>for c in coms:\n
    c.threadactive.clear()\n
#continue monitoring:\n
>>>for c in coms:\n
    c.threadactive.set()\n
#terminate monitoring threads on program end:\n
>>>for c in coms:\n
    c.threadlive.clear\n
#close com ports:\n
>>>ps.TClose(coms)\n
"""
import serial
import time
import datetime
import struct
import numpy as np
import threading

__version__ = "2014.01.16"

class TProtocolError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class TPacket: 
    """store everything read from a single TrioS sensor data package"""
    def __init__(self, TimeStampPC=datetime.datetime.now(), id1=None, id1_databytes=None, id1_fut=None, id1_id = None, id2=None, ModuleID=None, ModuleID_zipped = None, ModuleID_I2Cadd = None, Time1=None, Time2=None, Framebyte = None, DataVals = None, Checkbyte = None, Databytes = None, PacketType=None):
        self.TimeStampPC = TimeStampPC
        self.id1, self.id1_databytes, self.id1_fut, self.id1_id = id1, id1_databytes, id1_fut, id1_id
        self.id2 = id2
        self.ModuleID, self.ModuleID_zipped, self.ModuleID_I2Cadd = ModuleID, ModuleID_zipped, ModuleID_I2Cadd
        self.Time1, self.Time2 = Time1, Time2
        self.Framebyte = Framebyte
        self.Databytes = Databytes
        self.DataVals = DataVals
        self.Checkbyte = Checkbyte
        self.PacketType = PacketType

class TChannel: 
    """store information on a TrioS channel, needed e.g. to interpret data packages"""
    def __init__(self, TID = None, Tserialn=None, TModuleType=None, TFirmware=None, TModFreq=None, TFtype=None, TSMit=None, TCtlStart=None, TCtlAnalog=None,TCtlRange=None, TCtlAutoR=None, TCtlContn=None, TSAMspectrumframes = [[None]]*8, TlastRawdata=None, TlastCaldata = None, TlastTimestampPC = None, TMaster=None):
        self.TID = TID
        self.Tserialn = Tserialn
        self.TModuleType = TModuleType
        self.TFirmware = TFirmware
        self.TModFreq = TModFreq
        self.TFtype = TFtype            #MicroFlu type 1 is Chl, 2 is blue, 3 is CDOM
        self.TSMit = TSMit              #MicroFlu internal averaging
        self.TCtlStart = TCtlStart      #MicroFlu started/active
        self.TCtlAnalog = TCtlAnalog    #MicroFlu analog channel on
        self.TCtlRange = TCtlRange      #MicroFlu 0 = high gain, 1 = low gain
        self.TCtlAutoR = TCtlAutoR      #MicroFlu Autorange 1 on 0 off 
        self.TCtlContn = TCtlContn      #MicroFlu Datastream 0 On Demand / 1 Continuous
        self.TSAMspectrumframes = TSAMspectrumframes
        self.TlastRawdata = TlastRawdata
        self.TlastCaldata = TlastCaldata
        self.TlastTimestampPC = TlastTimestampPC
        self.TMaster = TMaster

def TConnectCOM(port,timeout=0.01,baudrate=9600,xonxoff=True,parity='N',stopbits=1,bytesize=8):
    """Create a serial object for a TriOS sensor on a COM port with default TriOS serial settings. \n\n *port* = *int* or *str* indicating COM port number, e.g. port=16, port=COM16, port='16' all work.\n"""
    try:
        port = str(port)
        port = "COM"+port.capitalize().strip('COM')
        ser = serial.Serial(port)
        ser.baudrate, ser.timeout, ser.xonxoff = baudrate, timeout, xonxoff
        ser.parity, ser.stopbits, ser.bytesize = parity, stopbits, bytesize
        return ser
    except serial.SerialException:
            print("Error connecting to port: "+port) #don't raise
    except ValueError:
            print("Value error in TriosConnectCOM: "+port) #don't raise
    except:
        raise

def TMonitor(ports):
    """Initiate serial port listening threads. Start here."""
    try:
        if not type(ports) is list:
            ports = [ports]
        COMobjslst = []
        for p in ports:
            ser = TConnectCOM(p,timeout=0.01,baudrate=9600, xonxoff=True, parity='N',stopbits=1,bytesize=8)
            #ser.Tchannel = TChannel()
            ser.TchannelDict={}                     #this will store TChannel objects
            ser.threadlisten = threading.Thread(target=TListen, args=(ser,)) #associated port listening thread
            ser.threadlive = threading.Event()      #clear to stop the thread (cannot be restarted once stopped)
            ser.threadactive = threading.Event()    #clear to stop thread from polling port, does not stop the thread but you could remove the port object
            ser.verbose = threading.Event()         #print more
            ser.verbosehex = threading.Event()      #print hex packets
            ser.threadlive.set()                    #intended as UI switch
            ser.threadactive.set()                  #intended as UI switch
            ser.verbose.clear()                     #intended as UI switch
            ser.verbosehex.clear()                  #intended as UI switch
            COMobjslst.append(ser)
            ser.threadlisten.start()                #start thread
            ser.threadlisten.join(0.01)             #join and return to calling thread
        return COMobjslst
    except:
        for c in COMobjslst:
            c.threadactive.clear()
            c.threadlive.clear()
            c.close()
            print "General Exception caught. Attempted to close TMonitor threads and serial connections"
        raise

def TListen(ser):
    """Monitors and maintains a serial port instance *ser*"""
    s=""
    timeouttimer = 0
    while ser.threadlive.isSet():
        while ser.threadactive.isSet():
            try:
                bitsatport = ser.inWaiting()
                if bitsatport>0 or len(s)>0:
                    s = s+ser.read(1000)                    # add new string to buffer
                    first, last = s.find('#'), s.rfind('#') # look for start chars
                    s = TStrRepl(s)                         # correct replacement chars
                    if first > -1 and last >= first:        # at least one data packet found
                        s = s[s.find('#',0):]               # cut any incomplete sequence away from start, it will not recur
                        len_s = len(s)                      # start checking if a complete packet is present
                        if len_s>1:                         # if one byte follows the # char, we know expected data size
                            ndatabytes = 2*2**(ord(s[1]) >> 5)
                            blocklength = 8+ndatabytes      #1xstart+2xID+1xModule+1xframebyte+2xtime+1xcheckbyte = 8 bytes
                            if len_s>=blocklength:          #should form a complete packet
                                s2parse = s[1:blocklength]  # the block to parse
                                if ser.verbosehex.isSet():
                                    print "TListen:", ":".join("{0:x}".format(ord(c)) for c in s2parse)
                                s = s[blocklength:]         # the remains to be used in the next cycle
                                timeouttimer = 0            # reset timeout timer for incomplete packages
                                packet = TSerial_parse(s2parse) #needs to be sent on to packet handler
                                if ser.verbose.isSet():
                                    print "TListen:", packet.TimeStampPC, packet.PacketType
                                ser, packet = TPacketInterpreter(ser, packet)
                            else: #there is an incomplete packet. At the timeout we flush it out of the buffer s to prevent it from holding up other packets
                                if timeouttimer-time.time() > 1: #check an existing timer against timeout
                                    s="" #clear the buffer
                                    raise TProtocolError("Timeout when parsing serial buffer")
                                else:
                                    if timeouttimer == 0:  #set a new timer
                                        timeouttimer = time.time()
                time.sleep(0.05) # prevent process from taking over all CPU cycles
            except TProtocolError as e:
                print e.message, ser.port
                pass
            except Exception:
                raise
        time.sleep(1) # check every second weather threadactive is Set

def TClose(COMs):
    if not type(COMs) is list:
        COMs = [COMs]
    for c in COMs:
        try:
            c.close()
        except Exception:
            pass

def TSerial_parse(s2parse): 
    """Parse a TriOS binary data packet"""
    try:
        packet = TPacket()
        packet.TimeStampPC = datetime.datetime.now() #time of parsing
        #identity byte 1        
        packet.id1 = ord(s2parse[0])
        packet.id1_databytes = 2*2**(ord(s2parse[0]) >> 5) #3 most sign bits give size of data frame 
        packet.id1_fut = (ord(s2parse[0]) & 0b10000)>>4    #5th bit is for future compatibility
        packet.id1_id = ord(s2parse[0]) & 0b1111           #first 4 lsb are identity bits
        if packet.id1_databytes is 256:              #error defined in TriOS protocol
            raise TProtocolError("TSerial_parse: Blocksize invalid")
        formatstring = '<BBBBBB'+str(packet.id1_databytes)+'BB'
        try:
            Data = struct.unpack(formatstring,s2parse)
        except:
            raise TProtocolError("TSerial_parse: unknown error unpacking Data block")
        #interpret framebyte and databytes
        #identity byte 2
        packet.id2 = Data[1]
        #module ID byte
        packet.ModuleID = Data[2]
        packet.ModuleID_zipped = Data[2] & 0b1     # zipped data if 1, original data if 0
        packet.ModuleID_I2Cadd = Data[2] >> 1      # Module I2C address in 7 msb
        #Framebyte, 0=single or last frame, 255=module info, 254=error message
        packet.Framebyte = Data[3]     
        packet.Time1= Data[4]          # 0 = no realtime clock
        packet.Time2= Data[5]          # 0 = no realtime clock
        packet.Databytes = Data[6:6+packet.id1_databytes]
        packet.Checkbyte= Data [-1] # not used
        #PacketType
        if packet.Framebyte is 254:    #error defined in TriOS protocol
            packet.PacketType = 'error/invalid'
            raise TProtocolError("TSerial_parse: Instrument reports error, wrong command sent?")
        if packet.Framebyte is 255:    # framebyte: 0=single or last frame, 255=module info, 254=error message
            packet.PacketType = 'query'
        if packet.Framebyte <254: # observation data are communicated
            packet.PacketType = 'measurement'
        return packet
    except TProtocolError as e:
        print e.message
        print "TSerial_parse: Error while parsing Trios data packet. Info:"
        print "TSerial_parse: Packet: ", ":".join("{0:x}".format(ord(c)) for c in s2parse) #string in pretty hex
        return packet
        pass    
    except Exception: #any uncaught error
        return packet
        raise

def TPacketInterpreter(ser, packet):
    """Interpret Trios data packet according to source instrument communication standards"""
    try:
        if packet.ModuleID == 164: #MicroFlu configuration package (address A4)
            print "Interpreter: received MicroFlu configuration on", ser.port
            packet.PacketType = 'config'
            try:
                TID = hex(packet.id1_id)[2:].zfill(2) + hex(packet.id2)[2:].zfill(2)+"00"
                ser.TchannelDict[TID].config = packet
                ser.TchannelDict[TID].config.ROMIntAvg = packet.Databytes[3]
                ser.TchannelDict[TID].config.ROMAuto = (packet.Databytes[4] & 0b00001000)>>3  #1 is Start measuring on startup
                ser.TchannelDict[TID].config.ROMAmpl = packet.Databytes[4]>>4                 #0/1/2 = high/auto/low
                ser.TchannelDict[TID].config.ROMHighA_Offset = np.float(packet.Databytes[5]*256 + packet.Databytes[6])
                ser.TchannelDict[TID].config.ROMLowA_Offset =  np.float(packet.Databytes[7]*256 + packet.Databytes[8])
                ser.TchannelDict[TID].config.ROMHighA_Scale = np.float(packet.Databytes[9]) + np.float(packet.Databytes[10])/256
                ser.TchannelDict[TID].config.ROMLowA_Scale = np.float(packet.Databytes[11]) + np.float(packet.Databytes[12])/256
                return ser, packet
            except:
                print "Interpreter: error interpreting config package"
                pass
        if packet.PacketType is 'query':
            serlow = packet.Databytes[0]        # in serial number ### this is the last 2 hex chars
            serhi = packet.Databytes[1]         # in serial number #### this is the first 2 hex chars
            vals,types = [2,4,8,9,10,12,16,20,24], ['MicroFlu','IOM','COM','IPS','SAMIP','SCM','SAM','DFM','ADM']
            #thisTchannel = TChannel(TID = str(packet.id1_id).zfill(2) + str(packet.id2).zfill(2)+str(packet.ModuleID).zfill(2))
            thisTchannel = TChannel(TID = hex(packet.id1_id)[2:].zfill(2) + hex(packet.id2)[2:].zfill(2)+hex(packet.ModuleID)[2:].zfill(2))
            thisTchannel.Tserialn = str.upper(hex(serhi)[-2::]+hex(serlow)[-2::]) #serial as quoted on instrument
            thisTchannel.TModuleType = types[vals.index(serhi>>3)]                # module type from 5 most sign Bits
            thisTchannel.TFirmware = packet.Databytes[3]+0.01*packet.Databytes[2]
            thisTchannel.TModFreq = [np.nan,2,4,6,8,10,12,20][packet.Databytes[4]]#operating freq. in MHz
            if thisTchannel.TModuleType is 'MicroFlu':
                thisTchannel.TFtype = packet.Databytes[5]                         #1 = chl; 2 = blue, 3 is CDOM
                thisTchannel.TSMit = packet.Databytes[6]                          #Internal averaging n samples
                thisTchannel.TCtlStart = (packet.Databytes[7] & 0b10000000)>>7    #bit 7 = sampling is active
                thisTchannel.TCtlAnalog = (packet.Databytes[7] & 0b01000000)>>6   #bit 6 Analog Power (0=OFF, 1=ON)
                thisTchannel.TCtlRange = (packet.Databytes[7] & 0b00100000)>>5    #Bit 5: Range (0= highAmp, 1= lowAmp)
                thisTchannel.TCtlAutoR = (packet.Databytes[7] & 0b00010000)>>4    #Bit 4: AutoRange (0= OFF, 1= ON)
                thisTchannel.TCtlContn = (packet.Databytes[7] & 0b00001000)>>3    #Bit 3: Datastream (0= OnDemand, 1= Continously)
                #a query command on a MicroFlu can be followed by a ROM Config request for more sensor info
                TCommandSend(ser,commandset='MicroFlu',ipschan=thisTchannel.TID[0:2],command='ReadCfg')
                #after config request reset the sensor to previous sampling state
                if thisTchannel.TCtlContn == 0:
                    TCommandSend(ser,commandset='MicroFlu',ipschan=thisTchannel.TID[0:2],command='cont_off')
                else:
                    TCommandSend(ser,commandset='MicroFlu',ipschan=thisTchannel.TID[0:2],command='cont_on')
            print "Interpreter:", packet.TimeStampPC, "Query result from", thisTchannel.TModuleType, "on", ser.port, hex(packet.id1_id), hex(packet.id2), hex(packet.ModuleID), thisTchannel.Tserialn, thisTchannel.TModuleType
            if thisTchannel.TModuleType in['SAM','SAMIP']:
                thisTchannel.SAMConfiguration = packet.Databytes[5]
                thisTchannel.SAMRange = packet.Databytes[6]
                thisTchannel.SAMStatus = packet.Databytes[7]
            ser.TchannelDict[thisTchannel.TID]=thisTchannel
            if thisTchannel.TModuleType is 'IPS':
                for c in ['02','04','06','08']:
                    TCommandSend(ser,commandset=None,ipschan=c,command='query') #query submodule information
        if packet.PacketType is 'measurement':
            TID = hex(packet.id1_id)[2:].zfill(2) + hex(packet.id2)[2:].zfill(2)+hex(packet.ModuleID)[2:].zfill(2)
            if ser.verbose.isSet():
                print "Interpreter:",packet.TimeStampPC, "Measurement on",ser.port,", Address",TID,", Type",ser.TchannelDict[TID].TModuleType
            if ser.TchannelDict[TID].TModuleType is 'MicroFlu':
                formatstring = '>'+'H'*int(packet.id1_databytes/2) #byteorder is big endian although documentation suggests different
                BEdata = struct.unpack(formatstring,''.join([chr(y) for y in packet.Databytes]))
                gain = BEdata[0] >> 15  #0 means high gain, 1 means low gain
                data = BEdata[0] & 0b111111111111
                ser.TchannelDict[TID].TlastRawdata = [gain,data]
                ser.TchannelDict[TID].TlastTimestampPC = packet.TimeStampPC
                if gain == 1:
                    ser.TchannelDict[TID].TlastCaldata = 100*data/np.float(2048)
                if gain == 0:
                    ser.TchannelDict[TID].TlastCaldata = 10*data/np.float(2048)
                if ser.verbose.isSet():
                    gains,ftypes = ['H','L'], [None,'Chl','Blue','CDOM']
                    print "Interpreter: Microflu-"+ftypes[ser.TchannelDict[TID].TFtype]+" data from", ser.port, "Gain:",gain,"("+gains[gain]+")","Raw Value:",data, "Cal. value:",ser.TchannelDict[TID].TlastCaldata
            if ser.TchannelDict[TID].TModuleType is 'SAM':
                if ser.verbose.isSet():
                    print "Interpreter: SAM frame:", packet.Framebyte, "with", packet.id1_databytes, " databytes on Module:",ser.TchannelDict[TID].Tserialn
                formatstring = '<'+'H'*int(packet.id1_databytes/2)
                LEdata = struct.unpack(formatstring,''.join([chr(y) for y in packet.Databytes]))
                ser.TchannelDict[TID].TSAMspectrumframes[packet.Framebyte]=LEdata
                if packet.Framebyte == 0:
                    frames = ser.TchannelDict[TID].TSAMspectrumframes
                    if sum(y is None for y in frames)==0:
                        ser.TchannelDict[TID].TlastRawdata = [item for sublist in frames for item in sublist]
                        ser.TchannelDict[TID].TlastTimestampPC = packet.TimeStampPC
                        if int(ser.TchannelDict[TID].TID[-2:])>0: #is a module in another instrument
                            ser.TchannelDict[TID].TMaster = ser.TchannelDict[ser.TchannelDict[TID].TID[0:4]+'80'].Tserialn
                        print "Interpreter: Spectrum received at", ser.port, "address",ser.TchannelDict[TID].TID, "module",ser.TchannelDict[TID].Tserialn
                    else:
                        print "Interpreter: Incomplete spectrum received and discarded"
                        raise TProtocolError("Interpreter: Incomplete spectrum received and discarded")
                    ser.TchannelDict[TID].TSAMspectrumframes=[[None]]*8 #reset to receive the next spectrum
            if ser.TchannelDict[TID].TModuleType is 'ADM':
                print "Interpreter: ADM measurement received (not implemented) address", TID, packet.id1_databytes,"bytes, Module:",ser.TchannelDict[TID].Tserialn, ", Instrument:",ser.TchannelDict['000080'].Tserialn
        return ser, packet
    except TProtocolError as e:
        print e.message
        return ser, packet
        pass
    except KeyError:
        print "Interpreter: KeyError, probably unidentified sensor on:",ser.port,"? (send query to resolve)"
        return ser, packet
        pass
    except Exception:
        print "Interpreter: Uncaught error"
        raise #debug
        return ser,packet

def TStrRepl(s):
    s = s.replace('@g','\x13')  # correct for escape chars (xOFF)
    s = s.replace('@f','\x11')  # correct for escape chars (xOn)
    s = s.replace('@e','\x23')  # correct for escape chars (data start #)
    s = s.replace('@d','\x40')  # correct for escape chars (escape char @)
    return s

def TCommandSend(ser,commandset,command='query', ipschan='00', par1='00',par2='00'):
    """send a command from a module specific command set to a TriOS device.\n
    Device reconfiguration is not supported.\n

    Command sets implemented:
        QUERY, not instrument specific: TCommandSend(ser,None,'query')
        *MicroFlu*  e.g. TCommandSend(ser,'MicroFlu',command='cont_off')
        *SAM*       e.g. TCommandSend(ser,'SAM',command='startIntAuto')

    For sensors on an IPS4 box, specify the channel as *ipschan* = '02','04','06','08' for channels 1-4 respectively.\n\n
    *par1* is the first user-configurable parameter mentioned in the documentation, even when listed as parameter2 in the docs. Most commands require only one argument.\n\n
    *par2* is only included for future use but not referenced in the current command set.
    """
    #TODO escape the control characters if they should occur in any command?
    commandsetdict = {None:0,'MicroFlu':1,'SAM':2,}
    commanddict = ['']*len(commandsetdict)
    commanddict[0] = {'query':bytearray.fromhex("23 "+str(ipschan)+" 00 80 B0 00 00 01")}
    commanddict[1] = {\
        'ReadCfg'    : bytearray.fromhex("23 "+ipschan+" 00 00 c0 00 00 01 23 "+ipschan+" 00 00 08 00 03 01 23 "+ipschan+" 00 00 08 00 04 01 23 "+ipschan+" 00 00 a0 a4 10 01"),\
        'cont_on'    : bytearray.fromhex("23 "+str(ipschan)+" 00 00 78 0f 01 01"),\
        'cont_off'   : bytearray.fromhex("23 "+str(ipschan)+" 00 00 78 0f 00 01"),\
        'query'      : bytearray.fromhex("23 "+str(ipschan)+" 00 00 B0 00 00 01"),\
        'reboot'     : bytearray.fromhex("23 "+str(ipschan)+" 00 00 00 00 00 01"),\
        'start'      : bytearray.fromhex("23 "+str(ipschan)+" 00 00 A8 00 81 01"),\
        'stop'       : bytearray.fromhex("23 "+str(ipschan)+" 00 00 A8 00 82 01"),\
        'autoamp_on' : bytearray.fromhex("23 "+str(ipschan)+" 00 00 78 06 01 01"),\
        'autoamp_off': bytearray.fromhex("23 "+str(ipschan)+" 00 00 78 06 00 01"),\
        'lowamp_on'  : bytearray.fromhex("23 "+str(ipschan)+" 00 00 78 05 01 01"),\
        'lowamp_off' : bytearray.fromhex("23 "+str(ipschan)+" 00 00 78 05 00 01"),\
        'int_avg'    : bytearray.fromhex("23 "+str(ipschan)+" 00 00 78 04 "+str(par1)+" 01"),\
        }
    #SAM address is 80, SAMIP has main address 80, but address 20 for IP and 30 for SAM specific commands
    commanddict[2] = {\
        'reboot'      : bytearray.fromhex("23 "+str(ipschan)+" 00 80 00 00 00 01"),\
        'startIntAuto': bytearray.fromhex("23 "+str(ipschan)+" 00 30 78 05 00 01 23 "+str(ipschan)+" 00 80 A8 00 81 01"),\
        'startIntSet' : bytearray.fromhex("23 "+str(ipschan)+" 00 30 78 05 "+str(par1)+" 01 23 "+str(ipschan)+" 00 80 A8 00 81 01"),\
        'cont_mode_off': bytearray.fromhex("23 "+str(ipschan)+" 00 30 78 F0 02 01"),\
        'cont_mode_on' : bytearray.fromhex("23 "+str(ipschan)+" 00 30 78 F0 03 01"),\
        'setIntTime'  : bytearray.fromhex("23 "+str(ipschan)+" 00 30 78 05 "+str(par1)+" 01"),\
        'sleep'       : bytearray.fromhex("23 "+str(ipschan)+" 00 80 A0 00 00 01"),\
        'setbaud'     : bytearray.fromhex("23 "+str(ipschan)+" 00 80 50 01 "+str(par1)+" 01"),\
        }
    command = commanddict[commandsetdict[commandset]][command]
    try:
        if ser.outWaiting()>0:
            ser.flush()
        ser.write(command)
    except serial.SerialException as e:
        print e.message
        pass
    except KeyError:
        print "TCommandSend: Command or command set not recognized"
        pass
    except Exception:
        print "TCommandSend: Unidentified error, please check command format"
        pass