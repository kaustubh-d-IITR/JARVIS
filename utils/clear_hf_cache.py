import shutil
import os
import pathlib
from utils.logger import get_logger

logger = get_logger(__name__)

def purge_hf_auth_cache():
    """
    Forcefully deletes local HuggingFace cache and auth folders 
    to prevent the SDK from using old/expired tokens.
    """
    home = pathlib.Path.home()
    targets = [
        home / ".cache" / "huggingface",
        home / ".huggingface"
    ]
    
    purged_count = 0
    for target in targets:
        if target.exists():
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    os.remove(target)
                logger.info(f"[HF CACHE] Purged: {target}")
                purged_count += 1
            except Exception as e:
                logger.warning(f"[HF CACHE] Failed to purge {target}: {e}")
    
    if purged_count == 0:
        logger.info("[HF CACHE] No local HF cache folders found. State is clean.")
    return purged_count

if __name__ == "__main__":
    purge_hf_auth_cache()
