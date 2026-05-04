import queue
import threading
import time
import requests
import logging

logger = logging.getLogger(__name__)

_queue = queue.Queue(maxsize=1000)
_endpoint = "http://localhost:8000"
_batch_size = 50
_flush_interval_seconds = 2.0
_worker_thread = None

def init_emitter(endpoint: str = "http://localhost:8000"):
    global _endpoint, _worker_thread
    _endpoint = endpoint
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
        _worker_thread.start()

def submit_event(event: dict):
    try:
        _queue.put_nowait(event)
    except queue.Full:
        pass  # Drop event silently

def _worker_loop():
    batch = []
    last_flush = time.time()
    
    while True:
        try:
            # Wait for event with a timeout to allow periodic flushing
            try:
                timeout = max(0.1, _flush_interval_seconds - (time.time() - last_flush))
                event = _queue.get(timeout=timeout)
                batch.append(event)
                _queue.task_done()
            except queue.Empty:
                pass

            # Flush conditions
            if len(batch) >= _batch_size or (time.time() - last_flush) >= _flush_interval_seconds:
                if batch:
                    _flush(batch)
                    batch = []
                last_flush = time.time()
        except Exception as e:
            # We never want the background thread to crash the main app
            logger.debug(f"Observer emitter loop error: {e}")
            pass

def _flush(batch: list):
    try:
        requests.post(f"{_endpoint}/ingest", json={"events": batch}, timeout=2.0)
    except Exception as e:
        logger.debug(f"Observer flush failed: {e}")
        pass
