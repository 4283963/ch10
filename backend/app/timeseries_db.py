import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List
from .models import FermenterDataPoint


class TimeSeriesDBSimulator:
    FERMENTER_CONFIGS = [
        {"id": "F01", "name": "发酵罐 1号", "target_temp": 37.0},
        {"id": "F02", "name": "发酵罐 2号", "target_temp": 36.5},
        {"id": "F03", "name": "发酵罐 3号", "target_temp": 37.0},
        {"id": "F04", "name": "发酵罐 4号", "target_temp": 37.5},
        {"id": "F05", "name": "发酵罐 5号", "target_temp": 36.5},
        {"id": "F06", "name": "发酵罐 6号", "target_temp": 37.0},
        {"id": "F07", "name": "发酵罐 7号", "target_temp": 37.0},
        {"id": "F08", "name": "发酵罐 8号", "target_temp": 36.5},
        {"id": "F09", "name": "发酵罐 9号", "target_temp": 37.5},
        {"id": "F10", "name": "发酵罐 10号", "target_temp": 37.0},
        {"id": "F11", "name": "发酵罐 11号", "target_temp": 37.0},
        {"id": "F12", "name": "发酵罐 12号", "target_temp": 36.5},
    ]

    def __init__(self):
        self._data: Dict[str, List[FermenterDataPoint]] = {}
        self._valve_state: Dict[str, float] = {}
        self._reaction_intensity: Dict[str, float] = {}
        self._initialize()

    def _initialize(self):
        now = datetime.now()
        for cfg in self.FERMENTER_CONFIGS:
            fid = cfg["id"]
            target = cfg["target_temp"]
            self._valve_state[fid] = random.uniform(40.0, 70.0)
            self._reaction_intensity[fid] = random.uniform(0.6, 1.4)
            self._data[fid] = []

            current_temp = target
            for i in range(720):
                ts = now - timedelta(minutes=(719 - i))
                intensity = self._reaction_intensity[fid] + random.uniform(-0.1, 0.1)
                valve = self._valve_state[fid] + random.uniform(-3, 3)
                heat_generated = intensity * 0.08
                cooling_effect = valve * 0.0012
                delta = heat_generated - cooling_effect
                current_temp = current_temp + delta + random.uniform(-0.05, 0.05)
                current_temp = max(30.0, min(45.0, current_temp))
                pressure = 0.35 + random.uniform(-0.03, 0.03) + (valve / 100) * 0.1
                self._data[fid].append(FermenterDataPoint(
                    timestamp=ts,
                    temperature=round(current_temp, 3),
                    inlet_pressure=round(pressure, 4),
                    valve_opening=round(valve, 2),
                ))

    async def start_simulation(self):
        while True:
            self._advance_one_minute()
            await asyncio.sleep(2)

    def _advance_one_minute(self):
        now = datetime.now()
        for cfg in self.FERMENTER_CONFIGS:
            fid = cfg["id"]
            target = cfg["target_temp"]
            history = self._data[fid]

            self._reaction_intensity[fid] += random.uniform(-0.02, 0.02)
            self._reaction_intensity[fid] = max(0.3, min(2.0, self._reaction_intensity[fid]))

            last_temp = history[-1].temperature
            last_valve = self._valve_state[fid]

            temp_diff = last_temp - target
            if abs(temp_diff) > 0.3:
                adjustment = -temp_diff * 15.0
                self._valve_state[fid] += adjustment + random.uniform(-2, 2)
            self._valve_state[fid] = max(10.0, min(95.0, self._valve_state[fid]))

            intensity = self._reaction_intensity[fid]
            valve = self._valve_state[fid]
            heat_generated = intensity * 0.08
            cooling_effect = valve * 0.0012
            delta = heat_generated - cooling_effect
            new_temp = last_temp + delta + random.uniform(-0.04, 0.04)
            new_temp = max(30.0, min(45.0, new_temp))
            pressure = 0.35 + random.uniform(-0.03, 0.03) + (valve / 100) * 0.1

            history.append(FermenterDataPoint(
                timestamp=now,
                temperature=round(new_temp, 3),
                inlet_pressure=round(pressure, 4),
                valve_opening=round(valve, 2),
            ))
            if len(history) > 720:
                history.pop(0)

    def get_fermenter_ids(self) -> List[str]:
        return [cfg["id"] for cfg in self.FERMENTER_CONFIGS]

    def get_fermenter_config(self, fid: str) -> dict:
        for cfg in self.FERMENTER_CONFIGS:
            if cfg["id"] == fid:
                return cfg
        return {}

    def get_history(self, fid: str, hours: float = 12.0) -> List[FermenterDataPoint]:
        points = int(hours * 60)
        return self._data.get(fid, [])[-points:]

    def get_current_valve(self, fid: str) -> float:
        return self._valve_state.get(fid, 50.0)
