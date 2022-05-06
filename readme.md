## Robot Server
Robot server consists of 3 main parts:
1. UDP discovery responses
    - client broadcasts a request on the network and server replies with its ip address 
2. Websocket robot control
    - client sends commands to the server, server sends them to Arduino (and vice versa)
3. HTTP + WS camera stream
    - separate server providing camera feed which can be viewed from any browser on the network

## Installation on RPI
clone this repo on Raspberry PI (e.g. to home folder)
```
git clone https://gitlab.com/zswi-robot-app/zswi-robot-app
```
install necessary python packages using pip
```
cd ./zswi-robot-app/server
pip install -r requirements.txt
```
install server as a service that will run on every boot.  
the following script creates and starts the service immediately:
```
sudo bash ./install_service.sh <optional server name>
```
(Server name e.g. `RPI#1` can be passed as a parameter)  
**Note:** do not remove this cloned repo as it is used by the service.  
To see a live console output run:
```
sudo bash ./read_logs.sh
```
## Server without service
To start server without any service simply run server.py:
```
python3 ./server.py
```

## Changing parameters
Many parameters can be changed in section `==CONSTANTS==` in *server.py*.
- `SERVER_NAME` name that will be displayed to clients (e.g. `RPI #1`)
- `CAM_RESOLUTION` resolution of camera (smaller is faster)
- `CAM_FRAMERATE` frames per sec (smaller is faster)
- `SERIAL_PORT` Arduino serial port
- `PORT_WEBSOCKET` port for WS communication
- `PORT_UDP_IN` listening port for client discovery requests
- `PORT_UDP_OUT` port to send discovery responses to
- and so on...

##### Optional Program Arguments
Can be set only when directly running file *./server.py* without using a service.
To see a list of available arguments type:
```
python3 ./server.py -h
```
Example running the server with custom server name, camera resolution and framerate:
```
python3 ./server.py --name ROBOT1 --resolution 1280 720 --framerate 20
```

