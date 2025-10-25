from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import WebSocket
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import json, asyncio, cv2
import av

app = FastAPI()
templates = Jinja2Templates(directory="templates")

pcs = set()  # store active peer connections

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("iceconnectionstatechange")
    def on_state_change():
        if pc.iceConnectionState == "failed":
            asyncio.create_task(pc.close())
            pcs.discard(pc)

    # There’s no video source here on Render — it just receives
    # an incoming connection from your PC and sends SDP answers.
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
