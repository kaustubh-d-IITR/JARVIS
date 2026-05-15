SYSTEM_PROMPT = """You are JARVIS, an emotion-aware AI assistant.
STRICT RULES:
- Maximum 2 sentences per response. Never more.
- NEVER ask the user questions. Never.
- When music is playing or was just triggered, just confirm it briefly.
- Be warm, calm, and direct.
- You know the user's emotion, posture, and weather. Use that context.
- If an action was completed, acknowledge it. Do not re-explain it."""


def build_contextual_prompt(user_text: str, emotion: str, posture: str, weather: dict, action_taken: str = None) -> str:
    """
    Injects live context into the user's prompt.
    If an action was already taken by the system, includes that info so the LLM
    knows to confirm rather than ask questions.
    """
    context = f"[CONTEXT: emotion={emotion}, posture={posture}"
    if weather:
        temp = weather.get('temperature', 'unknown')
        condition = weather.get('condition', 'unknown')
        context += f", weather={condition} {temp}°C"
    if action_taken:
        context += f", ACTION COMPLETED={action_taken}"
    context += "]"
    return f"{context}\nUser said: {user_text}"
