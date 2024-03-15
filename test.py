from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from bleak import BleakClient
import array
import base64
from typing import Optional
from govee_utils import prepareMultiplePacketsData  # Ensure this is accessible

app = FastAPI()
logging.basicConfig(level=logging.INFO)

UUID_CONTROL_CHARACTERISTIC = '00010203-0405-0607-0809-0a0b0c0d2b11'

class LightCommand(BaseModel):
    address: str
    brightness: Optional[int] = None
    rgb_color: Optional[list[int]] = None
    effect: Optional[str] = None

async def send_command(address: str, command: bytes):
    async with BleakClient(address) as client:
        await client.connect()
        if client.is_connected:
            await client.write_gatt_char(UUID_CONTROL_CHARACTERISTIC, command, False)
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to device")

def prepare_single_packet_data(cmd, payload):
    if not isinstance(cmd, int):
        raise ValueError('Invalid command')
    if not isinstance(payload, bytes) and not (
            isinstance(payload, list) and all(isinstance(x, int) for x in payload)):
        raise ValueError('Invalid payload')
    if len(payload) > 17:
        raise ValueError('Payload too long')

    cmd = cmd & 0xFF
    payload = bytes(payload)

    frame = bytes([0x33, cmd]) + bytes(payload)
    frame += bytes([0] * (19 - len(frame)))

    checksum = 0
    for b in frame:
        checksum ^= b

    frame += bytes([checksum & 0xFF])
    return frame

@app.post("/turn_on/")
async def turn_on(command: LightCommand):
    commands = []
    commands.append(prepare_single_packet_data(0x01, [0x1]))  # Power on

    if command.brightness is not None:
        commands.append(prepare_single_packet_data(0x04, [command.brightness]))

    if command.rgb_color:
        commands.append(prepare_single_packet_data(0x05, [0x02] + command.rgb_color))  # Manual mode + RGB

    if command.effect:
        # Simplified effect handling; you'll need to adapt this based on your actual effect data
        effect_data = base64.b64decode(command.effect)  # Assuming effect is base64-encoded
        for cmd in prepareMultiplePacketsData(0xa3, array.array('B', [0x02]), array.array('B', effect_data)):
            commands.append(cmd)

    for cmd in commands:
        await send_command(command.address, cmd)

    return {"message": "Command sent successfully."}

@app.post("/turn_off/")
async def turn_off(command: LightCommand):
    await send_command(command.address, prepare_single_packet_data(0x01, [0x0]))  # Power off
    return {"message": "Command sent successfully."}