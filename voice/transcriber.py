import asyncio
import os
import requests
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

        try:
            url = "https://api.deepgram.com/v1/listen"

            # Enhanced parameters for better accuracy
            # keywords with boost values prioritize recognition of command words
            params = {
                "model": "nova-2",
                "language": "en",
                "smart_format": "true",
                "punctuate": "true",
                "utterances": "false",
                "filler_words": "false",
                "profanity_filter": "false",
                "numerals": "true",
                "keywords": [
                    "pause:3",
                    "stop:3",
                    "play:3",
                    "music:2",
                    "song:2",
                    "JARVIS:3"
                ]
            }

            headers = {
                "Authorization": f"Token {api_key}",
                "Content-Type": "audio/wav"
            }

            # Read file and send POST request in a thread to avoid blocking async loop
            def fetch_transcription():
                with open(file_path, "rb") as audio:
                    return requests.post(url, headers=headers, params=params, data=audio)

            response = await asyncio.to_thread(fetch_transcription)

            if response.status_code == 200:
                data = response.json()
                transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
            else:
                transcript = f"Error: Deepgram API returned {response.status_code} - {response.text}"

            # Clean up temp file
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Could not remove temp audio file {file_path}: {e}")

            return transcript

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return f"Error: {str(e)}"
