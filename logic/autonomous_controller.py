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
        self.lock = threading.Lock()
        
    def start(self, get_current_state_cb):
        """
        Starts the background loop. 
        get_current_state_cb should return (emotion, confidence, posture, weather)
        """
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._loop, args=(get_current_state_cb,), daemon=True)
        self.thread.start()
        
    def _loop(self, get_current_state_cb):
        logger.info("Autonomous controller background loop started.")
        while self.is_running:
            time.sleep(5) # Poll state every 5 seconds
            
            now = time.time()
            if now - self.last_action_time < self.cooldown:
                continue # In cooldown
                
            emotion, confidence, posture, weather = get_current_state_cb()
            
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
