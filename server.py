#!/usr/bin/env python

# WS server example

import asyncio
import websockets
import base64
import cv2
import numpy as np
import json

class Person:
    def __init__(self, ws, email, role):
        self.ws = ws
        self.name = email.split("@")[0]
        self.email = email
        self.role = role
        self.presence = 0
        self.num_frames = 0

    def __repr__(self):
        return self.email

def data_uri_to_cv2_img(uri):
    encoded_data = uri.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def calc_presence(uri):
    img = data_uri_to_cv2_img(uri)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    return int(len(faces)>0)

MEETS = {}
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

async def handler(websocket, path):
    async for message in websocket:
        msg = json.loads(message)
        if msg["event"] == "init":
            print(msg)
            if msg["meetCode"] not in MEETS.keys():
                MEETS[msg["meetCode"]] = {"Host":[], "Audi":[]}
            
            person = Person(websocket, msg["email"], msg["role"])

            if msg["role"] == "Audi":
                adder = {"event": "Add new","name": person.name}
                for host in MEETS[msg["meetCode"]]["Host"]:
                    await host.ws.send(json.dumps(adder))
            else:
                person.name = "Presentation Score"

            MEETS[msg["meetCode"]][msg["role"]].append(person)
            del person

            print(MEETS)
        elif msg["event"] == "process":
            for person in MEETS[msg["meetCode"]][msg["role"]]:
                if person.email == msg["email"]:
                    if not msg["end"]:
                        person.num_frames += 1
                        person.presence += calc_presence(msg["data"])
                    else:
                        print(person.email, person.presence, person.num_frames)
                        response = {"event": "Update", "name": person.name, "presence": str(round(100*(person.presence)/(person.num_frames)))}
                        await websocket.send(json.dumps(response))
                        if person.role == "Audi":
                            for host in MEETS[msg["meetCode"]]["Host"]:
                                await host.ws.send(json.dumps(response))
                        
                        del response
                        person.presence, person.num_frames = 0, 0

async def main():
    async with websockets.serve(handler, "", 8000):
        await asyncio.Future()  # run forever

asyncio.run(main())