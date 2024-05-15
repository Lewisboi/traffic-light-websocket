import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from dotenv import load_dotenv
from pydantic import BaseModel
from enum import Enum
import logging

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "localhost")
TRAFFIC_LIGHT_CHANNEL = os.getenv("TRAFFIC_LIGHT_CHANNEL", "traffic-light-channel")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(host=REDIS_URL, port=6379)

logging.basicConfig(level=logging.INFO)


class Color(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class TrafficLightUpdateRequest(BaseModel):
    color: Color


@app.post("/update-traffic-light")
async def handle_update_traffic_light(update_request: TrafficLightUpdateRequest):
    try:
        message = update_request.json()
        await redis_client.publish(TRAFFIC_LIGHT_CHANNEL, message)
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Error publishing to Redis: {e}")
        return {"status": "error", "detail": str(e)}


@app.websocket("/traffic-light")
async def handle_traffic_light_connection(websocket: WebSocket):
    await websocket.accept()
    pubsub = redis_client.pubsub()
    try:
        await pubsub.subscribe(TRAFFIC_LIGHT_CHANNEL)
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_json(message["data"].decode())
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()
        await pubsub.unsubscribe(TRAFFIC_LIGHT_CHANNEL)
        await pubsub.close()
