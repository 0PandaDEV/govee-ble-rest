from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from typing import Optional
import logging
from bleak import BleakClient

app = FastAPI()

UUID_CONTROL_CHARACTERISTIC = '000102030405060708090a0b0c0d2b11'

_LOGGER = logging.getLogger(__name__)

class LightCommand(BaseModel):
    address: str
    state: Optional[bool] = None

async def _connectBluetooth(address) -> BleakClient:
    client = BleakClient(address)
    await client.connect()
    return client

@app.post("/control-light/")
async def control_light(command: LightCommand):
    if command.state is None:
        return {"error": "State must be provided"}

    client = await _connectBluetooth(command.address)
    if client.is_connected:
        await client.write_gatt_char(UUID_CONTROL_CHARACTERISTIC, bytearray([0x01 if command.state else 0x00]), False)
        await client.disconnect()
        return {"success": True}
    else:
        return {"error": "Failed to connect to the device"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
