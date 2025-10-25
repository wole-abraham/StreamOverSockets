from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
import asyncio

app = FastAPI()
templates = Jinja2Templates(directory="templates")

pcs = set()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer

@app.post("/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # Use only STUN (Google)
    config = RTCConfiguration(
    iceServers=[
        {"urls": ["stun:stun.l.google.com:19302"]},
        {
            "urls": [f"turn:69.62.122.230:3478"],
            "username": "9e5ea9665c2529f427000d7a",
            "credential": "KCCPb8Ase9yyvB8Z"
        }
    ]
)



    pc = RTCPeerConnection(configuration=config)
    pcs.add(pc)

    @pc.on("iceconnectionstatechange")
    def on_state_change():
        print("ICE connection state:", pc.iceConnectionState)
        if pc.iceConnectionState in ("failed", "closed", "disconnected"):
            asyncio.create_task(pc.close())
            pcs.discard(pc)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
