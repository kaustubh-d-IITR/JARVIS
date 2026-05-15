SYSTEM_PROMPT = """You are JARVIS, an emotion-aware AI assistant.

STRICT RULES — follow these exactly:
1. Maximum 2 sentences. Never more.
2. NEVER ask the user a question. Ever.
3. NEVER say a song is playing unless [SYSTEM ACTION RESULT] confirms it.
4. When [SYSTEM ACTION RESULT] shows what played, mention the actual 
   song/artist name from the result. Do not invent song names.
5. When music is paused, confirm it simply: "Music paused."
6. Be warm and brief. Reference emotion or weather only if natural.
7. If no action was taken, just respond conversationally in 1-2 sentences."""


def build_contextual_prompt(user_text: str, emotion: str, posture: str, weather: dict, action_taken: str = None) -> str:
    """
    Injects live context into the user's prompt.
    If an action was already taken by the system, includes the actual result
    so the LLM can reference real song/artist names instead of hallucinating.
    """
    context_parts = [f"emotion={emotion}", f"posture={posture}"]

    if weather:
        temp = weather.get('temperature', 'unknown')
        condition = weather.get('condition', 'unknown')
        context_parts.append(f"weather={condition} {temp}°C")

    context = "[CONTEXT: " + ", ".join(context_parts) + "]"

    if action_taken:
        action_line = f"[SYSTEM ACTION RESULT: {action_taken}]"
        return f"{context}\n{action_line}\nUser said: {user_text}"
    else:
        return f"{context}\nUser said: {user_text}"
