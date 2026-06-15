import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple
from .models import FermenterDataPoint, PredictionPoint, ValveAdjustment


class TemperaturePredictor:
    PREDICTION_MINUTES = 15
    DERIVATIVE_WINDOW = 10
    SMOOTHING_WINDOW = 5

    def __init__(self):
        pass

    def compute_sliding_derivative(self, temperatures: np.ndarray) -> np.ndarray:
        series = pd.Series(temperatures)
        smoothed = series.rolling(window=self.SMOOTHING_WINDOW, center=True).mean()
        derivative = smoothed.rolling(window=self.DERIVATIVE_WINDOW).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0],
            raw=True
        )
        return derivative.values

    def predict_temperature(
        self,
        history: List[FermenterDataPoint],
        target_temp: float
    ) -> Tuple[List[PredictionPoint], ValveAdjustment]:
        temps = np.array([dp.temperature for dp in history])
        timestamps = [dp.timestamp for dp in history]
        current_valve = history[-1].valve_opening
        current_temp = temps[-1]

        derivatives = self.compute_sliding_derivative(temps)
        valid_derivatives = derivatives[~np.isnan(derivatives)]
        if len(valid_derivatives) == 0:
            avg_derivative = 0.0
        else:
            recent = valid_derivatives[-min(15, len(valid_derivatives)):]
            avg_derivative = float(np.mean(recent))

        second_derivatives = np.diff(valid_derivatives)
        if len(second_derivatives) == 0:
            accel = 0.0
        else:
            accel = float(np.mean(second_derivatives[-min(10, len(second_derivatives)):]))

        last_ts = timestamps[-1]
        predictions: List[PredictionPoint] = []
        pred_temp = current_temp
        for i in range(1, self.PREDICTION_MINUTES + 1):
            pred_ts = last_ts + timedelta(minutes=i)
            pred_temp = current_temp + avg_derivative * i + 0.5 * accel * i * i
            pred_temp = round(max(30.0, min(45.0, pred_temp)), 3)
            predictions.append(PredictionPoint(timestamp=pred_ts, temperature=pred_temp))

        future_temp = pred_temp
        temp_diff = current_temp - target_temp
        future_diff = future_temp - target_temp

        if abs(future_diff) <= 0.15:
            urgency = "stable"
            suggested = current_valve
            reason = "温度稳定，维持当前阀门开度"
        elif future_diff > 0.15:
            urgency = "high" if future_diff > 0.5 else "medium"
            suggested = min(95.0, current_valve + future_diff * 18.0 + abs(avg_derivative) * 50)
            reason = f"温度偏高{future_diff:+.2f}°C，预测将继续上升，需加大冷却水流量"
        else:
            urgency = "high" if future_diff < -0.5 else "medium"
            suggested = max(10.0, current_valve - abs(future_diff) * 18.0 - abs(avg_derivative) * 50)
            reason = f"温度偏低{future_diff:+.2f}°C，预测将继续下降，需减小冷却水流量"

        suggested = round(suggested, 2)
        adjustment = round(suggested - current_valve, 2)

        valve_adj = ValveAdjustment(
            suggested_opening=suggested,
            current_opening=round(current_valve, 2),
            adjustment_pct=adjustment,
            urgency=urgency,
            reason=reason
        )

        return predictions, valve_adj

    def analyze_stability(self, history: List[FermenterDataPoint], target_temp: float) -> dict:
        temps = np.array([dp.temperature for dp in history])
        deviations = temps - target_temp
        derivatives = self.compute_sliding_derivative(temps)
        valid_deriv = derivatives[~np.isnan(derivatives)]

        return {
            "std_dev": round(float(np.std(deviations)), 4),
            "max_deviation": round(float(np.max(np.abs(deviations))), 4),
            "mean_derivative": round(float(np.mean(valid_deriv)) if len(valid_deriv) > 0 else 0.0, 6),
            "stability_score": round(max(0.0, 100.0 - float(np.std(deviations)) * 80
                                         - abs(float(np.mean(valid_deriv)) if len(valid_deriv) > 0 else 0.0) * 200), 1),
        }
