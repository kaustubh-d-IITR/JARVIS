import asyncio
import os
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class AudioTranscriber:
    def __init__(self):
        pass
            
    async def transcribe_audio_async(self, file_path: str) -> str:
        api_key = settings.DEEPGRAM_API_KEY
        if not api_key:
            return "Error: Deepgram API key not configured."
            
        deepgram = DeepgramClient(api_key)
            
        try:
            with open(file_path, "rb") as audio:
                buffer_data = audio.read()

            payload: FileSource = {
                "buffer": buffer_data,
            }

            options = PrerecordedOptions(
                model="nova-2",
                smart_format=True,
            )

            # Deepgram SDK allows async calling if needed, but we'll run it in a thread 
            # to avoid blocking if the sync client is used. The SDK supports `listen.prerecorded.v("1")`
            # For simplicity in Streamlit, we can just run the sync call in an executor or use asyncio.to_thread
            response = await asyncio.to_thread(
                deepgram.listen.prerecorded.v("1").transcribe_file,
                payload,
                options
            )
            
            transcript = response.results.channels[0].alternatives[0].transcript
            
            # Clean up temp file
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Could not remove temp audio file {file_path}: {e}")
                
            return transcript
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return f"Error: {str(e)}"
