
from ModbusTCPClient import ModbusClient

# Atrea:
client = ModbusClient(host="10.10.12.210", port=int(502), auto_open=True, auto_close=True, timeout=10, debug=1)
#data = client.read_holding_registers(514, 1)
data = client.read_input_registers(210, 5)
print("MODBUS data = " + str(data))
