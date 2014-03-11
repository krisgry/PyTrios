# -*- coding: utf-8 -*-
"""
Implements serial communication with TriOS sensors in the Python language\n

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
Last update: see __version__\n

*For example use please see the enclosed PyTrios_Examples.py script.*
"""
import serial
import time
import datetime
import struct
import numpy as np
import threading

__version__ = "2014.03.11"

class TProtocolError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class TPacket(object): 
    """TrioS sensor data package object"""
    def __init__(self, TimeStampPC=datetime.datetime.now(), id1=None, 
                 id1_databytes=None, id1_fut=None, id1_id = None, id2=None, 
                 ModuleID=None, ModuleID_zipped = None, ModuleID_I2Cadd = None, 
                 Time1=None, Time2=None, Framebyte = None, DataVals = None, 
                 Checkbyte = None, Databytes = None, PacketType=None):
        pass
    def __repr__(self):
        return ("<PyTrios TPacket, Timestamp=%s, Framebyte=%s, PacketType=%s>" %
                (self.TimeStampPC, self.Framebyte, self.PacketType))

class SAMSettings(object):
    def __init__(self,SAMConfiguration = None, SAMRange = None, 
                 SAMStatus =None): pass

class TSAM(object):
    """Stores data from connected MicroFlu instrument:\n
    *Settings* = Sensor specific settings\n
    *lastRawSAM* = last uncalibrated spectrum from SAM unit\n
    *lastRawSAMTime* = Reception timestamp of last spectrum\n"""
    def __init__(self,Settings=SAMSettings, dataframes=[[None]]*8,lastRawSAM=None,lastRawSAMTime=None):
        self.Settings = Settings()
        self.dataframes = dataframes
    def __repr__(self):
        try:
            return ("<PyTrios SAM, last measurement received at %s>" %
                (self.lastRawSAMTime))
        except: return str(None)

class TInfo(object):
    """Basic information about connected instrument:\n
    *TID* = Address\n
    *ModuleType* = SAM, SAMIP, MicroFlu\n
    *Firmware* = Sensor firmware\n
    *ModFreq* = Sensor internal frequency\n"""
    def __init__(self,TID=None,ModuleType=None,Firmware=None,ModFreq=None,serialn=None):
        self.TID = TID
        self.ModuleType=ModuleType
        self.Firmware = Firmware
        self.ModFreq = ModFreq
        self.serialn = serialn
    def __repr__(self):
        return ("<PyTrios Instrument, TID=%s, serialn=%s, ModuleType=%s, Firmware=%s>" %
            (self.TID, self.serialn, self.ModuleType, self.Firmware))
            
class MFSettings(object):
            """Microflu sensor specific settings\n
            *Ftype*:     1/2/3 = Chl, blue, CDOM\n*Mit*: internal averaging\n
            *CtlStart*: sensor is active\n*CtlAnalog*:analog output on\n
            *CtlRange*: 0/1 = high/low gain\n*CtlAutoR*: 1/0 = Auto-range On/Off\n
            *CtlContn*: 0/1 = On Demand / Continuous\n"""
            def __init__(self, Ftype=None, SMit=None, 
                         CtlStart=None, CtlAnalog=None,CtlRange=None,
                         CtlAutoR=None, CtlContn=None): pass

class MFROMConfig(object):
    """"IntAvg, Auto, Ampl, HighA_Offset, LowA_Offset, HighA_Scale, LowA_Scale"""
    def __init__(self, IntAvg=None, Auto=None, Ampl=None,
                 HighA_Offset=None, LowA_Offset=None, 
                 HighA_Scale=None, LowA_Scale=None): pass

class TMicroFlu(object):
        """Stores data from connected MicroFlu instrument:\n
        *Settings* = Sensor specific settings\n*ROMConfig* = Sensor startup configuration\n
        *lastFluRaw* = last raw measurement (amplification, value)\n
        *lastFluCal* = last calibrated measurement\n*lastFluTime* = local timestamp of last measurement\n"""
        def __init__(self,Settings=MFSettings,ROMConfig=MFROMConfig,
                     lastFluRaw=None,lastFluCal=None,lastFluTime=None):
            self.Settings = Settings()
            self.ROMConfig = ROMConfig()
        def __repr__(self):
            ftypes = ['','Chl','Blue','CDOM']
            try:
                return ("<PyTrios MicroFlu-%s, Averaging=%s, Continuous=%s, Autorange=%s, last measurement=%s: %s>" %
                (ftypes[self.Settings.Ftype], self.Settings.Mit, self.Settings.CtlContn,\
                self.Settings.CtlAutoR, self.lastFluTime, self.lastFluCal))
            except: return str(None)

