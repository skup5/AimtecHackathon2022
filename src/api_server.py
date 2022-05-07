#!/usr/bin/env python3

import http.server as SimpleHTTPServer
import socketserver as SocketServer
import logging
import serial

from commander import Commander

PORT = 8000

serialArduino = serial.Serial('/dev/ttyACM0', 9600, timeout=0)
lights = 0


class GetHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    # SimpleHTTPServer.SimpleHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        self.serialArduino = serial.Serial('/dev/ttyACM0', 9600, timeout=0)
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)
        self.commander = Commander()

    def send2Arduino(self, str):
        global serialArduino
        # print("Pi->Arduino: " + str)
        serialArduino.write(str.encode())

    def do_GET(self):
        global lights
        # logging.error(self.headers)
        print(self.headers)
        cmd = self.path.split("=")[1]
        # self.serialArduino(arduino)
        arduino_cmd = self.commander.translate_command(cmd)
        print(cmd + ' -> "' + arduino_cmd + '"')
        self.send2Arduino(str(arduino_cmd))
        lights = (lights + 1) % 6
        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)


if __name__ == "__main__":
    Handler = GetHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    httpd.serve_forever()
