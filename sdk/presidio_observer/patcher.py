import time
import uuid
import logging
from functools import wraps
from .emitter import submit_event

logger = logging.getLogger(__name__)
_PATCHED_ATTR = "_presidio_observer_patched"

def patch():
    _patch_analyzer()

def _arg_or_kwarg(args, kwargs, position, name, default=None):
    if name in kwargs:
        return kwargs[name]
    if len(args) > position:
        return args[position]
    return default

def _safe_class_name(value):
    if value is None:
        return None
    return value.__class__.__name__

def _allow_list_count(allow_list):
    if not allow_list:
        return 0
    try:
        return len(allow_list)
    except TypeError:
        return None

def _analysis_explanation_metadata(result):
    explanation = getattr(result, "analysis_explanation", None)
    if explanation is None:
        return {
            "recognizer": "unknown",
            "pattern_name": None,
            "original_score": None,
            "score_context_improvement": None,
            "validation_result": None,
        }

    validation_result = getattr(explanation, "validation_result", None)
    if validation_result is not None:
        validation_result = str(validation_result)

    return {
        "recognizer": getattr(explanation, "recognizer", None) or "unknown",
        "pattern_name": getattr(explanation, "pattern_name", None),
        "original_score": getattr(explanation, "original_score", None),
        "score_context_improvement": getattr(explanation, "score_context_improvement", None),
        "validation_result": validation_result,
    }

def _patch_analyzer():
    try:
        from presidio_analyzer import AnalyzerEngine
        if getattr(AnalyzerEngine.analyze, _PATCHED_ATTR, False):
            return

        original_analyze = AnalyzerEngine.analyze

        @wraps(original_analyze)
        def _patched_analyze(self, *args, **kwargs):
            start_time = time.time()
            results = original_analyze(self, *args, **kwargs)
            latency_ms = (time.time() - start_time) * 1000

            try:
                language = _arg_or_kwarg(args, kwargs, 1, "language")
                requested_entities = _arg_or_kwarg(args, kwargs, 2, "entities", [])
                score_threshold = _arg_or_kwarg(args, kwargs, 3, "score_threshold")
                allow_list = _arg_or_kwarg(args, kwargs, 7, "allow_list")
                correlation_id = kwargs.get("correlation_id") or str(uuid.uuid4())

                # Calculate scores and entity info
                entities_data = []
                has_pii = False
                
                # We need to compute flag:
                # confident: no entities or all >= 0.6
                # uncertain: any entity < 0.6
                flag = "confident"

                for r in results:
                    has_pii = True
                    score = float(r.score)
                    if score < 0.6:
                        flag = "uncertain"
                    explanation_metadata = _analysis_explanation_metadata(r)
                    start = getattr(r, "start", None)
                    end = getattr(r, "end", None)
                    entities_data.append({
                        "type": r.entity_type,
                        "score": score,
                        "start": start,
                        "end": end,
                        "span_length": end - start if start is not None and end is not None else None,
                        **explanation_metadata,
                    })

                event = {
                    "id": str(uuid.uuid4()),
                    "correlation_id": correlation_id,
                    "type": "analyze",
                    "latency_ms": latency_ms,
                    "language": language,
                    "requested_entities": requested_entities or [],
                    "score_threshold": score_threshold,
                    "allow_list_count": _allow_list_count(allow_list),
                    "entity_count": len(results),
                    "has_pii": has_pii,
                    "entities": entities_data,
                    "flag": flag,
                    "nlp_engine": _safe_class_name(getattr(self, "nlp_engine", None)),
                    "context_enhancer": _safe_class_name(getattr(self, "context_aware_enhancer", None)),
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                submit_event(event)
            except Exception as e:
                logger.debug(f"Observer analyzer patch error: {e}")
                pass
                
            return results
            
        setattr(_patched_analyze, _PATCHED_ATTR, True)
        AnalyzerEngine.analyze = _patched_analyze
        logger.debug("Patched presidio_analyzer.AnalyzerEngine.analyze")
    except ImportError:
        pass
