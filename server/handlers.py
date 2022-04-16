import base64
import json
from datetime import datetime

import cv2
import numpy as np

AGGREGATE = 0
NUM_AUDI = 0
PRSNT_SCORE = 0
FGBG = cv2.createBackgroundSubtractorMOG2(detectShadows = False)
TIMER = None
TIME_DELAY = 5

class Person:
    def __init__(self, ws, name, uid, role):
        self.ws = ws
        self.name = name
        self.uid = uid
        self.role = role
        self.presence = 0
        self.num_frames = 0

    def __repr__(self):
        return self.name

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

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

async def processContent(meetCode, MEETS, img_uri):
    global TIMER
    frame = data_uri_to_cv2_img(img_uri)
    fgmask = FGBG.apply(frame)
    img = cv2.cvtColor(fgmask, cv2.COLOR_GRAY2RGB)
    median = cv2.medianBlur(img,5)
    whitePixel = np.sum(median==255)
    if whitePixel > 1000:
        if TIMER is None:
            print("START")
            await requestClient(meetCode, MEETS, "frames")
        TIMER = datetime.now()
    elif TIMER is not None and (datetime.now()-TIMER).total_seconds() > TIME_DELAY:
            print("TIME OUT")
            await requestClient(meetCode, MEETS, "stop")
            TIMER = None

async def addNewPerson(websocket, msg, MEETS):
    print(msg)
    if msg["meetCode"] not in MEETS.keys():
        MEETS[msg["meetCode"]] = {"Host":{}, "Audi":{}}
    
    person = Person(websocket, msg["name"], msg["uid"], msg["role"])

    if msg["role"] == "Audi":
        adder = {"event": "Add new","name": person.name, "uid":person.uid}
        for host in MEETS[msg["meetCode"]]["Host"].values():
            await host.ws.send(json.dumps(adder))
    else:
        person.name = "Presentation Score"

    if msg["uid"] not in MEETS[msg["meetCode"]][msg["role"]].keys():
        MEETS[msg["meetCode"]][msg["role"]][msg["uid"]] = None

    MEETS[msg["meetCode"]][msg["role"]][msg["uid"]] = person
    del person

    print(MEETS)

async def requestClient(meetCode, MEETS, request):
    event = None
    if request == "frames":
        event = "Request Frames"
    elif request == "stop":
        event = "Stop Frames"
    for host in MEETS[meetCode]["Host"].values():
        requestJson = {"event": event}
        await host.ws.send(json.dumps(requestJson))

    for member in MEETS[meetCode]["Audi"].values():
        requestJson = {"event": event}
        await member.ws.send(json.dumps(requestJson))

async def replyScore(websocket, msg, MEETS):
    global AGGREGATE, NUM_AUDI, PRSNT_SCORE, TIMER

    person = MEETS[msg["meetCode"]][msg["role"]][msg["uid"]]

    if not msg["end"]:
        person.num_frames += 1
        person.presence += calc_presence(msg["data"])
    else:
        response = {"event": "Update", "name": person.name, "uid": person.uid, "presence": str(round(100*(person.presence)/(person.num_frames)))}
        await websocket.send(json.dumps(response))
        if msg["role"] == "Audi":
            for host in MEETS[msg["meetCode"]]["Host"].values():
                await host.ws.send(json.dumps(response))
            
            AGGREGATE += round(100*(person.presence)/(person.num_frames))
            NUM_AUDI += 1
            if NUM_AUDI == len(MEETS[msg["meetCode"]]["Audi"].keys()):
                table_response = {"event": "Add Row", "time": datetime.now().strftime("%I:%M:%S %p"), "score": str(PRSNT_SCORE), "aggregate": str(round(AGGREGATE/NUM_AUDI))}
                for host in MEETS[msg["meetCode"]]["Host"].values():
                    await host.ws.send(json.dumps(table_response))
                AGGREGATE = 0
                NUM_AUDI = 0
                PRSNT_SCORE = 0
        else:
            PRSNT_SCORE = round(100*(person.presence)/(person.num_frames))
        person.presence, person.num_frames = 0, 0
        TIMER = None

def backgroundSubtractor(frames):
    startTimeList = []
    endTimeList = []
    flag = True
    frameNum = 0
    
    for frame in frames:
        frameNum += 1
        fgmask = FGBG.apply(frame)
        img = cv2.cvtColor(fgmask, cv2.COLOR_GRAY2RGB)
        median = cv2.medianBlur(img,5)
        
        whitePixel = np.sum(median==255)
        if whitePixel > 1000 and flag:
            startTimeList.append(frameNum)
            flag = False
        elif whitePixel < 1000 and not flag:
            endTimeList.append(frameNum)
            flag = True

        finalStartTimeList = [startTimeList[2]]
        finalEndTimeList = [endTimeList[2]]
        k = 1
        # if len(endTimeList) > 2:
        #     if len(startTimeList) == 2:


