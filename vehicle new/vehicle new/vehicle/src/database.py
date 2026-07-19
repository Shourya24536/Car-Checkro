# Extensible Storage Layer for Inspection History
import os
import json
import threading
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .config import DATABASE_FILE

class BaseStorage(ABC):
    """
    Abstract Base Class for inspection data persistence.
    """
    @abstractmethod
    def save_inspection(self, payload: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass


class JSONFileStorage(BaseStorage):
    """
    JSON File-based storage implementation. Thread-safe using threading.Lock.
    """
    def __init__(self):
        self.filepath = DATABASE_FILE
        self.lock = threading.Lock()
        self._initialize_db()

    def _initialize_db(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump([], f)

    def save_inspection(self, payload: Dict[str, Any]) -> bool:
        with self.lock:
            try:
                history = []
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        history = json.load(f)
                
                # Append payload to history
                history.append(payload)
                
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=4)
                return True
            except Exception as e:
                print(f"[JSONFileStorage] Error saving inspection: {e}")
                return False

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.lock:
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        history = json.load(f)
                    # Return latest first
                    return list(reversed(history))[:limit]
            except Exception as e:
                print(f"[JSONFileStorage] Error reading history: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            try:
                if not os.path.exists(self.filepath):
                    return self._default_stats()
                
                with open(self.filepath, "r", encoding="utf-8") as f:
                    history = json.load(f)
                
                total = len(history)
                if total == 0:
                    return self._default_stats()
                
                passed = sum(1 for x in history if x.get("status") == "PASS")
                failed = total - passed
                pass_rate = (passed / total) * 100.0
                
                total_dents = sum(len(x.get("dents", [])) for x in history)
                total_scratches = sum(len(x.get("scratches", [])) for x in history)
                
                avg_latency = sum(float(x.get("processing_time", 0.0)) for x in history) / total
                
                return {
                    "total_inspections": total,
                    "passed": passed,
                    "failed": failed,
                    "pass_rate": round(pass_rate, 1),
                    "total_dents": total_dents,
                    "total_scratches": total_scratches,
                    "avg_processing_time": round(avg_latency, 2)
                }
            except Exception as e:
                print(f"[JSONFileStorage] Error getting stats: {e}")
            return self._default_stats()

    def _default_stats(self) -> Dict[str, Any]:
        return {
            "total_inspections": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "total_dents": 0,
            "total_scratches": 0,
            "avg_processing_time": 0.0
        }

    def clear(self) -> None:
        with self.lock:
            try:
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception as e:
                print(f"[JSONFileStorage] Error clearing storage: {e}")
