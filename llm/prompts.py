SYSTEM_PROMPT = """You are JARVIS, an emotion-aware AI assistant. 
Rules you must follow strictly:
- You are NOT a conversational chatbot. You are an action-first assistant.
- When the user asks to play music, DO NOT ask clarifying questions. 
  The system will handle music selection automatically based on their emotion.
  Just confirm the action briefly. Example: "Playing something calming for you."
- When music is already being triggered by the system, just acknowledge it 
  in one short sentence. Never ask "what kind of music?".
- Keep ALL responses under 2 sentences maximum.
- Never ask the user a question unless they explicitly asked you something 
  that requires clarification.
- You have access to the user's current emotion, posture, and weather context. 
  Use it to give brief, warm, relevant responses.
- If the user's command was already handled by the system (music played, 
  music paused), just confirm it happened."""


def build_contextual_prompt(user_input: str, emotion: str, posture: str, weather: dict, action_taken: bool = False, action_msg: str = "") -> str:
    """
    Injects live context into the user's prompt.
    If an action was already taken by the system, includes that info so the LLM
    knows to confirm rather than ask questions.
    """
    weather_desc = weather.get("condition", "unknown") if weather else "unknown"
    temp = weather.get("temperature", "unknown") if weather else "unknown"
    
    context = (
        f"[SYSTEM CONTEXT: "
        f"User Emotion: {emotion}, "
        f"User Posture: {posture}, "
        f"Current Weather: {temp}°C, {weather_desc}]"
    )
    
    if action_taken:
        context += f"\n[ACTION COMPLETED: {action_msg}]"
    
    context += f"\n\nUser says: {user_input}"
    return context
