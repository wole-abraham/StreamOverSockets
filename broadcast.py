from fastapi import FastAPI,  WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles



app = FastAPI()
last_frame = None

@app.websocket("/ws/stream")
async def stream_socket(websocket: WebSocket):
    global last_frame
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        last_frame = data

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
    <body>
      <h1>Live Stream</h1>
      <img id="feed" width="640"/>
      <script>
        async function update() {
          const res = await fetch('/frame');
          const blob = await res.blob();
          document.getElementById('feed').src = URL.createObjectURL(blob);
          requestAnimationFrame(update);
        }
        update();
      </script>
    </body>
    </html>
    """
@app.get("/frame")
async def get_frame():
    from fastapi.responses import Response
    global last_frame
    if last_frame is None:
        return Response(status_code=404)
    import base64
    img = base64.b64decode(last_frame)
    return Response(content=img, media_type="image/jpeg")