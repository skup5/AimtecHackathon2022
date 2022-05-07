#!/usr/bin/python3

import argparse
import asyncio
import json
import os.path
from typing import Optional

import yaml
from requests import post

# ------------------------------------------------------------------
# Asynchronous one thread WebSocket and UDP server to be used on
# RPI robot to control the robot based on requests
# from a client
#
#  broadcasts discovery request via UDP to find servers on the network
# Servers send back UDP response
# Client connects to the server via WS to control the robot
# only 1 concurrent client may be connected to the server via WS
#
# Separately on a different thread a separate HTTP+WS server is sending camera stream
# ------------------------------------------------------------------
from arduino_server import InternalServer

# ==================================CONSTANTS==================================
SERVER_NAME = "<nameless>"
SERIAL_BAUD_RATE = 115200
SERIAL_PORT = '/dev/ttyUSB0'

FEEDBACK_URI_BASE = 'http://147.228.124.48:7000/dialog/'


# SERIAL_PORT = (str(check_output(['ls /dev/ttyACM*']).decode()).strip())

class Message:
    # keys
    REQUEST = "REQUEST"
    SERVER_NAME = "SERVER_NAME"
    SERVER_IP = "SERVER_IP"
    CLIENT_IP = "CLIENT_IP"
    SUCCESS = "SUCCESS"
    MESSAGE = "MESSAGE"

    REBOOT = "REBOOT"

    # serial status variables
    SS_LIFT_DIRECTION = "SERIAL_LIFT_DIRECTION"
    SS_LIFT_POSITION = "SERIAL_LIFT_POSITION"
    SS_ODO_LEFT = "SERIAL_ODO_LEFT"
    SS_ODO_RIGHT = "SERIAL_ODO_RIGHT"
    SS_LASER_DISTANCE = "SERIAL_LASER_DISTANCE"
    SS_SPEED = "SERIAL_SPEED"

    # serial command variables
    REQUEST_SC_COMMAND = "REQUEST_SC_COMMAND"
    SC_SPEED_UP = "+"
    SC_SPEED_DOWN = "-"
    SC_LIFT_UP = "e"
    SC_LIFT_DOWN = "q"
    SC_FORWARD = "w"
    SC_BACKWARD = "s"
    SC_LEFT = "a"
    SC_RIGHT = "d"
    SC_LASER_ON = "l"
    SC_LASER_OFF = "k"
    SC_DEBUG = "i"
    SC_DEMO = "x"
    SC_STOP = " "
    SC_RESET = "0"
    SC_VELOCITY = "v"

    SC_LIGHT = "L"


# ==================== CONSTANTS_FROM_PROGRAM_ARGUMENTS========================

if os.path.exists("config.yaml"):
    try:
        with open('config.yaml', 'r', encoding='utf-8') as open_yml:
            doc = yaml.full_load(open_yml)
            for name, val in doc.items():
                if name in globals():
                    if type(val) is type(globals()[name]):
                        globals()[name] = val
                    else:
                        print("Invalid parameter type in config.yaml: " + name
                              + ", Expected " + str(type(globals()[name]))
                              + " Got " + str(type(val)))
                else:
                    print("Invalid parameter name in config.yaml: " + name)
            print("Loaded config.yaml")
    except:
        print("Invalid config.yaml - skipping")

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", help="sets server name", type=str, default=SERVER_NAME)

args = parser.parse_args()
SERVER_NAME = args.name


def parse_feedback(message: str):
    if message.startswith('1'):
        return 'ok'
    elif message.startswith('0'):
        return 'no'
    else:
        return ''


class MainServer(InternalServer):

    def __init__(self, SERVER_NAME, SERIAL_BAUD_RATE, SERIAL_PORT):

        super().__init__(SERVER_NAME, SERIAL_BAUD_RATE, SERIAL_PORT)

        self.ARDUINO_STATUS = {}

    def proccessShutdown(self, jso: json):
        reboot = Message.MESSAGE in jso and jso[Message.MESSAGE] == Message.REBOOT

        from subprocess import call
        if reboot:
            print("Received reboot command")
            call("sudo reboot now", shell=True)
        else:
            print("Received shutdown command")
            call("sudo shutdown now", shell=True)

    async def on_received_serial(self, message: str) -> Optional[str]:
        print('ARDUINO: ' + message)
        feedback = parse_feedback(message)
        print(feedback)
        if feedback:
            print('sending: ' + feedback)
            ans = self.send_http_feedback(feedback)
            print(ans)

        return

    def send_http_feedback(self, feedback):
        body = {
            'feedback': feedback,
            'device': 'touch'
        }
        ans = post(FEEDBACK_URI_BASE, json.dumps(body)).json()['answer']
        return ans


server = MainServer(SERVER_NAME, SERIAL_BAUD_RATE, SERIAL_PORT)

print("Starting server")
print(" - ServerName: " + SERVER_NAME)

server.start()

# asyncio.run(server.send_http_feedback("ok"))
