
"""
<plugin key="Atrea" name="Atrea - Modbus TCP/IP" author="Maxim" version="2021.02.06">
    <params>
        <param field="Address" label="TCP: IPv4" width="140px" required="true" default="0.0.0.0"/>
        <param field="SerialPort" label="Debug mode" width="140px" required="true">
            <options>
                <option label="NO" value="0"/>
                <option label="YES" value="1"/>
            </options>
        </param>
        <param field="Mode1" label="IN1 label" width="140px" required="true" default="IN1"/>
        <param field="Mode2" label="IN2 label" width="140px" required="true" default="IN2"/>
        <param field="Mode3" label="D1 label" width="140px" required="true" default="D1"/>
        <param field="Mode4" label="D2 label" width="140px" required="true" default="D2"/>
        <param field="Mode5" label="D3 label" width="140px" required="true" default="D3"/>
        <param field="Mode6" label="D4 label" width="140px" required="true" default="D4"/>
    </params>
</plugin>
"""

import Domoticz
from datetime import datetime
import gettext
from pyModbusTCP.client import ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
import re
import requests
import xmltodict

class Atrea:

    def onStart(self):

        self.uTEa = 1
        self.uTEb = 6
        self.uTU1 = 3
        self.uTU2 = 4
        self.uPowerCur = 8
        self.uControlMode = 9
        #self.uPowerReq = 10
        self.uModeCur = 7
        #self.uModeReq = 11
        self.uIN1 = 12
        self.uIN2 = 13
        self.uD1 = 14
        self.uD2 = 15
        self.uD3 = 16
        self.uD4 = 17
        self.uZVT = 18
        self.uBypass = 19
        self.uAlarmFilter = 20
        self.uHeatingSeason = 21
        self.uNightlyCooling = 22


        # CMDs:
        #  init: pygettext3.8 -d base -o locales/base.pot plugin.py
        #  init: locales/cs/LC_MESSAGES# msgfmt -o base.mo base
        #  update: xgettext -d base --from-code utf-8 -s -j -o locales/base.pot plugin.py
        #  update: msgmerge --update locales/cs/LC_MESSAGES/base.po locales/base.pot
        #  update: locales/cs/LC_MESSAGES# msgfmt -o base.mo base
        translate = gettext.translation('base', localedir='plugins/atrea/locales', fallback=True, languages=['cs'])
        translate.install()
        self._ = translate.gettext
       

        if (Parameters["SerialPort"] == "1"):
            Domoticz.Debugging(1)
            DumpConfigToLog()
            Domoticz.Debug("Domoticz language: " + Settings["Language"]) # Domoticz language: cs
            Domoticz.Debug("***** NOTIFICATION: Debug is enabled!")
        else:
            Domoticz.Debugging(0)
        Domoticz.Debug("onStart called")
        
        Domoticz.Heartbeat(int(10)) # Device pollrate (heartbeat) : 10s

        self.TCP_IP = Parameters["Address"]
        self.TCP_PORT = 502

        self.labelIN1 = str(Parameters["Mode1"])
        self.labelIN2 = str(Parameters["Mode2"])
        self.labelD1 = str(Parameters["Mode3"])
        self.labelD2 = str(Parameters["Mode4"])
        self.labelD3 = str(Parameters["Mode5"])
        self.labelD4 = str(Parameters["Mode6"])
        
        self.atreaMinPower = 60
                
        # Get Atrea unit info from Modbus..
        try: client = ModbusClient(host=self.TCP_IP, port=int(self.TCP_PORT), unit_id=int(1), auto_open=True, auto_close=True, timeout=2)
        except: Domoticz.Error("Can not connect to Modbus TCP/IP: " + self.TCP_IP + ":" + self.TCP_PORT)
        try:
            # 1 = 180 EC, 2 = 190 ECV, 3 = 370 EC, 4 = 390ECV, 5 = 510 EC, 6 = 520 ECV
            self.atreaType = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(509, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            if (self.atreaType == 1):
                self.atreaTypeStr = "180 EC"
                self.atreaNominalPower = 180
            elif (self.atreaType == 2):
                self.atreaTypeStr = "190 ECV"
                self.atreaNominalPower = 180
            elif (self.atreaType == 3):
                self.atreaTypeStr = "370 EC"
                self.atreaNominalPower = 370
            elif (self.atreaType == 4):
                self.atreaTypeStr = "390 ECV"
                self.atreaNominalPower = 370
            elif (self.atreaType == 5):
                self.atreaTypeStr = "510 EC"
                self.atreaNominalPower = 510
            elif (self.atreaType == 6):
                self.atreaTypeStr = "520 ECV"
                self.atreaNominalPower = 510
            Domoticz.Debug("Atrea type: " + self.atreaTypeStr)

            self.atreaLimitedPower = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(516, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            self.atreaMaxPower = self.atreaLimitedPower / 100 * self.atreaNominalPower 
            Domoticz.Debug("Atrea limited power at: " + str(self.atreaLimitedPower) + "% = " + str(self.atreaMaxPower) + "m3") 
            
            self.atreaIN1type = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(705, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            self.atreaIN2type = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(704, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            self.atreaZVT = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(514, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            
        except: Domoticz.Error("Modbus TCP/IP communication error. Check it out!")
                
        if self.uTEa not in Devices: Domoticz.Device(Unit=self.uTEa, DeviceID="TEa", Name=self._("Outside temperature"), TypeName="Temperature", Used=1).Create()
        if self.uTEb not in Devices: Domoticz.Device(Unit=self.uTEb, DeviceID="TEb", Name=self._("Exhaust air before recuperation"), TypeName="Temperature", Used=1).Create()
        if self.uTU1 not in Devices: Domoticz.Device(Unit=self.uTU1, DeviceID="TU1", Name=self._("Fresh air after recuperation"), TypeName="Temperature", Used=1).Create()
        if self.uTU2 not in Devices: Domoticz.Device(Unit=self.uTU2, DeviceID="TU2", Name=self._("Exhaust air after recuperation"), TypeName="Temperature", Used=1).Create()
        if self.labelD1 != "" and self.labelD1 != "D1" and self.uD1 not in Devices: Domoticz.Device(Unit=self.uD1, DeviceID="D1", Name=self.labelD1, TypeName="Contact", Used=1).Create()
        if self.labelD2 != "" and self.labelD2 != "D2" and self.uD2 not in Devices: Domoticz.Device(Unit=self.uD2, DeviceID="D2", Name=self.labelD2, TypeName="Contact", Used=1).Create()
        if self.labelD3 != "" and self.labelD3 != "D3" and self.uD3 not in Devices: Domoticz.Device(Unit=self.uD3, DeviceID="D3", Name=self.labelD3, TypeName="Contact", Used=1).Create()
        if self.labelD4 != "" and self.labelD4 != "D4" and self.uD4 not in Devices: Domoticz.Device(Unit=self.uD4, DeviceID="D4", Name=self.labelD4, TypeName="Contact", Used=1).Create()
        if self.atreaZVT > 0 and self.uZVT not in Devices: Domoticz.Device(Unit=self.uZVT, DeviceID="ZVT", Name=self._("Ground heat exchanger"), TypeName="Contact", Used=1).Create()
        if self.uBypass not in Devices: Domoticz.Device(Unit=self.uBypass, DeviceID="BYPASS", Name=self._("Bypass flap"), TypeName="Contact", Used=1).Create()
        if self.uAlarmFilter not in Devices: Domoticz.Device(Unit=self.uAlarmFilter, DeviceID="AlarmFilter", Name=self._("Filter change"), Type=243, Subtype=22, Used=1).Create()
        if self.uHeatingSeason not in Devices: Domoticz.Device(Unit=self.uHeatingSeason, DeviceID="HeatingSeason", Name=self._("Heating season"), Type=244, Subtype=73, Switchtype=0, Image=10, Used=1).Create()
        if self.uNightlyCooling not in Devices: Domoticz.Device(Unit=self.uNightlyCooling, DeviceID="NightlyCooling", Name=self._("Nightly cooling"), Type=244, Subtype=73, Switchtype=0, Image=16, Used=1).Create()

        
        if self.labelIN1 != "" and self.labelIN1 != "IN1" and self.uIN1 not in Devices:
            # H00705 Režim vstupu IN1: 0 = Kontakt, 1 = Analog (0-10V)
            if self.atreaIN1type == 0: TypeName = "Contact"
            elif self.atreaIN1type == 1: # analog
                if re.search('vlhko', self.labelIN1, re.IGNORECASE) or re.search('humid', self.labelIN1, re.IGNORECASE): TypeName = "Humidity"
                elif re.search('teplot', self.labelIN1, re.IGNORECASE) or re.search('temp', self.labelIN1, re.IGNORECASE): TypeName = "Temperature"
                else: TypeName = "Percentage"
            Domoticz.Device(Unit=self.uIN1, DeviceID="IN1", Name=self.labelIN1, TypeName=TypeName, Used=1).Create()

        if self.labelIN2 != "" and self.labelIN2 != "IN2" and self.uIN2 not in Devices:
            # H00704 Režim vstupu IN2: 0 = Kontakt, 1 = Analog (0-10V), 2 = Teplota
            if self.atreaIN2type == 0: TypeName = "Contact"
            elif self.atreaIN2type == 2: TypeName = "Temperature"
            elif self.atreaIN2type == 1: # analog
                if re.search('vlhko', self.labelIN2, re.IGNORECASE) or re.search('humid', self.labelIN2, re.IGNORECASE): TypeName = "Humidity"
                elif re.search('teplot', self.labelIN2, re.IGNORECASE) or re.search('temp', self.labelIN2, re.IGNORECASE): TypeName = "Temperature"
                else: TypeName = "Percentage"
            Domoticz.Device(Unit=self.uIN2, DeviceID="IN2", Name=self.labelIN2, TypeName=TypeName, Used=1).Create()
        
        o1 = 60 + (self.atreaMaxPower-60) / 8
        o2 = o1 + (self.atreaMaxPower-60) / 8
        o3 = o2 + (self.atreaMaxPower-60) / 8
        o4 = o3 + (self.atreaMaxPower-60) / 8
        o5 = o4 + (self.atreaMaxPower-60) / 4
        self.oPower = {"LevelNames": "0|60|" + str(int(o1)) + "|" + str(int(o2)) + "|" + str(int(o3)) + "|" + str(int(o4)) + "|" + str(int(o5)) + "|" + str(int(self.atreaMaxPower))}
        self.oControlMode = {"LevelNames": "|" + self._("Manual") + "|" + self._("Automatic") + "|" + self._("Temporary"), "LevelOffHidden": "true", "SelectorStyle": "1"}
        self.oModeReq = {"LevelNames":  self._("Off") + "|" + self._("Periodic ventilation") + "|" + self._("Ventilation"), "SelectorStyle": "1"}
        self.oModeCur = {"LevelNames":  self._("Off") + "|" + self._("Periodic ventilation") + "|" + self._("Ventilation") + "|" + self.labelIN1 + "|" + self.labelIN2 + "|" + self.labelD1 + "|" + self.labelD2 + "|" + self.labelD3 + "|" + self.labelD4 + "|" + self._("Rise") + "|" + self._("Rundown") + "|" + self._("Defrosting the recuperator"), "SelectorStyle": "1"}

        if self.uControlMode not in Devices: Domoticz.Device(Unit=self.uControlMode, DeviceID="ControlMode", Name=self._("Ventilation control mode"), Options=self.oControlMode, Type=244, Subtype=62, Switchtype=18, Image=9, Used=1).Create()
        if self.uPowerCur not in Devices: Domoticz.Device(Unit=self.uPowerCur, DeviceID="PowerCur", Name=self._("Current ventilation power"), Options=self.oPower, Type=244, Subtype=62, Switchtype=18, Image=7, Used=1).Create()
        #if self.uPowerReq not in Devices: Domoticz.Device(Unit=self.uPowerReq, DeviceID="PowerReq", Name=self._("Requested ventilation power"), Options=self.oPower, Type=244, Subtype=62, Switchtype=18, Image=7, Used=1).Create()
        if self.uModeCur not in Devices: Domoticz.Device(Unit=self.uModeCur, DeviceID="ModeCur", Name=self._("Current ventilation mode"), Options=self.oModeCur, Image=7, Type=244, Subtype=62, Switchtype=18, Used=1).Create()
        #if self.uModeReq not in Devices: Domoticz.Device(Unit=self.uModeReq, DeviceID="ModeReq", Name=self._("Requested ventilation mode"), Options=self.oModeReq, Image=7, Type=244, Subtype=62, Switchtype=18, Used=1).Create()
        
        return

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")

        try: client = ModbusClient(host=self.TCP_IP, port=int(self.TCP_PORT), unit_id=int(1), auto_open=True, auto_close=True, timeout=2)
        except: Domoticz.Error("Can not connect to Modbus TCP/IP: " + self.TCP_IP + ":" + self.TCP_PORT)

        try:
            c207 = BinaryPayloadDecoder.fromRegisters(client.read_coils(207, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            c211 = BinaryPayloadDecoder.fromRegisters(client.read_coils(211, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            c902 = BinaryPayloadDecoder.fromRegisters(client.read_coils(902, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            c1200 = BinaryPayloadDecoder.fromRegisters(client.read_coils(1200, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            #Domoticz.Debug("Modbus response: v='" + str(i201) + "'")
        except: Domoticz.Error("Modbus TCP/IP communication error (input registers). Check it out!")

        try:
            i200 = BinaryPayloadDecoder.fromRegisters(client.read_input_registers(200, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            i201 = BinaryPayloadDecoder.fromRegisters(client.read_input_registers(201, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            i203 = BinaryPayloadDecoder.fromRegisters(client.read_input_registers(203, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            i204 = BinaryPayloadDecoder.fromRegisters(client.read_input_registers(204, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            i205 = BinaryPayloadDecoder.fromRegisters(client.read_input_registers(205, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            i206 = BinaryPayloadDecoder.fromRegisters(client.read_input_registers(206, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            #Domoticz.Debug("Modbus response: v='" + str(i201) + "'")
        except: Domoticz.Error("Modbus TCP/IP communication error (input registers). Check it out!")

        try:
            d200 = BinaryPayloadDecoder.fromRegisters(client.read_discrete_inputs(200, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            d201 = BinaryPayloadDecoder.fromRegisters(client.read_discrete_inputs(201, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            d202 = BinaryPayloadDecoder.fromRegisters(client.read_discrete_inputs(202, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            d203 = BinaryPayloadDecoder.fromRegisters(client.read_discrete_inputs(203, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            #Domoticz.Debug("Modbus response: v='" + str(i201) + "'")
        except: Domoticz.Error("Modbus TCP/IP communication error (discrete inputs). Check it out!")

        try:
            v1000 = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(1000, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            v1001 = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(1001, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            #v1008 = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(1008, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            #v1009 = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(1009, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            #v1012 = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(1012, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            #v1013 = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(1013, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            v1015 = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(1015, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            v1016 = BinaryPayloadDecoder.fromRegisters(client.read_holding_registers(1016, 1), byteorder=Endian.Big, wordorder=Endian.Big).decode_16bit_int()
            #Domoticz.Debug("Modbus response: v='" + str(v1015) + "'")
        except: Domoticz.Error("Modbus TCP/IP communication error (holding registers). Check it out!")


        # == Temperatures
        Devices[self.uTU1].Update(0, str(i200 / 10))
        Devices[self.uTU2].Update(0, str(i201 / 10))
        Devices[self.uTEa].Update(0, str(i203 / 10))
        Devices[self.uTEb].Update(0, str(i204 / 10))

        # == IN1 & IN2
        # I00205 Stav vstupu IN1 (0-10V): Analogový vstup: U= DATA/1000, Kontaktní vstup: rozepnuto ~ 3350 až 3450, sepnuto ~ do 20
        # I00206 Stav vstupu IN2 (0-10V): Analogový vstup: U= DATA/1000, Kontaktní vstup: rozepnuto ~ 3350 až 3450, sepnuto ~ do 20
        # kontakt: Statuses: Open: nValue = 1, Closed: nValue = 0 
        if self.uIN1 in Devices:
            if self.atreaIN1type == "Contact": Devices[self.uIN1].Update(int(not(i205 <= 50)), "")
            elif Devices[self.uIN1].Type == 81:
                # Humidity_status can be one of:
                # 0=Normal      45~50, 55~60
                # 1=Comfortable 50~55
                # 2=Dry         <45
                # 3=Wet         >60
                if i205 < 4500: humstat = 2
                elif i205 > 6000: humstat = 3
                elif i205 >= 5000 and i205 <= 5500: humstat = 1
                else: humstat = 0
                Devices[self.uIN1].Update(int(i205 / 100), str(humstat))
            else: Devices[self.uIN1].Update(int(i205 / 100), str(i205 / 100))
        if self.uIN2 in Devices:
            if self.atreaIN2type == "Contact": Devices[self.uIN2].Update(int(not(i206 <= 50)), "")
            elif Devices[self.uIN2].Type == 81:
                if i206 < 4500: humstat = 2
                elif i206 > 6000: humstat = 3
                elif i206 >= 5000 and i206 <= 5500: humstat = 1
                else: humstat = 0
                Devices[self.uIN2].Update(int(i206 / 100), str(humstat))
            else: Devices[self.uIN2].Update(int(i206 / 100), str(i206 / 100))
        
        # == D1 & D2 & D3 & D4
        # D00200 Stav vstupu D1 : 0/1 : Vypnuto/Zapnuto
        # D00201 Stav vstupu D2 : 0/1 : Vypnuto/Zapnuto
        # D00202 Stav vstupu D3 : 0/1 : Vypnuto/Zapnuto
        # D00203 Stav vstupu D4 : 0/1 : Vypnuto/Zapnuto
        if self.uD1 in Devices: Devices[self.uD1].Update(int(d200 == 1), "")
        if self.uD2 in Devices: Devices[self.uD2].Update(int(d201 == 1), "")
        if self.uD3 in Devices: Devices[self.uD3].Update(int(d202 == 1), "")
        if self.uD4 in Devices: Devices[self.uD4].Update(int(d203 == 1), "")
        
        # == ZVT
        # C00207 0 = ZVT
        if self.uZVT in Devices: Devices[self.uZVT].Update(int(c207 == 0), "")
        
        # == Bypass
        # C00211 1 = Bypass flap
        if self.uBypass in Devices: Devices[self.uBypass].Update(int(c211 == 1), "")
        
        # == Heating season
        # C01200 1 = heating, 0 = non-heating
        if self.uHeatingSeason in Devices: Devices[self.uHeatingSeason].Update(int(c1200 == 1), "")
        
        # == Nightly Cooling
        # C00902 0 = recuperation, 1 = cooling
        if self.uNightlyCooling in Devices: Devices[self.uNightlyCooling].Update(int(c902 == 1), "")
        
        
        # == ControlMode
        if v1015 == 2 or v1016 == 2: Devices[self.uControlMode].Update(1, str(30))
        elif v1015 == 1 or v1016 == 1: Devices[self.uControlMode].Update(0, str(10))
        else: Devices[self.uControlMode].Update(0, str(20))
        
        # == PowerReq
        # H01009 Nastavení požadovaného výkonu, pokud H01016=1,   0 = Vyp, 12=12%,..., 100 = 100%
        # H01013 Nastavení požadovaného výkonu, pokud H01016=0/2, 0 = Vyp, 12=12%,..., 100 = 100%
        #if (v1016 == 1):   Devices[self.uPowerReq].Update(int(int(v1009) >= 10), str(self._powerPercentToDomoticzValue(v1009)))
        #elif (v1016 == 2): Devices[self.uPowerReq].Update(int(int(v1013) >= 10), str(self._powerPercentToDomoticzValue(v1013)))
        #elif (v1016 == 0): Devices[self.uPowerReq].Update(int(int(v1001) >= 10), str(self._powerPercentToDomoticzValue(v1001)))

        # == PowerCur
        # "0|60|90|120|150|180|240|300"
        Devices[self.uPowerCur].Update(int(int(v1001) >= 10), str(self._powerPercentToDomoticzValue(v1001)))

        # == ModeReq                                                  "Vypnuto |    Periodické větrání |    Větrání"
        # H01008 Nastavení požadovaného režimu, pokud H01015=1,                 0 = Periodické větrání, 1 = Větrání
        # H01012 Nastavení požadovaného režimu, pokud H01015= 0/2, 0 = Vypnuto, 1 = Periodické větrání, 2 = Větrání
        #if (v1015 == 1): 
        #    if v1008 == 0:   Devices[self.uModeReq].Update(1, str(10))
        #    elif v1008 == 1: Devices[self.uModeReq].Update(1, str(20))
        #elif (v1015 == 2): 
        #    if v1012 == 0:   Devices[self.uModeReq].Update(1, str(10))
        #    elif v1012 == 1: Devices[self.uModeReq].Update(1, str(20))
        #elif (v1015 == 0): 
        #    if v1000 == 0:   Devices[self.uModeReq].Update(1, str(10))
        #    elif v1000 == 1: Devices[self.uModeReq].Update(1, str(20))
            
        # == ModeCur
        # "|Periodické větrání|Větrání|Čidlo vlhkosti|IN2|D1|D2|Koupelny+WC|Odsavač kuchyň|Náběh|Doběh|Odmrazování rekuperátoru"
        if (v1000 == 0):    Devices[self.uModeCur].Update(int(int(v1001) >= 10), str(10))
        elif (v1000 == 1):  Devices[self.uModeCur].Update(int(int(v1001) >= 10), str(20))
        elif (v1000 == 10): Devices[self.uModeCur].Update(1, str(30))
        elif (v1000 == 11): Devices[self.uModeCur].Update(1, str(40))
        elif (v1000 == 12): Devices[self.uModeCur].Update(1, str(50))
        elif (v1000 == 13): Devices[self.uModeCur].Update(1, str(60))
        elif (v1000 == 14): Devices[self.uModeCur].Update(1, str(70))
        elif (v1000 == 15): Devices[self.uModeCur].Update(1, str(80))
        elif (v1000 == 20): Devices[self.uModeCur].Update(1, str(90))
        elif (v1000 == 21): Devices[self.uModeCur].Update(1, str(100))
        elif (v1000 == 22): Devices[self.uModeCur].Update(1, str(110))
        
        # == Filter alarm from XML via HTTP
        try:
            xml = xmltodict.parse(requests.get("http://" + str(self.TCP_IP) + "/config/alarms.xml").content)

            lastErrTime = 0 # p == 0
            lastOkTime = 0  # p == 1
            for i in xml['root']['errors']['i']:
                if int(i['@i']) == 100:
                    if int(i['@p']) == 0 and int(i['@t']) > lastErrTime: lastErrTime = int(i['@t'])
                    elif int(i['@p']) == 1 and int(i['@t']) > lastOkTime: lastOkTime = int(i['@t'])

            if lastOkTime > lastErrTime: Devices[self.uAlarmFilter].Update(1, self._("Filter last changed") + ": " + str(datetime.fromtimestamp(lastOkTime)))
            else: Devices[self.uAlarmFilter].Update(4, self._("Filter to change since") + ": " + str(datetime.fromtimestamp(lastErrTime)))

        except:
            Domoticz.Error("Failed to get or process XML via HTML to get state of filter alarm.")

        return
        
    def onCommand(self, u, Command, Level, Hue):
        Domoticz.Debug(str(Devices[u].DeviceID) + ": onCommand called: Parameter '" + str(Command) + "', Level: " + str(Level))
        
        try: client = ModbusClient(host=self.TCP_IP, port=int(self.TCP_PORT), unit_id=int(1), auto_open=True, auto_close=True, timeout=2)
        except: Domoticz.Error("Can not connect to Modbus TCP/IP: " + self.TCP_IP + ":" + self.TCP_PORT)

        try:
            # == ControlMode  : man = 1, auto = 0, docasny = 2 |  "|Manuál|Automat|Dočasný"
            if (u == self.uControlMode): 
                #if Level == 10: atreaControlMode = 1
                if Level == 20:   atreaControlMode = 0
                elif Level == 30: atreaControlMode = 2
                client.write_single_register(1015, atreaControlMode)
                client.write_single_register(1016, atreaControlMode)
            
            # == HeatingSeason  : 0 = non-heating, 1 = heating
            elif (u == self.uHeatingSeason): 
                client.write_single_coil(1200, int(Command == "On"))
            
            # == NightlyCooling  : 0 = recuperation, 1 = cooling
            elif (u == self.uNightlyCooling): 
                client.write_single_coil(902, int(Command == "On"))
            
            # == uPowerCur
            # == uPowerReq
            elif (u == self.uPowerCur): 
                atreaPower = int(self._powerDomoticzValueToPercent(Level))
                Domoticz.Debug(str(Devices[u].DeviceID) + ": COMMAND: Level=" + str(Level) + ", atreaPower='" + str(atreaPower) + "'")
                client.write_single_register(1009, atreaPower)
                client.write_single_register(1013, atreaPower)
                client.write_single_register(1015, 2)
                client.write_single_register(1016, 2)
                
            # == ModeCur                                                        "Vypnuto |    Periodické větrání |    Větrání |Čidlo vlhkosti|IN2|D1|D2|Koupelny+WC|Odsavač kuchyň|Náběh|Doběh|Odmrazování rekuperátoru"
            # == ModeReq                                                        "Vypnuto |    Periodické větrání |    Větrání"
            #       H01008 Nastavení požadovaného režimu, pokud H01015=1,                 0 = Periodické větrání, 1 = Větrání
            #       H01012 Nastavení požadovaného režimu, pokud H01015= 0/2, 0 = Vypnuto, 1 = Periodické větrání, 2 = Větrání
            elif (u == self.uModeCur): 
                if Level == 0:
                    atreaMode = 1
                    self.onCommand(self.uPowerCur, Command, 0, Hue)
                elif Level == 10: atreaMode = 0
                elif Level == 20: atreaMode = 1
                Domoticz.Debug(str(Devices[u].DeviceID) + ": COMMAND: Level=" + str(Level) + ", atreaMode='" + str(atreaMode) + "'")
                client.write_single_register(1008, atreaMode)
                client.write_single_register(1012, atreaMode)
                client.write_single_register(1015, 2)
                client.write_single_register(1016, 2)
        
        except: Domoticz.Error(str(Devices[u].DeviceID) + ": Modbus update error. Check it out!")
        
        # Update values now!
        self.onHeartbeat() 
        return
        

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)


    def _powerPercentToDomoticzValue(self, percentValue):
        
        valueM3 = None
        valueDomoticz = None
        valueDomoticzM3 = None

        if percentValue < 10:                          # vypnuto nebo méně jak 10%
            valueDomoticz = 0 
            valueDomoticzM3 = 0
        elif percentValue == 10:                       # 10% => 60m3
            valueDomoticz = 10 
            valueDomoticzM3 = self.atreaMinPower
        elif percentValue > self.atreaLimitedPower:    # horní mez
            valueDomoticz = (len(powerLevels) - 1) * 10
            valueDomoticzM3 = self.atreaMaxPower
        else:                                          # 11~80
            valueM3 = ((percentValue - 10) * (self.atreaNominalPower - self.atreaMinPower) / 90) + self.atreaMinPower
            powerLevels = self.oPower.get("LevelNames").split("|")
            for p in range(len(powerLevels)):
                if (p != len(powerLevels) - 1): avgVal = (int(powerLevels[p]) + int(powerLevels[p + 1])) / 2
                else: avgVal = int(powerLevels[p])
                if (valueM3 <= avgVal):
                    valueDomoticz = p * 10
                    valueDomoticzM3 = powerLevels[p]
                    break
                    
        return valueDomoticz
    
    def _powerDomoticzValueToPercent(self, valueDomoticz):
        
        value = 0
        if valueDomoticz == 0:
            valueM3 = 0
            value = 0
        else:
            powerLevels = self.oPower.get("LevelNames").split("|")
            for p in range(len(powerLevels)):
                if (p * 10 == valueDomoticz): 
                    valueM3 = int(powerLevels[p])
                    value = (((valueM3 - self.atreaMinPower) * 90) / (self.atreaNominalPower - self.atreaMinPower)) + 10
                    break

        return value


global _plugin
_plugin = Atrea()

def onStart():
    global _plugin
    _plugin.onStart()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device ID='" + str(Devices[x].ID) + "', DeviceID='" + str(Devices[x].DeviceID) + "', Name='" + Devices[x].Name 
                       + "', nValue='" + str(Devices[x].nValue) + "', sValue='" + Devices[x].sValue + "', LastLevel='" + str(Devices[x].LastLevel) 
                       + "', Type='" + str(Devices[x].Type) + "', SubType='" + str(Devices[x].SubType) + "', SwitchType='" + str(Devices[x].SwitchType) + "'")
        
    return
