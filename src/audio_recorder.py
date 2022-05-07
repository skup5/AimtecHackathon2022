import pyaudio
import wave
from datetime import datetime

from speech_to_text import convert


def record(dev_index, record_secs=0):
    """

    :param dev_index: device index found by usb_mic_test.py (p.get_device_info_by_index(ii))
    :param record_secs: seconds to record. If 0, opens audio stream and returns this stream
    :return stream
    """
    form_1 = pyaudio.paInt16  # 16-bit resolution
    chans = 1  # 1 channel
    samp_rate = 44100  # 44.1kHz sampling rate
    chunk = 4096  # 2^12 samples for buffer
    # record_secs = 3  # seconds to record
    # dev_index = 2  # device index found by p.get_device_info_by_index(ii)
    wav_output_filename = 'record_' + str(get_timestamp()) + '.wav'  # name of .wav file

    audio = pyaudio.PyAudio()  # create pyaudio instantiation

    # create pyaudio stream
    stream = audio.open(format=form_1, rate=samp_rate, channels=chans, \
                        input_device_index=dev_index, input=True, \
                        frames_per_buffer=chunk)
    print("recording")
    frames = []

    if record_secs > 0:
        record_into_file(audio, chans, chunk, form_1, frames, record_secs, samp_rate, stream, wav_output_filename)
        res = convert(wav_output_filename)
        # print(res.json())
        return res.text
    else:
        data = stream.read(chunk)


def record_into_file(audio, chans, chunk, form_1, frames, record_secs, samp_rate, stream, wav_output_filename):
    # loop through stream and append audio chunks to frame array
    for ii in range(0, int((samp_rate / chunk) * record_secs)):
        data = stream.read(chunk)
        frames.append(data)
    print("finished recording")
    # stop the stream, close it, and terminate the pyaudio instantiation
    stream.stop_stream()
    stream.close()
    audio.terminate()
    # save the audio frames as .wav file
    wavefile = wave.open(wav_output_filename, 'wb')
    wavefile.setnchannels(chans)
    wavefile.setsampwidth(audio.get_sample_size(form_1))
    wavefile.setframerate(samp_rate)
    wavefile.writeframes(b''.join(frames))
    wavefile.close()


def get_timestamp() -> float:
    # Getting the current date and time
    dt = datetime.now()

    # getting the timestamp
    ts = datetime.timestamp(dt)

    # print("Date and time is:", dt)
    # print("Timestamp is:", ts)

    return ts


# record(2, 5)
