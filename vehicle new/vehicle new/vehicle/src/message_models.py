# Data models for edge client message payloads (Frozen / Immutable)
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass(frozen=True)
class ScratchDetail:
    id: str
    length_mm: float
    width_mm: float
    area_mm2: float
    angle: float
    confidence: float
    camera_id: str
    height: float  # Z-height (m)
    crop_filename: Optional[str] = None

@dataclass(frozen=True)
class DentDetail:
    id: str
    diameter_mm: float
    depth_mm: float
    area_mm2: float
    angle: float
    confidence: float
    camera_id: str
    height: float  # Z-height (m)
    severity: str
    crop_filename: Optional[str] = None

@dataclass(frozen=True)
class InspectionMessage:
    request_id: str
    inspection_id: str
    timestamp: str
    version: str
    status: str  # PASS / FAIL
    confidence: float
    processing_time: float
    scratches: List[ScratchDetail] = field(default_factory=list)
    dents: List[DentDetail] = field(default_factory=list)
    camera_1_frame: Optional[str] = None  # Saved local filename
    camera_2_frame: Optional[str] = None  # Saved local filename
