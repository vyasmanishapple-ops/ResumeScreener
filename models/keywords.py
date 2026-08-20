from typing import Literal
from pydantic import BaseModel

SignalType = Literal["POSITIVE","NEGATIVE","REQUIRED","DISQUALIFYING"]

class KeywordSignal(BaseModel):
    keyword: str
    signal_type: SignalType
    weight: float = 0
    enabled: bool = True
    description: str = ""

class KeywordDetection(BaseModel):
    keyword: str
    signal_type: SignalType
    configured_weight: float
    detected: bool
    context: str = ""
    relevant: bool = False
    applied_adjustment: float = 0
