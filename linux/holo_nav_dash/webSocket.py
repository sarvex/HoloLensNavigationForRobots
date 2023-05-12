# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import sys
import os
import time
import numpy as np 
import enum 
import copy
import json
import gevent
from gevent.queue import Queue, Empty
from gevent.event import AsyncResult
from flask import Flask, render_template
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource, WebSocketError
from collections import OrderedDict

# -----------------------------------------------------------------------------
#
class webSocket(WebSocketApplication):
    msgType = "msgType"
    eMsgType = enum.Enum(msgType, "addClient removeClient status")

    EMsgKey = enum.Enum("EMsgKey", "msgType client")

    application = None
    initialized = False
    queue = Queue()
    clients = set() 

    # -----------------------------------------------------------------------------
    #
    def on_open(self):
        if (self.initialized is not True):
            if (self.application is not None):
                self.application.setCallbackSendMessage(self.sendMessage)
                self.application.setCallbackQueueMessage(self.queueMessage)
            else:
                print("websocket: application object expected.")

            gevent.spawn(self.handle_queue_messages)
            self.initialized = True

        self.addClient(self)
        self.sendInitialization(self.ws)

    # -----------------------------------------------------------------------------
    #
    def on_close(self, reason):
        self.removeClient(self)

    # -----------------------------------------------------------------------------
    #
    def on_message(self, msg):
        if msg is None:
            return

        msg = json.loads(msg)

        # print ("on_message(): ", msg)

        if msg[self.msgType] == "calibrateHoloLens":
            self.CalibrateHoloLens()
        elif msg[self.msgType] == "startNode":
            self.StartNode(msg['startNode'])
        elif msg[self.msgType] == "quitApplication":
            self.quitApplication()
        else:
            print(f"invalid message, msg = '%s'{str(msg)}")

    # -----------------------------------------------------------------------------
    #
    def handle_queue_messages(self):
        msg = None
        while True:
            msg = self.queue.get()

            #if msg is not None:
            #    print("msg: '" + str(msg[self.msgType]) + "'")
            #else:
            #    print("msg: none")

            if msg is None:
                pass
            elif msg[self.msgType] is self.eMsgType.addClient:
                self.clients.add(msg[self.EMsgKey.client])
            elif msg[self.msgType] is self.eMsgType.removeClient:
                self.clients.discard(msg[self.EMsgKey.client])
            elif (msg[self.msgType] == "status"):
                j = json.dumps(msg)
                self.sendMessage(j)
            elif (msg[self.msgType] == "pose"):
                j = json.dumps(msg)
                self.sendMessage(j)
            elif (msg[self.msgType] == "exit_handle_queue_messages"):
                break
            else:
                print("handle_queue_messages(): invalid message, msgType = %s", msg[self.msgType])

            gevent.sleep(0.02)

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def close(cls):
        if cls.queue is not None:
            msg = {cls.msgType: "exit_handle_queue_messages"}
            cls.queue.put(msg)

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def setApplication(cls, application):
        cls.application = application

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def addClient(cls, client):
        msg = {cls.msgType: cls.eMsgType.addClient, cls.EMsgKey.client: client}

        cls.queue.put(msg)

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def removeClient(cls, client):
        msg = {cls.msgType: cls.eMsgType.removeClient, cls.EMsgKey.client: client}

        cls.queue.put(msg)

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def sendInitialization(cls, ws):
        if cls.application is None:
            print(f"sendInitialization(): application object expected, client: {id(ws)}")
            return

        status = {cls.msgType: "initialization"}

        #status["gestureInfo"] = self.application.getGestureInfo()
        #status["status"] = self.application.getStatus()
        #status["pose"] = self.application.getPose()

        #
        # serialize
        j = json.dumps(status)

        try:
            ws.send(j)
        except:
            print(f"sendInitialization() exception, client: {id(ws)}")

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def queueMessage(cls, msg):
        cls.queue.put(msg)

    # -----------------------------------------------------------------------------
    #
    def handleException(self, e, msg):
        if e.message:
            print(f"{msg} {e.message}")
        elif ((e.errno) and (e.errno == 2)):
            print(f"{msg} '{e.filename}' - {e.strerror}")
        else:
            print(f"{msg} {e.strerror}")

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def sendMessage(cls, msg):
        j = json.dumps(msg)
        ws = None
        try:
            for client in cls.clients:
                ws = client.ws
                ws.send(j)
        except Exception as e:
            cls.handleException(
                e, f"application.sendMessage() exception, client: {id(ws)}"
            )

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def CalibrateHoloLens(cls):
        try:
            if cls.application is not None:
                cls.application.CalibrateHoloLens()
        except Exception as e:
            cls.handleException(
                e, f"application.CalibrateHoloLens() exception, client: {id(ws)}"
            )

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def StartNode(cls, name):
        try:
            if cls.application is not None:
                cls.application.StartNode(name)
        except Exception as e:
            cls.handleException(e, f"application.StartNode() exception, client: {id(ws)}")

    # -----------------------------------------------------------------------------
    #
    @classmethod
    def quitApplication(cls):
        try:
            if cls.application is not None:
                cls.application.quitApplication()
        except Exception as e:
            cls.handleException(
                e, f"application.quitApplication() exception, client: {id(ws)}"
            )

