#!/usr/bin/python3

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
import ipaddress
import os.path

import websockets
import asyncio
import json
import yaml
from typing import Union, Optional
from websockets import WebSocketServerProtocol as WSSProtocol
from netifaces import interfaces, ifaddresses, AF_INET
import argparse
from stream_picamera_h264.PiCamera_H264_Server import VideoStreamer

# ============================CONDITIONAL_IMPORTS============================

is_serial_imported = False

try:
    import serial_asyncio

    is_serial_imported = True
except:
    print("SERIAL library not found")

# ==================================CONSTANTS==================================
SERVER_NAME = "<nameless>"
PORT_WEBSOCKET = 7890
HOST_IP = "0.0.0.0"
SUBNET_MASK = "255.255.255.0"
SERIAL_BAUD_RATE = 9600
SERIAL_PORT = '/dev/ttyACM0'
# SERIAL_PORT = (str(check_output(['ls /dev/ttyACM*']).decode()).strip())
PORT_UDP_IN = 7891  # PORT FOR LISTEN FOR UDP REQUESTS
PORT_UDP_OUT = 7892  # PORT TO SEND RESPONSES TO
CAM_PORT_HTTP = 8000
# !NOTE if you change this global, you have to change camera port in CAM_SERVER_ROOT_DIR/index.html
CAM_PORT_WEBSOCKET = 9000
CAM_RESOLUTION = [640, 480]
CAM_FRAMERATE = 24
CAM_SERVER_ROOT_DIR = "./stream_picamera_h264"


def ip4_addresses():
    ip_list = []
    for interface in interfaces():
        if len(ifaddresses(interface)) > AF_INET:
            for link in ifaddresses(interface)[AF_INET]:
                ip_list.append(link['addr'])
    return ip_list


HOST_WEBSOCKETS = ip4_addresses()


def _getHostIP(clientIp: str) -> Optional[str]:
    mask = int(ipaddress.IPv4Address(SUBNET_MASK))
    ip = int(ipaddress.IPv4Address(clientIp)) & mask
    for address in HOST_WEBSOCKETS:
        if (int(ipaddress.IPv4Address(address)) & mask) == ip:
            return address


def getHostIP(clientIp: str) -> Optional[str]:
    global HOST_WEBSOCKETS
    out = _getHostIP(clientIp)
    if out is None:
        # if no ip found -> update table
        HOST_WEBSOCKETS=ip4_addresses()
        out=_getHostIP(clientIp)
    if out is None:
        print("ERROR Can not find server IP on subnet with client IP: "+clientIp)
    return out


# Message keys of the protocol
class Message:
    # keys
    REQUEST = "REQUEST"
    SERVER_NAME = "SERVER_NAME"
    SERVER_IP = "SERVER_IP"
    CLIENT_IP = "CLIENT_IP"
    SUCCESS = "SUCCESS"
    MESSAGE = "MESSAGE"

    # values
    REQUEST_DISCOVERY = "REQUEST_DISCOVERY"
    REQUEST_KICKOUT = "REQUEST_KICKOUT"
    REQUEST_CONNECT = "REQUEST_CONNECT"
    REQUEST_TAKE_OVER = "REQUEST_TAKE_OVER"
    REQUEST_UPDATE = "REQUEST_UPDATE"

    # serial status variables
    SS_LIFT_DIRECTION = "SERIAL_LIFT_DIRECTION"
    SS_LIFT_POSITION = "SERIAL_LIFT_POSITION"
    SS_ODO_LEFT = "SERIAL_ODO_LEFT"
    SS_ODO_RIGHT = "SERIAL_ODO_RIGHT"
    SS_LASER_DISTANCE = "SERIAL_LASER_DISTANCE"

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

    SC_LIGHT = "L"


# ==================== CONSTANTS_FROM_PROGRAM_ARGUMENTS========================

if os.path.exists("config.yaml"):
    try:
        with open('config.yaml', 'r',encoding='utf-8') as open_yml:
            doc = yaml.full_load(open_yml)
            for name,val in doc.items():
                if name in globals():
                    if type(val) is type(globals()[name]):
                        globals()[name]=val
                    else:
                        print("Invalid parameter type in config.yaml: "+name
                              +", Expected "+str(type(globals()[name]))
                              +" Got "+str(type(val)))
                else:
                    print("Invalid parameter name in config.yaml: "+name)
            print("Loaded config.yaml")
    except:
        print("Invalid config.yaml - skipping")


parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", help="sets server name", type=str, default=SERVER_NAME)
parser.add_argument("-m", "--subnet-mask", help="determines if server ip and client ip are on same subnet", type=str,
                    default=SUBNET_MASK)
