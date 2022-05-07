#!/usr/bin/python3

import asyncio
from typing import Optional

import serial_asyncio


class InternalServer(asyncio.DatagramProtocol):
    def __init__(self,
                 SERVER_NAME,
                 SERIAL_BAUD_RATE,
                 SERIAL_PORT
                 ):
        self.SERVER_NAME = SERVER_NAME
        self.SERIAL_BAUD_RATE = SERIAL_BAUD_RATE
        self.SERIAL_PORT = SERIAL_PORT

        self.arduino_reader = None  # type: asyncio.StreamReader
        self.arduino_writer = None  # type: asyncio.StreamWriter

    async def _setupSerial(self):
        try:
            self.arduino_reader, self.arduino_writer = \
                await serial_asyncio.open_serial_connection(url=self.SERIAL_PORT, baudrate=self.SERIAL_BAUD_RATE)
        except:
            print("SERIAL no port found : no arduino communication ")

    async def _listen_serial(self):
        await self._setupSerial()
        if self.arduino_reader is None:
            return
        while True:
            try:
                line = await self.arduino_reader.readline()
                response = await self.on_received_serial(str(line, 'utf-8'))
                if response is not None:
                    await self.send_message_serial(response)
            except Exception as e:
                print("SERIAL " + str(e))

    async def send_message_serial(self, message: str):
        print('send to ARDUINO: ' + message)
        # if self.arduino_reader is None:
        #     return
        # self.arduino_writer.write(bytes(message, 'utf-8'))
        # await self.arduino_writer.drain()

    async def on_received_serial(self, message: str) -> Optional[str]:
        """Called when UDP message was received.

           returns string to be sent as a response
           """
        pass

    def start(self):
        asyncio.get_event_loop().run_until_complete(
            asyncio.gather(self._listen_serial()))
        try:
            asyncio.get_event_loop().run_forever()

        except KeyboardInterrupt:
            print("Exiting server")
