#!/usr/bin/env python3

import http.server as SimpleHTTPServer
import sched
import socketserver as SocketServer
import logging
import serial
import time
import urllib.parse

from commander import Commander

PORT = 8000
# send STOP cmd to arduino after [X] s
STOP_DELAY = 2


serialArduino = serial.Serial('/dev/ttyACM0', 9600, timeout=0)


def should_stop(arduino_cmd):
    if arduino_cmd in ['w', 's', 'd', 'a']:
        return True
    else:
        return False


class GetHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    # SimpleHTTPServer.SimpleHTTPRequestHandler):

    commander = Commander()

    def __init__(self, request, client_address, server):
        self.serialArduino = serial.Serial('/dev/ttyACM0', 9600, timeout=0)
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def send2Arduino(self, str):
        global serialArduino
        # print("Pi->Arduino: " + str)
        serialArduino.write(str.encode())

    def do_GET(self):
        global lights
        # logging.error(self.headers)
        print(self.headers)
        parameter = self.path.split("=")
        if len(parameter) > 0:
            cmd = urllib.parse.unquote(parameter[1])
            # self.serialArduino(arduino)
            arduino_cmd = self.commander.translate_command(cmd)
            print(cmd + ' -> "' + arduino_cmd + '"')
            self.send2Arduino(str(arduino_cmd))
            if should_stop(arduino_cmd):
                s = sched.scheduler(time.time, time.sleep)
                s.enter(STOP_DELAY, 1, self.send_stop, ())
                s.run()

        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def send_stop(self):
        self.send2Arduino(str(self.commander.translate_command('stop')))


if __name__ == "__main__":
    Handler = GetHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    print('server is listening on ' + str(PORT))
    httpd.serve_forever()