parser.add_argument("-f", "--framerate", help="camera fps", type=int, default=CAM_FRAMERATE)
parser.add_argument("-r", "--resolution", help="camera resolution: width height", nargs=2, type=int,
                    default=CAM_RESOLUTION)
args = parser.parse_args()
SERVER_NAME = args.name
CAM_FRAMERATE = args.framerate
CAM_RESOLUTION = args.resolution
SUBNET_MASK = args.subnet_mask
print("Starting server")
print(" - ServerName: " + SERVER_NAME)
print(" - Server IPs: " + str(HOST_WEBSOCKETS))
print(" - Camera FPS: " + str(CAM_FRAMERATE))
print(" - Camera RES: " + str(CAM_RESOLUTION))

# ==================================VARIABLES==================================

video_streamer = VideoStreamer(CAM_RESOLUTION[0], CAM_RESOLUTION[1], CAM_FRAMERATE, CAM_PORT_HTTP, CAM_PORT_WEBSOCKET,
                               CAM_SERVER_ROOT_DIR)

# current validated connected socket
connectedSocket = None  # type: WSSProtocol

# list of all opened websockets
openedSockets = []

arduino_reader = None  # type: asyncio.StreamReader
arduino_writer = None  # type: asyncio.StreamWriter

schedule_arduino_reset = False


# ============================EVENT_CALLBACKS==================================
def on_receive_udp(message: str, addr: tuple) -> Union[str, None]:
    """Called when UDP message was received.

    returns string to be sent as a response
    """
    global connectedSocket
    out = {}

    try:
        try:
            data = json.loads(message)
        except:
            out = {Message.SUCCESS: False, Message.MESSAGE: "Invalid JSON"}
            return json.dumps(out)

        action = data[Message.REQUEST]

        if action == Message.REQUEST_DISCOVERY:
            if connectedSocket is not None:
                out[Message.CLIENT_IP] = "EXISTS"

            #    out[Message.CLIENT_IP] = openedSockets[0].gethostname()
            out[Message.SERVER_NAME] = SERVER_NAME
            out[Message.SERVER_IP] = getHostIP(addr[0])
            out[Message.SUCCESS] = True

        elif action == Message.REQUEST_KICKOUT:
            out[Message.SUCCESS] = connectedSocket is not None

            if connectedSocket is not None:
                ws_remove_client(connectedSocket)
        else:
            out[Message.SUCCESS] = False
            out[Message.MESSAGE] = "INVALID_REQUEST"
        return json.dumps(out)

    except Exception as e:
        print("UDP " + str(e))
        out[Message.SUCCESS] = False
        out[Message.MESSAGE] = "ERROR_WHILE_PARSING_UDP_REQUEST"
        return json.dumps(out)


async def on_receive_ws(websocket: WSSProtocol, jso: {}):
    """Called when json object is received from client."""

    try:
        if jso[Message.REQUEST] == Message.REQUEST_SC_COMMAND and arduino_writer is not None:

            depeche = jso[Message.MESSAGE]
            if depeche.startswith(Message.SC_LIGHT):
                depeche = depeche[len(Message.SC_LIGHT):]

            await arduino_writer.drain()
            arduino_writer.write(bytes(depeche, 'utf-8'))
            await arduino_writer.drain()

            await websocket.send(json.dumps({Message.MESSAGE: "sEND COMMAND"}))
    except Exception as e:
        print("WS " + str(e))


# ======================MANAGING_CONNECTION_METHODS============================
async def ws_on_connected(websocket: WSSProtocol, path):
    """Entry point of newly created websocket."""
    ws_add_client(websocket)
    try:
        validated = False
        async for message in websocket:
            if not validated:
                validated = await ws_validate(websocket, message)
                if not validated:
                    print("WS Client was not validated - kicking out")
                    return
                continue

            print("WS Received > " + message)
            try:
                jso = json.loads(message)
                await on_receive_ws(websocket, jso)
            except:
                print("WS Invalid message from client")

            # await websocket.close()
    except:
        pass

    finally:
        print("WS Client disconnected")
        await ws_remove_client(websocket)


def ws_add_client(websocket: WSSProtocol):
    """Adds websocket to list of connected websockets.

    also activates camera if it's a first websocket for the server
    """

    print("WS New connection established")
    openedSockets.append(websocket)


async def ws_remove_client(websocket: WSSProtocol):
    """Disconnects client."""

    try:
        await websocket.close()
    except:
        print("WS socket already closed")

    global connectedSocket
    global openedSockets
    global schedule_arduino_reset

    if connectedSocket is not None and websocket == connectedSocket:
        schedule_arduino_reset = True

        connectedSocket = None
    if websocket in openedSockets:
        openedSockets.remove(websocket)


