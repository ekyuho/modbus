#!/usr/bin/env python3
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer
from pymodbus.server.sync import StartSerialServer

from _thread import start_new_thread
import time
import requests

import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

sensors = {}
index = {'NO':0,'T0':1,'H0':2,'D0':3,'D1':4,'C0':5,'M0':6,'Q0':7}
refresh = True

with open("mcu3k.conf") as f:
    lines = f.readlines()
    for k in lines:
        if k[0] == '#': continue
        s = k.replace('\n','').split(',')
        if len(s) == 2:
            sensors[s[0]] = int(s[1])
        else:
            print("wrong sensor.txt: %s"%(s))
print("Number of sensors for tracking = %d"%(len(sensors)))


def updating_writer(a):
    global refresh, sensors, index
    while True:
        log.debug("\nupdating the context")
        if refresh:
            try:
                r = requests.get('http://t.damoa.io:9500/latest')
            except Exception as e:
                print("error in request", e)
            try:
                latest = r.json()
            except Exception as e:
                print("error in request", e)
            refresh = False
        context = a[0]
        register = 3
        address = 0x00
        values = context.getValues(register, address, count=10*len(sensors))
        print("old values=", values)
        for sens in sensors:
            if sens in latest:
                try:
                    values[sensors[sens]+index['NO']-1] = int(sens[2:])
                    values[sensors[sens]+index['T0']-1] = int(float(latest[sens].get('T0',0)) * 10)
                    values[sensors[sens]+index['H0']-1] = int(float(latest[sens].get('H0',0)) * 10)
                    values[sensors[sens]+index['D0']-1] = int(latest[sens].get('D0',0)) * 10
                    values[sensors[sens]+index['D1']-1] = int(latest[sens].get('D1',0)) * 10
                    values[sensors[sens]+index['C0']-1] = int(latest[sens].get('C0',0)) * 10
                    values[sensors[sens]+index['M0']-1] = int(latest[sens].get('M0',0)) * 10
                    values[sensors[sens]+index['Q0']-1] = int(latest[sens].get('Q0',0)) * 10
                except Exception as e:
                    print("error in conversion", e)
                log.debug("got new values: " + str(values[sensors[sens]+index['NO']-1:sensors[sens]+index['Q0']]))
        print("new values=", values)
        context.setValues(register, address, values)
        time.sleep(60)
        refresh = True


def run_updating_server():
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [17]*100),
        co=ModbusSequentialDataBlock(0, [17]*100),
        hr=ModbusSequentialDataBlock(0, [0, 250,650,66,99,4210,76,0,0,0]*10),
        ir=ModbusSequentialDataBlock(0, [17]*100))
    context = ModbusServerContext(slaves=store, single=True)
    
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl = 'http://github.com/bashwork/pymodbus/'
    identity.ProductName = 'pymodbus Server'
    identity.ModelName = 'pymodbus Server'
    identity.MajorMinorRevision = '1.0'
    
    start_new_thread(updating_writer, (context,))
    StartSerialServer(context, framer=ModbusRtuFramer, identity=identity, port='/dev/ttyUSB0', timeout=.005, baudrate=9600)


if __name__ == "__main__":
    run_updating_server()
