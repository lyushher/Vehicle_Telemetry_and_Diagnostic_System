from telemetry.simulator import VehicleSimulator
from fastapi import FastAPI, WebSocket
from prometheus_fastapi_instrumentator import Instrumentator
import random
import asyncio

app = FastAPI(title="Vehicle Telemetry API")

Instrumentator().instrument(app).expose(app)

simulator = VehicleSimulator()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/telemetry/latest")
def latest():
    return simulator.get_state()

@app.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            telemetry = simulator.get_state()
            await websocket.send_json(telemetry)
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket baglantisi kapandi: {e}")

@app.on_event("startup")
async def start_simulation():
    asyncio.create_task(simulator.run())
