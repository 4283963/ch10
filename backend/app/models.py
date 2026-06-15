from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class FermenterDataPoint(BaseModel):
    timestamp: datetime
    temperature: float
    inlet_pressure: float
    valve_opening: float


class FermenterInfo(BaseModel):
    id: str
    name: str
    target_temp: float
    current_temp: float
    current_pressure: float
    current_valve: float


class PredictionPoint(BaseModel):
    timestamp: datetime
    temperature: float


class ValveAdjustment(BaseModel):
    suggested_opening: float
    current_opening: float
    adjustment_pct: float
    urgency: str
    reason: str


class GradualAdjustmentStep(BaseModel):
    minute: int
    valve_opening: float
    increment: float
    note: str


class RedlineAlert(BaseModel):
    triggered: bool
    redline_temp: float
    breach_minutes: Optional[int] = None
    current_slope: float = 0.0
    slope_steepening: bool = False
    gradual_steps: List[GradualAdjustmentStep] = []
    overshoot_margin: float = 0.0


class FermenterStatus(BaseModel):
    info: FermenterInfo
    history: List[FermenterDataPoint]
    prediction: List[PredictionPoint]
    valve_adjustment: Optional[ValveAdjustment] = None
    redline_alert: Optional[RedlineAlert] = None
