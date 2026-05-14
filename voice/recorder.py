import pyaudio
import wave
import threading
import tempfile
import os
from utils.logger import get_logger

logger = get_logger(__name__)

class AudioRecorder:
    def __init__(self):
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.is_recording = False
        self.frames = []
        self.p = pyaudio.PyAudio()
        self.output_filename = None
        
    def start_recording(self):
        """Starts recording audio in a background thread."""
        if self.is_recording:
            return
            
        self.is_recording = True
        self.frames = []
        
        # Determine default input device
        try:
            default_device = self.p.get_default_input_device_info()
            logger.info(f"Using microphone: {default_device.get('name')}")
        except IOError:
            logger.error("No default input device found.")
            self.is_recording = False
            return
            
        # Create temp file for this recording
        fd, self.output_filename = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        self.thread = threading.Thread(target=self._record_loop)
        self.thread.start()
        
    def _record_loop(self):
        stream = self.p.open(format=self.format,
                             channels=self.channels,
                             rate=self.rate,
                             input=True,
                             frames_per_buffer=self.chunk)
                             
        logger.info("Recording started.")
        while self.is_recording:
            try:
                data = stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
            except Exception as e:
                logger.error(f"Error reading audio stream: {e}")
                
        logger.info("Recording stopped.")
        stream.stop_stream()
        stream.close()
        
        # Save to file
        wf = wave.open(self.output_filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
    def stop_recording(self) -> str:
        """Stops recording and returns the path to the saved WAV file."""
        self.is_recording = False
        if hasattr(self, 'thread'):
            self.thread.join()
        return self.output_filename
        
    def cleanup(self):
        self.p.terminate()
