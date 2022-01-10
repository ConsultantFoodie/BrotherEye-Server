#!/usr/bin/env python

# WS server example

import asyncio
import websockets
import base64
import cv2
import numpy as np

def data_uri_to_cv2_img(uri):
    encoded_data = uri.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def calc_presence(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    return int(len(faces)>0)

num=0
presence=0
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

async def hello(websocket, path):
    async for message in websocket:
        global num,presence
        if len(message) > 20:
            # print("NUM:", num)
            # print(message)
            # print("got image {}".format(num))
            num += 1
            img = data_uri_to_cv2_img(message)
            presence += calc_presence(img)
        else:
            print(message)
            print(presence, num)
            await websocket.send(str(round(100*presence/num)))
            presence, num = 0, 0
        
        # with open("./photos/img_{}.jpg".format(num),"wb") as f:
            


    

async def main():
    async with websockets.serve(hello, "localhost", 8000):
        await asyncio.Future()  # run forever

asyncio.run(main())