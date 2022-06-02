
from ModbusTCPClient import ModbusClient

# Atrea:
client = ModbusClient(host="10.10.12.210", port=int(502), auto_open=True, auto_close=True, timeout=10, debug=1)
data = client.read_holding_registers(0, 100)
#data = client.read_input_registers(10, 10)
#data = client.read_coils(4, 6)
print("MODBUS data = " + str(data))



exit(0)



print("~~~~~~~~~~~")

client.write_single_register(8, 18)

print("~~~~~~~~~~~")



client = ModbusClient(host="10.10.12.210", port=int(502), auto_open=True, auto_close=True, timeout=10, debug=1)
data = client.read_input_registers(4, 6)
print("MODBUS data = " + str(data))
