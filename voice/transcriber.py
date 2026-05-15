import asyncio
import os
import requests
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AudioTranscriber:
    def __init__(self):
        pass

    def _is_likely_music_bleed(self, transcript: str) -> bool:
        """
        Detect if the transcript is likely music lyrics rather than
        a voice command. Music bleed transcriptions tend to be:
        - Long sentences with no command words
        - Fragments of song lyrics
        - Incoherent phrases
        """
        if not transcript:
            return False

        text_lower = transcript.lower().strip()

        # If transcript contains any command word, it's likely real
        COMMAND_WORDS = [
            "play", "pause", "stop", "music", "song", "jarvis",
            "skip", "next", "volume", "quiet", "silence", "start",
            "hello", "hey", "please", "i want", "i am", "can you",
            "what", "how", "tell", "show", "help"
        ]

        has_command = any(word in text_lower for word in COMMAND_WORDS)
        if has_command:
            return False  # Likely a real command

        # If very long (>15 words) with no command words = likely lyrics
        word_count = len(text_lower.split())
        if word_count > 15 and not has_command:
            return True

        return False

    async def transcribe_audio_async(self, file_path: str) -> str:
        api_key = settings.DEEPGRAM_API_KEY
        if not api_key:
            return "Error: Deepgram API key not configured."

        try:
            url = "https://api.deepgram.com/v1/listen"

            # Enhanced parameters with heavy keyword boosting
            # to prioritize command words over background music lyrics
            params = {
                "model": "nova-2",
                "language": "en",
                "smart_format": "true",
                "punctuate": "true",
                "filler_words": "false",
                "profanity_filter": "false",
                "numerals": "true",
                "utterances": "false",
                "diarize": "false",
                "multichannel": "false",
                "detect_language": "false",
                # Keyword boosting — heavily boost command words so they
                # win over music lyrics in mixed audio
                "keywords": [
                    "pause:5",
                    "stop:5",
                    "play:5",
                    "music:4",
                    "song:4",
                    "JARVIS:5",
                    "skip:4",
                    "next:3",
                    "volume:3",
                    "quiet:4",
                    "silence:4"
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
                result = data

                # Check confidence — mixed audio gives low confidence scores
                try:
                    words = result["results"]["channels"][0]["alternatives"][0].get("words", [])
                    if words:
                        avg_confidence = sum(w.get("confidence", 1.0) for w in words) / len(words)
                        if avg_confidence < 0.55:
                            # Low confidence = likely picking up background music
                            logger.info(f"Rejecting transcript (low confidence: {avg_confidence:.2f})")
                            return ""
                except (KeyError, ZeroDivisionError):
                    pass  # If we can't check confidence, proceed normally

                transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]

                # Filter out likely music-bleed transcriptions
                if self._is_likely_music_bleed(transcript):
                    logger.info(f"Rejecting transcript (likely music bleed): {transcript[:50]}...")
                    return ""

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
