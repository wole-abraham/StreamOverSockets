import cv2,  base64, asyncio, websockets


async def send_frame():
    uri = None
    cap = cv2.VideoCapture(0)

    async with websockets.connect(uri, max_size=2**24) as ws:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            await ws.send(base64.b64encode(buffer).decode("utf-8"))


asyncio.run(send_frame())