class TChannel(object):
    """Stores Trios Instrument info/data, identified by address (self.TID)"""
    def __init__(self,TInfo=TInfo,TMicroFlu=TMicroFlu,TSAM=TSAM):
        self.TInfo = TInfo()
        self.TMicroFlu = TMicroFlu()
        self.TSAM = TSAM()

def TConnectCOM(port,timeout=0.01,baudrate=9600,xonxoff=True,parity='N',
                stopbits=1,bytesize=8):
    """Create a serial object for a TriOS sensor on a COM port with default 
    TriOS serial settings. \n\n *port* = *int* or *str* indicating COM port 
    number, e.g. port=16, port=COM16, port='16' all work.\n"""
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
            ser = TConnectCOM(p,timeout=0.01,baudrate=9600, xonxoff=True, 
                              parity='N',stopbits=1,bytesize=8)
            ser.Tchannels={}                 #stores TChannel objects
            #associated port listening thread
            ser.threadlisten = threading.Thread(target=TListen, args=(ser,)) 
            ser.threadlive = threading.Event()  #clear stops thread permanently
            ser.threadactive = threading.Event()#clear pauses thread
            ser.verbosity = 1                   #UI switch. 0/1/2/3 = none, queries(default), measurements, all
            ser.threadlive.set()                #intended as UI switch
            ser.threadactive.set()              #intended as UI switch
            COMobjslst.append(ser)
            ser.threadlisten.start()            #start thread
            ser.threadlisten.join(0.01)         #join calling thread
        return COMobjslst
    except:
        TClose(COMobjslst)
        print "Uncaught exception. Threads and serial port(s) stopped."
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
                    s = s+ser.read(1000)            # add string to buffer
                    first, last = s.find('#'), s.rfind('#') # Find start chars
                    s = TStrRepl(s)                 # correct replacement chars
                    if first > -1 and last >= first:# at least 1 packet found
                        s = s[s.find('#',0):]       # omit incomplete sequence
                        len_s = len(s)              # check for complete packet 
                        if len_s>1:                 # 1st byte after # = size
                            ndatabytes = 2*2**(ord(s[1]) >> 5)
                            blocklength = 8+ndatabytes
                            if len_s>=blocklength:  
                                s2parse = s[1:blocklength]  # block to parse
                                if ser.verbosity>2:
                                    print "TListen:", ":".join("{0:x}".format(ord(c)) for c in s2parse)
                                s = s[blocklength:] # remains go to next cycle
                                timeouttimer = 0    # reset timeout timer
                                packet = TSerial_parse(s2parse) #to handler
                                if ser.verbosity>2:
                                    print "TListen:", packet.TimeStampPC, packet.PacketType
                                ser, packet = TPacketInterpreter(ser, packet)
                            else: #incomplete packet -> check timeout timer
                                if timeouttimer-time.time() > 1: 
                                    s="" #clear the buffer
                                    raise TProtocolError("Timeout when parsing serial buffer")
                                else:
                                    if timeouttimer == 0:  #set a new timer
                                        timeouttimer = time.time()
                time.sleep(0.05) # pace this process 
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
            c.threadactive.clear()
            c.threadlive.clear()
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
        prettyhex = ":".join("{0:x}".format(ord(c)) for c in s2parse) #string in pretty hex        
        print "TSerial_parse: Packet: ", prettyhex
        return packet
        pass    
    except Exception: #any uncaught error
        return packet
        raise