async def ws_validate(websocket: WSSProtocol, message: str) -> bool:
    """Validates websocket by checking the message received.

    returns true if socket was validated"""
    try:
        jso = json.loads(message)
        req = jso[Message.REQUEST]
        global connectedSocket

        out = {Message.SUCCESS: False}

        if req == Message.REQUEST_CONNECT:
            out[Message.SUCCESS] = connectedSocket is None
            if connectedSocket is None:
                connectedSocket = websocket

        elif req == Message.REQUEST_TAKE_OVER:
            out[Message.SUCCESS] = True
            if connectedSocket is not None:
                print("WS Kicking out old socket")
                await ws_remove_client(connectedSocket)
            connectedSocket = websocket

        await ws_send_json_message(websocket, out)
        return out[Message.SUCCESS]
    except Exception as e:
        print("WS " + str(e))
        return False


async def ws_send_json_message(websocket: WSSProtocol, obj: {}):
    """Send obj converted to json message."""
    await websocket.send(json.dumps(obj))


class UDPServerProtocol(asyncio.DatagramProtocol):
    """UDP entry point."""

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode()
        response = on_receive_udp(message, addr)
        if response is not None:
            self.transport.sendto(bytearray(response, "UTF-8"), (addr[0], PORT_UDP_OUT))

        print('UDP Received %r from %s' % (message, addr))
        if response is not None:
            print('UDP Send %r to %s' % (response, (addr[0], PORT_UDP_OUT)))

    def error_received(self, exc):
        print("UDP Error: " + str(exc))
        print("UDP Restarting")
        self.transport.close()
        startUDP = asyncio.get_event_loop().create_datagram_endpoint(
            lambda: UDPServerProtocol(),
            local_addr=(HOST_IP, PORT_UDP_IN))
        asyncio.get_event_loop().create_task(startUDP)


async def listenSerial():
    global is_serial_imported

    if not is_serial_imported:
        print("SERIAL no lib found : no arduino communication")
        return

    global arduino_reader
    global arduino_writer
    try:
        arduino_reader, arduino_writer = await serial_asyncio.open_serial_connection(url=SERIAL_PORT,
                                                                                     baudrate=SERIAL_BAUD_RATE)
    except:
        print("SERIAL no port found : no arduino communication")
        is_serial_imported = False
        return

    print("SERIAL connection opened on " + SERIAL_PORT + " with baud-rate " + str(SERIAL_BAUD_RATE))
    global schedule_arduino_reset

    while True:
        try:
            line = await arduino_reader.readline()

            if schedule_arduino_reset:
                print("SERIAL resetting arduino after ws disconnected")
                schedule_arduino_reset = False
                await arduino_writer.drain()
                arduino_writer.write(bytes(Message.SC_RESET, 'utf-8'))
                await arduino_writer.drain()

            if connectedSocket is not None:
                if not str(line, 'utf-8').startswith("Lift("):
                    await ws_send_json_message(connectedSocket, {
                        Message.REQUEST: Message.REQUEST,  # todo change request type
                        Message.MESSAGE: str(line, 'utf-8')})
                    continue

                mes = parseSerialStatusToJSON(str(line, 'utf-8'))
                await ws_send_json_message(connectedSocket, {
                    Message.REQUEST: Message.REQUEST_UPDATE,
                    Message.MESSAGE: mes})
        except Exception as e:
            print("SERIAL " + str(e))


def parseSerialStatusToJSON(s: str):
    s = s.replace(")", "(")
    spl = s.split("(")

    s = spl[1].split(",")
    out = {
        Message.SS_LIFT_DIRECTION: int(s[0]),
        Message.SS_LIFT_POSITION: int(s[1]),
    }
    s = spl[3].split(",")
    out[Message.SS_ODO_LEFT] = int(s[0])
    out[Message.SS_ODO_RIGHT] = int(s[1])
    out[Message.SS_LASER_DISTANCE] = int(spl[5])
    return out


# ================SETUP_WS_AND_UDP_SERVER_USING_ASYNCIO=======================
video_streamer.stream()

startServer = websockets.serve(ws_on_connected, HOST_IP, PORT_WEBSOCKET)
startUDP = asyncio.get_event_loop().create_datagram_endpoint(
    lambda: UDPServerProtocol(),
    local_addr=(HOST_IP, PORT_UDP_IN))

print("CAMERA HTTP server started on : " + str(HOST_IP) + ":" + str(CAM_PORT_HTTP))
print("CAMERA WS server started on : " + str(HOST_IP) + ":" + str(CAM_PORT_WEBSOCKET))
print("UDP server started on : " + str(HOST_IP) + ":" + str(PORT_UDP_IN))
print("WS server started on : " + str(HOST_IP) + ":" + str(PORT_WEBSOCKET))


# schedule all necessary coroutines to event_loop
asyncio.get_event_loop().run_until_complete(
    asyncio.gather(listenSerial(), startServer, startUDP))
try:
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    print("Exiting server")
