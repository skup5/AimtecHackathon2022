import pyaudio

p = pyaudio.PyAudio()
for ii in range(p.get_device_count()):
    # This should output the index of each audio-capable device on your Pi.
    # You are looking for index of the USB device (like USB PnP Sound Device: Audio)
    print(p.get_device_info_by_index(ii).get('name'))
