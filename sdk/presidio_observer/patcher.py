import time
import uuid
import logging
from .emitter import submit_event

logger = logging.getLogger(__name__)

def patch():
    _patch_analyzer()
    _patch_anonymizer()

def _patch_analyzer():
    try:
        from presidio_analyzer import AnalyzerEngine
        original_analyze = AnalyzerEngine.analyze
        
        def _patched_analyze(self, text, language, **kwargs):
            start_time = time.time()
            results = original_analyze(self, text=text, language=language, **kwargs)
            latency_ms = (time.time() - start_time) * 1000

            try:
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
                    entities_data.append({
                        "type": r.entity_type,
                        "score": score,
                        "recognizer": getattr(r, 'analysis_explanation', None) and r.analysis_explanation.recognizer or "unknown"
                    })

                event = {
                    "id": str(uuid.uuid4()),
                    "type": "analyze",
                    "latency_ms": latency_ms,
                    "language": language,
                    "entity_count": len(results),
                    "has_pii": has_pii,
                    "entities": entities_data,
                    "flag": flag,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                submit_event(event)
            except Exception as e:
                logger.debug(f"Observer analyzer patch error: {e}")
                pass
                
            return results
            
        AnalyzerEngine.analyze = _patched_analyze
        logger.debug("Patched presidio_analyzer.AnalyzerEngine.analyze")
    except ImportError:
        pass

def _patch_anonymizer():
    try:
        from presidio_anonymizer import AnonymizerEngine
        original_anonymize = AnonymizerEngine.anonymize
        
        def _patched_anonymize(self, text, analyzer_results, **kwargs):
            start_time = time.time()
            result = original_anonymize(self, text=text, analyzer_results=analyzer_results, **kwargs)
            latency_ms = (time.time() - start_time) * 1000

            try:
                operators_used = []
                for item in result.items:
                    operators_used.append(item.operator)

                event = {
                    "id": str(uuid.uuid4()),
                    "type": "anonymize",
                    "latency_ms": latency_ms,
                    "items_anonymized": len(result.items),
                    "operators_used": operators_used,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                submit_event(event)
            except Exception as e:
                logger.debug(f"Observer anonymizer patch error: {e}")
                pass
                
            return result
            
        AnonymizerEngine.anonymize = _patched_anonymize
        logger.debug("Patched presidio_anonymizer.AnonymizerEngine.anonymize")
    except ImportError:
        pass
