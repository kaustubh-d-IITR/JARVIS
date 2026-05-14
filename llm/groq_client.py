from groq import Groq
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class GroqClient:
    def __init__(self):
        pass
            
    def get_response(self, system_prompt: str, user_prompt: str) -> str:
        api_key = settings.GROQ_API_KEY
        if not api_key:
            return "I'm sorry, my Groq API key is not configured."
            
        try:
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=150,
                top_p=1,
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
