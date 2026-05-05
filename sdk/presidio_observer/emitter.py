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
_worker_lock = threading.Lock()
_metrics_lock = threading.Lock()
_metrics = {
    "dropped_events": 0,
    "failed_flushes": 0,
    "sent_events": 0,
}

def init_emitter(endpoint: str = "http://localhost:8000"):
    global _endpoint, _worker_thread
    _endpoint = endpoint
    with _worker_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
            _worker_thread.start()

def submit_event(event: dict):
    try:
        _queue.put_nowait(event)
    except queue.Full:
        _increment_metric("dropped_events")

def emitter_metrics():
    with _metrics_lock:
        return dict(_metrics)

def _worker_loop():
    batch = []
    last_flush = time.monotonic()
    
    while True:
        try:
            # Wait for event with a timeout to allow periodic flushing
            try:
                timeout = max(0.1, _flush_interval_seconds - (time.monotonic() - last_flush))
                event = _queue.get(timeout=timeout)
                batch.append(event)
                _queue.task_done()
            except queue.Empty:
                pass

            # Flush conditions
            if len(batch) >= _batch_size or (time.monotonic() - last_flush) >= _flush_interval_seconds:
                if batch:
                    if _flush(batch):
                        _increment_metric("sent_events", len(batch))
                    else:
                        _increment_metric("failed_flushes")
                    batch = []
                last_flush = time.monotonic()
        except Exception as e:
            # We never want the background thread to crash the main app
            logger.debug(f"Observer emitter loop error: {e}")
            pass

def _flush(batch: list):
    try:
        response = requests.post(f"{_endpoint}/ingest", json={"events": batch}, timeout=2.0)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.debug(f"Observer flush failed: {e}")
        return False

def _increment_metric(name: str, value: int = 1):
    with _metrics_lock:
        _metrics[name] += value
