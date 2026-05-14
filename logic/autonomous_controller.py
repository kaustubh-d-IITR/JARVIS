import threading
import time
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class AutonomousController:
    """
    Runs in a background thread to periodically evaluate user state 
    and push suggestions to Streamlit session state.
    """
    def __init__(self, decision_engine):
        self.decision_engine = decision_engine
        self.is_running = False
        self.cooldown = settings.AUTONOMOUS_COOLDOWN_SECONDS
        self.last_action_time = 0
        
        # Thread-safe state for the Streamlit UI to poll
        self.latest_suggestion = None
        
        # Internal state
        self.current_emotion = "neutral"
        self.current_confidence = 0.0
        self.current_posture = "unknown"
        self.current_weather = {}
        
        self.lock = threading.Lock()
        
    def update_state(self, emotion, confidence, posture, weather):
        with self.lock:
            self.current_emotion = emotion
            self.current_confidence = confidence
            self.current_posture = posture
            self.current_weather = weather
            
    def start(self):
        """Starts the background loop."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        
    def _loop(self):
        logger.info("Autonomous controller background loop started.")
        while self.is_running:
            time.sleep(5) # Poll state every 5 seconds
            
            now = time.time()
            if now - self.last_action_time < self.cooldown:
                continue # In cooldown
                
            with self.lock:
                emotion = self.current_emotion
                confidence = self.current_confidence
                posture = self.current_posture
                weather = self.current_weather
            
            # Use decision engine to see if an action should be suggested
            decision = self.decision_engine.evaluate_autonomous_state(emotion, confidence, posture, weather)
            
            if decision and decision.get("suggested_action"):
                with self.lock:
                    self.latest_suggestion = decision
                # Reset cooldown only when a suggestion is made
                self.last_action_time = now
                
    def get_and_clear_suggestion(self):
        """Called by UI to check if there's a pending suggestion."""
        with self.lock:
            suggestion = self.latest_suggestion
            self.latest_suggestion = None
            return suggestion
            
    def stop(self):
        self.is_running = False