def TPacketInterpreter(ser, packet):
    """Interpret Trios data packet according to source instrument communication standards. All information is stored in a dictionary where key, value  = instrument serial number, TChannel"""
    try:
        if packet.ModuleID == 164: #MicroFlu configuration package (address A4)
            packet.PacketType = 'config'
            if ser.verbosity>0:
                print "Interpreter: received MicroFlu configuration on", ser.port
            try:
                TID = hex(packet.id1_id)[2:].zfill(2) + hex(packet.id2)[2:].zfill(2)+"00"
                ser.Tchannels[TID].TMicroFlu.ROMConfig.IntAvg = packet.Databytes[3]
                ser.Tchannels[TID].TMicroFlu.ROMConfig.Auto = (packet.Databytes[4] & 0b00001000)>>3  #1 is Start measuring on startup
                ser.Tchannels[TID].TMicroFlu.ROMConfig.Ampl = packet.Databytes[4]>>4                 #0/1/2 = high/auto/low
                ser.Tchannels[TID].TMicroFlu.ROMConfig.HighA_Offset = np.float(packet.Databytes[5]*256 + packet.Databytes[6])
                ser.Tchannels[TID].TMicroFlu.ROMConfig.LowA_Offset =  np.float(packet.Databytes[7]*256 + packet.Databytes[8])
                ser.Tchannels[TID].TMicroFlu.ROMConfig.HighA_Scale = np.float(packet.Databytes[9]) + np.float(packet.Databytes[10])/256
                ser.Tchannels[TID].TMicroFlu.ROMConfig.LowA_Scale = np.float(packet.Databytes[11]) + np.float(packet.Databytes[12])/256
                return ser, packet
            except:
                print "Interpreter: error interpreting config package"
                pass
        if packet.PacketType is 'query':
            serlow = packet.Databytes[0]        # in serial number ### this is the last 2 hex chars
            serhi = packet.Databytes[1]         # in serial number #### this is the first 2 hex chars
            vals,types = [2,4,8,9,10,12,16,20,24], ['MicroFlu','IOM','COM','IPS','SAMIP','SCM','SAM','DFM','ADM']
            thisTchannel = TChannel()
            tid1 = hex(packet.id1_id)[2:].zfill(2)
            tid2 = hex(packet.id2)[2:].zfill(2)
            tid3 = hex(packet.ModuleID)[2:].zfill(2)
            thisTchannel.TInfo.TID = tid1+tid2+tid3
            thisTchannel.TInfo.serialn = str.upper(hex(serhi)[-2::]+hex(serlow)[-2::]) #serial as quoted on instrument
            thisTchannel.TInfo.ModuleType = types[vals.index(serhi>>3)]                # module type from 5 most sign Bits
            thisTchannel.TInfo.Firmware = packet.Databytes[3]+0.01*packet.Databytes[2]
            thisTchannel.TInfo.ModFreq = [np.nan,2,4,6,8,10,12,20][packet.Databytes[4]]#operating freq. in MHz
            if thisTchannel.TInfo.ModuleType is 'IPS':
                for c in ['02','04','06','08']:
                    TCommandSend(ser,commandset=None,ipschan=c,command='query') #query submodule information
            if thisTchannel.TInfo.ModuleType is 'MicroFlu':
                thisTchannel.TMicroFlu.Settings.Ftype = packet.Databytes[5]                         #1 = chl; 2 = blue, 3 is CDOM
                thisTchannel.TMicroFlu.Settings.SMit = packet.Databytes[6]                          #Internal averaging n samples
                thisTchannel.TMicroFlu.Settings.CtlStart = (packet.Databytes[7] & 0b10000000)>>7    #bit 7 = sampling is active
                thisTchannel.TMicroFlu.Settings.CtlAnalog = (packet.Databytes[7] & 0b01000000)>>6   #bit 6 Analog Power (0=OFF, 1=ON)
                thisTchannel.TMicroFlu.Settings.CtlRange = (packet.Databytes[7] & 0b00100000)>>5    #Bit 5: Range (0= highAmp, 1= lowAmp)
                thisTchannel.TMicroFlu.Settings.CtlAutoR = (packet.Databytes[7] & 0b00010000)>>4    #Bit 4: AutoRange (0= OFF, 1= ON)
                thisTchannel.TMicroFlu.Settings.CtlContn = (packet.Databytes[7] & 0b00001000)>>3    #Bit 3: Datastream (0= OnDemand, 1= Continously)
                #a query command on a MicroFlu can be followed by a ROM Config request for more sensor info
                TCommandSend(ser,commandset='MicroFlu',ipschan=thisTchannel.TInfo.TID[0:2],command='ReadCfg')
                #after config request reset the sensor to previous sampling state
                if thisTchannel.TMicroFlu.Settings.CtlContn == 0:
                    TCommandSend(ser,commandset='MicroFlu',\
                        ipschan=thisTchannel.TInfo.TID[0:2],command='cont_off')
                else:
                    TCommandSend(ser,commandset='MicroFlu',\
                        ipschan=thisTchannel.TInfo.TID[0:2],command='cont_on')
            if thisTchannel.TInfo.ModuleType in['SAM','SAMIP']:
                thisTchannel.TSAM.Settings.SAMConfiguration = packet.Databytes[5]
                thisTchannel.TSAM.Settings.SAMRange = packet.Databytes[6]
                thisTchannel.TSAM.Settings.SAMStatus = packet.Databytes[7]
            ser.Tchannels[thisTchannel.TInfo.TID]=thisTchannel
            if ser.verbosity>1:
                print "Interpreter:", packet.TimeStampPC, "Query result from",\
                    thisTchannel.TInfo.ModuleType, "on", ser.port, hex(packet.id1_id),\
                    hex(packet.id2), hex(packet.ModuleID), thisTchannel.TInfo.serialn,\
                    thisTchannel.TInfo.ModuleType
        if packet.PacketType is 'measurement':
            tid1 = hex(packet.id1_id)[2:].zfill(2)
            tid2 = hex(packet.id2)[2:].zfill(2)
            tid3 = hex(packet.ModuleID)[2:].zfill(2)
            TID = tid1+tid2+tid3
            interpreter = ''
            if int(tid3) == 0:
                if ser.Tchannels[TID].TInfo.ModuleType in['SAM','SAMIP']:
                    interpreter = 'SAM'
                if ser.Tchannels[TID].TInfo.ModuleType is 'MicroFlu':
                    interpreter='MicroFlu'
            if int(tid3) == 20:
                if ser.Tchannels[tid1+tid2+'80'].TInfo.ModuleType in ['COM','SAMIP']:
                    TID = tid1+tid2+'80'
                    interpreter='ADM'
            if int(tid3) == 30:
                if ser.Tchannels[tid1+tid2+'80'].TInfo.ModuleType in ['COM','SAMIP']:
                    TID = tid1+tid2+'80'
                    interpreter='SAM'
            if ser.verbosity>1:
                print "Interpreter:",packet.TimeStampPC, "type: ",interpreter,\
                    "measurement on",ser.port,", Address",TID
            if interpreter is 'ADM':
                if ser.verbosity>1:
                    print "Interpreter: ADM measurement (not implemented),\
                        address", TID, packet.id1_databytes,"bytes, \
                        Instrument:",ser.Tchannels[TID].TInfo.serialn
            if interpreter is 'SAM':
                if ser.verbosity>1:
                    print "Interpreter: SAM frame:", packet.Framebyte, "with",\
                        packet.id1_databytes, " databytes on Module:",\
                        ser.Tchannels[TID].TInfo.serialn
                formatstring = '<'+'H'*int(packet.id1_databytes/2)
                rawdata = ''.join([chr(y) for y in packet.Databytes])
                LEdata = struct.unpack(formatstring,rawdata)
                ser.Tchannels[TID].TSAM.dataframes[packet.Framebyte]=LEdata
                if packet.Framebyte == 0:
                    frames = ser.Tchannels[TID].TSAM.dataframes
                    if sum(y is None for y in frames)==0:
                        ser.Tchannels[TID].TSAM.lastRawSAM = [item for sublist in frames for item in sublist]
                        ser.Tchannels[TID].TSAM.lastRawSAMTime = packet.TimeStampPC
                        if ser.verbosity>1:
                            print "Interpreter: Spectrum received at", ser.port, "address (master)",ser.Tchannels[TID].TInfo.TID, "module",ser.Tchannels[TID].TInfo.serialn
                    else:
                        if ser.verbosity>1:
                            print "Interpreter: Incomplete spectrum received and discarded"
                        raise TProtocolError("Interpreter: Incomplete spectrum received and discarded")
                    ser.Tchannels[TID].TSAM.dataframes=[[None]]*8 #reset to receive the next spectrum
            if interpreter is 'MicroFlu':
                formatstring = '>'+'H'*int(packet.id1_databytes/2) #byteorder is big endian although documentation suggests different
                BEdata = struct.unpack(formatstring,''.join([chr(y) for y in packet.Databytes]))
                gain = BEdata[0] >> 15  #0 means high gain, 1 means low gain
                data = BEdata[0] & 0b111111111111
                ser.Tchannels[TID].TMicroFlu.lastFluRaw = [gain,data]
                ser.Tchannels[TID].TMicroFlu.lastFluTime = packet.TimeStampPC
                if gain == 1:
                    ser.Tchannels[TID].TMicroFlu.lastFluCal= 100*data/np.float(2048)
                if gain == 0:
                    ser.Tchannels[TID].TMicroFlu.lastFluCal= 10*data/np.float(2048)
                if ser.verbosity>1:
                    gains,ftypes = ['H','L'], [None,'Chl','Blue','CDOM']
                    print "Interpreter: Microflu-",ftypes[ser.Tchannels[TID].TMicroFlu.Settings.Ftype],\
                    " data from", ser.port, "Gain:",gain,"("+gains[gain]+")",\
                    "Raw Value:",data, "Cal. value:",ser.Tchannels[TID].TMicroFlu.lastFluCal
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

def TCommandSend(ser,commandset,command='query', ipschan='00', par1='00'):
    """send a command from a module specific command set to a TriOS device.\n
    Device reconfiguration is not supported.\n

    Command sets implemented:
        QUERY, not instrument specific: TCommandSend(ser,None,'query')
        *MicroFlu*  e.g. TCommandSend(ser,'MicroFlu',command='cont_off')
        *SAM*       e.g. TCommandSend(ser,'SAM',command='startIntAuto')

        The reboot command has been disabled for now, until it is better understood:\n
        SAM: 'reboot'      : bytearray.fromhex("23 "+str(ipschan)+" 00 80 00 00 00 01")\n
        Micrflu: 'reboot'     : bytearray.fromhex("23 "+str(ipschan)+" 00 00 00 00 00 01")\n
        
    For sensors on an IPS4 box, specify the channel as *ipschan* = '02','04','06','08' for channels 1-4 respectively.\n\n
    *par1* is the first user-configurable parameter mentioned in the documentation, even when listed as parameter2 in the docs. Most commands require only one argument.\n\n
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