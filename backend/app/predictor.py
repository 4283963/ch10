import numpy as np
import pandas as pd
import warnings
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

from .models import FermenterDataPoint, PredictionPoint, ValveAdjustment, GradualAdjustmentStep, RedlineAlert


np.seterr(all='warn')
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=FutureWarning)


class TemperaturePredictor:
    PREDICTION_MINUTES = 15
    DERIVATIVE_WINDOW = 10
    SMOOTHING_WINDOW = 5
    MIN_VALID_POINTS = 3
    EPS = 1e-10

    def __init__(self):
        pass

    def _safe_clean(self, arr: np.ndarray) -> np.ndarray:
        arr = np.asarray(arr, dtype=np.float64)
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        return arr

    def _is_finite(self, val) -> bool:
        try:
            f = float(val)
            return np.isfinite(f)
        except (TypeError, ValueError):
            return False

    def _robust_slope(self, y: np.ndarray) -> float:
        y = np.asarray(y, dtype=np.float64)
        y = self._safe_clean(y)
        n = len(y)
        if n < self.MIN_VALID_POINTS:
            return 0.0

        x = np.arange(n, dtype=np.float64)
        y_mean = np.mean(y)
        x_mean = np.mean(x)

        if y_mean == 0 and np.all(y == 0):
            return 0.0

        sxx = np.sum((x - x_mean) ** 2)
        sxy = np.sum((x - x_mean) * (y - y_mean))

        denom = sxx + self.EPS
        slope = sxy / denom

        if not self._is_finite(slope):
            return 0.0

        if abs(slope) > 100.0:
            return 0.0

        return float(slope)

    def compute_sliding_derivative(self, temperatures: np.ndarray) -> np.ndarray:
        try:
            temps = np.asarray(temperatures, dtype=np.float64)
            temps = self._safe_clean(temps)

            if len(temps) < self.MIN_VALID_POINTS:
                return np.zeros_like(temps, dtype=np.float64)

            series = pd.Series(temps)
            smoothed = series.rolling(
                window=self.SMOOTHING_WINDOW,
                min_periods=self.MIN_VALID_POINTS,
                center=True
            ).mean().values

            smoothed = self._safe_clean(smoothed)

            n = len(smoothed)
            derivatives = np.zeros(n, dtype=np.float64)
            half_win = self.DERIVATIVE_WINDOW // 2

            for i in range(n):
                start = max(0, i - half_win)
                end = min(n, i + half_win + 1)
                window_y = smoothed[start:end]
                derivatives[i] = self._robust_slope(window_y)

            derivatives = self._safe_clean(derivatives)
            return derivatives

        except Exception as e:
            print(f"[WARN] compute_sliding_derivative failed: {e}")
            return np.zeros_like(temperatures, dtype=np.float64)

    def _safe_mean(self, arr: np.ndarray) -> float:
        try:
            arr = np.asarray(arr, dtype=np.float64)
            valid = arr[np.isfinite(arr)]
            if len(valid) == 0:
                return 0.0
            m = float(np.mean(valid))
            return m if self._is_finite(m) else 0.0
        except Exception:
            return 0.0

    def _safe_std(self, arr: np.ndarray) -> float:
        try:
            arr = np.asarray(arr, dtype=np.float64)
            valid = arr[np.isfinite(arr)]
            if len(valid) == 0:
                return 0.0
            s = float(np.std(valid))
            return s if self._is_finite(s) else 0.0
        except Exception:
            return 0.0

    def _safe_max_abs(self, arr: np.ndarray) -> float:
        try:
            arr = np.asarray(arr, dtype=np.float64)
            valid = arr[np.isfinite(arr)]
            if len(valid) == 0:
                return 0.0
            m = float(np.max(np.abs(valid)))
            return m if self._is_finite(m) else 0.0
        except Exception:
            return 0.0

    def predict_temperature(
        self,
        history: List[FermenterDataPoint],
        target_temp: float
    ) -> Tuple[List[PredictionPoint], ValveAdjustment]:
        try:
            if not history:
                return self._fallback_prediction(target_temp, 50.0)

            temps = np.array([dp.temperature for dp in history], dtype=np.float64)
            timestamps = [dp.timestamp for dp in history]
            current_valve = float(history[-1].valve_opening)
            current_temp = float(temps[-1])

            if not self._is_finite(current_temp) or not self._is_finite(current_valve):
                return self._fallback_prediction(target_temp, 50.0)

            derivatives = self.compute_sliding_derivative(temps)
            valid_derivatives = derivatives[np.isfinite(derivatives)]

            if len(valid_derivatives) == 0:
                avg_derivative = 0.0
                accel = 0.0
            else:
                recent_n = min(15, len(valid_derivatives))
                recent = valid_derivatives[-recent_n:]
                avg_derivative = self._safe_mean(recent)

                if len(recent) >= 2:
                    second_derivs = np.diff(recent)
                    accel = self._safe_mean(second_derivs[-min(10, len(second_derivs)):])
                else:
                    accel = 0.0

            if not self._is_finite(avg_derivative):
                avg_derivative = 0.0
            if not self._is_finite(accel):
                accel = 0.0

            avg_derivative = max(-5.0, min(5.0, avg_derivative))
            accel = max(-1.0, min(1.0, accel))

            last_ts = timestamps[-1]
            predictions: List[PredictionPoint] = []
            pred_temp = current_temp
            for i in range(1, self.PREDICTION_MINUTES + 1):
                pred_ts = last_ts + timedelta(minutes=i)
                pred_temp = current_temp + avg_derivative * i + 0.5 * accel * i * i
                pred_temp = float(max(0.0, min(100.0, pred_temp)))
                if not self._is_finite(pred_temp):
                    pred_temp = current_temp
                predictions.append(PredictionPoint(
                    timestamp=pred_ts,
                    temperature=round(pred_temp, 3)
                ))

            future_temp = pred_temp
            temp_diff = current_temp - target_temp
            future_diff = future_temp - target_temp

            if not self._is_finite(future_diff):
                future_diff = temp_diff

            if abs(future_diff) <= 0.15:
                urgency = "stable"
                suggested = current_valve
                reason = "温度稳定，维持当前阀门开度"
            elif future_diff > 0.15:
                urgency = "high" if future_diff > 0.5 else "medium"
                adjust_amount = future_diff * 18.0 + abs(avg_derivative) * 50
                if not self._is_finite(adjust_amount):
                    adjust_amount = future_diff * 10.0
                suggested = min(95.0, current_valve + adjust_amount)
                reason = f"温度偏高{future_diff:+.2f}°C，预测将继续上升，需加大冷却水流量"
            else:
                urgency = "high" if future_diff < -0.5 else "medium"
                adjust_amount = abs(future_diff) * 18.0 + abs(avg_derivative) * 50
                if not self._is_finite(adjust_amount):
                    adjust_amount = abs(future_diff) * 10.0
                suggested = max(10.0, current_valve - adjust_amount)
                reason = f"温度偏低{future_diff:+.2f}°C，预测将继续下降，需减小冷却水流量"

            suggested = float(max(0.0, min(100.0, suggested)))
            if not self._is_finite(suggested):
                suggested = current_valve

            adjustment = round(suggested - current_valve, 2)
            if not self._is_finite(adjustment):
                adjustment = 0.0

            valve_adj = ValveAdjustment(
                suggested_opening=round(suggested, 2),
                current_opening=round(current_valve, 2),
                adjustment_pct=adjustment,
                urgency=urgency,
                reason=reason
            )

            return predictions, valve_adj

        except Exception as e:
            print(f"[ERROR] predict_temperature failed: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_prediction(target_temp, 50.0)

    def _fallback_prediction(
        self, target_temp: float, current_valve: float
    ) -> Tuple[List[PredictionPoint], ValveAdjustment]:
        now = datetime.now()
        predictions = []
        for i in range(1, self.PREDICTION_MINUTES + 1):
            predictions.append(PredictionPoint(
                timestamp=now + timedelta(minutes=i),
                temperature=round(target_temp, 3)
            ))
        valve_adj = ValveAdjustment(
            suggested_opening=round(current_valve, 2),
            current_opening=round(current_valve, 2),
            adjustment_pct=0.0,
            urgency="stable",
            reason="数据质量异常，算法切换至安全模式"
        )
        return predictions, valve_adj

    def analyze_stability(self, history: List[FermenterDataPoint], target_temp: float) -> dict:
        try:
            if not history:
                return {
                    "std_dev": 0.0,
                    "max_deviation": 0.0,
                    "mean_derivative": 0.0,
                    "stability_score": 50.0,
                }

            temps = np.array([dp.temperature for dp in history], dtype=np.float64)
            temps = self._safe_clean(temps)

            deviations = temps - target_temp
            deviations = self._safe_clean(deviations)

            derivatives = self.compute_sliding_derivative(temps)
            valid_deriv = derivatives[np.isfinite(derivatives)]

            std_dev = self._safe_std(deviations)
            max_dev = self._safe_max_abs(deviations)
            mean_deriv = self._safe_mean(valid_deriv) if len(valid_deriv) > 0 else 0.0

            if not self._is_finite(std_dev):
                std_dev = 0.0
            if not self._is_finite(max_dev):
                max_dev = 0.0
            if not self._is_finite(mean_deriv):
                mean_deriv = 0.0

            score = 100.0 - std_dev * 80.0 - abs(mean_deriv) * 200.0
            score = max(0.0, min(100.0, score))
            if not self._is_finite(score):
                score = 50.0

            return {
                "std_dev": round(std_dev, 4),
                "max_deviation": round(max_dev, 4),
                "mean_derivative": round(mean_deriv, 6),
                "stability_score": round(score, 1),
            }
        except Exception as e:
            print(f"[ERROR] analyze_stability failed: {e}")
            return {
                "std_dev": 0.0,
                "max_deviation": 0.0,
                "mean_derivative": 0.0,
                "stability_score": 50.0,
            }

    def compute_redline_alert(
        self,
        history: List[FermenterDataPoint],
        prediction: List[PredictionPoint],
        redline_temp: float = 37.5
    ) -> RedlineAlert:
        try:
            if not history or not prediction:
                return RedlineAlert(
                    triggered=False,
                    redline_temp=redline_temp,
                    current_slope=0.0,
                    slope_steepening=False,
                    gradual_steps=[],
                    overshoot_margin=0.0,
                )

            current_temp = float(history[-1].temperature)
            current_valve = float(history[-1].valve_opening)

            if not self._is_finite(current_temp) or not self._is_finite(current_valve):
                return RedlineAlert(triggered=False, redline_temp=redline_temp)

            breach_minute = None
            for p in prediction[:5]:
                if self._is_finite(p.temperature) and p.temperature >= redline_temp:
                    idx = prediction.index(p) + 1
                    breach_minute = idx
                    break

            if breach_minute is None and current_temp < redline_temp:
                return RedlineAlert(
                    triggered=False,
                    redline_temp=redline_temp,
                    current_slope=0.0,
                    slope_steepening=False,
                    gradual_steps=[],
                    overshoot_margin=0.0,
                )

            temps = np.array([dp.temperature for dp in history], dtype=np.float64)
            derivatives = self.compute_sliding_derivative(temps)
            valid_deriv = derivatives[np.isfinite(derivatives)]

            current_slope = 0.0
            slope_steepening = False

            if len(valid_deriv) >= 3:
                recent_slope = float(valid_deriv[-1])
                if self._is_finite(recent_slope):
                    current_slope = max(-5.0, min(5.0, recent_slope))

                recent_3 = valid_deriv[-3:]
                if len(recent_3) >= 3:
                    d1, d2, d3 = float(recent_3[0]), float(recent_3[1]), float(recent_3[2])
                    if self._is_finite(d1) and self._is_finite(d2) and self._is_finite(d3):
                        if d3 > d2 > d1 and d3 > 0:
                            slope_steepening = True

            if not slope_steepening and current_slope <= 0:
                return RedlineAlert(
                    triggered=True,
                    redline_temp=redline_temp,
                    breach_minutes=breach_minute,
                    current_slope=round(current_slope, 6),
                    slope_steepening=False,
                    gradual_steps=[],
                    overshoot_margin=0.0,
                )

            steps = self._compute_gradual_steps(
                current_temp=current_temp,
                current_valve=current_valve,
                current_slope=current_slope,
                slope_steepening=slope_steepening,
                redline_temp=redline_temp,
                breach_minute=breach_minute,
            )

            final_valve = steps[-1].valve_opening if steps else current_valve
            overshoot_margin = self._estimate_overshoot_margin(
                current_temp, current_slope, current_valve, final_valve
            )

            return RedlineAlert(
                triggered=True,
                redline_temp=redline_temp,
                breach_minutes=breach_minute,
                current_slope=round(current_slope, 6),
                slope_steepening=slope_steepening,
                gradual_steps=steps,
                overshoot_margin=round(overshoot_margin, 3),
            )

        except Exception as e:
            print(f"[ERROR] compute_redline_alert failed: {e}")
            return RedlineAlert(triggered=False, redline_temp=redline_temp)

    def _compute_gradual_steps(
        self,
        current_temp: float,
        current_valve: float,
        current_slope: float,
        slope_steepening: bool,
        redline_temp: float,
        breach_minute: Optional[int],
    ) -> List[GradualAdjustmentStep]:
        temp_gap = redline_temp - current_temp
        if temp_gap <= 0:
            total_adjustment = abs(current_slope) * 80 + 25
        else:
            time_to_redline = breach_minute if breach_minute else max(1, temp_gap / max(current_slope, 0.001))
            total_adjustment = (temp_gap / max(time_to_redline, 0.5)) * 60 + abs(current_slope) * 40

        if slope_steepening:
            total_adjustment *= 1.4

        total_adjustment = min(total_adjustment, 85.0 - current_valve)
        total_adjustment = max(0.0, total_adjustment)

        final_valve = min(95.0, current_valve + total_adjustment)

        ramp_profile = [0.15, 0.20, 0.25, 0.22, 0.18]
        cumulative = 0.0
        steps: List[GradualAdjustmentStep] = []

        for minute in range(1, 6):
            weight = ramp_profile[minute - 1]
            increment = total_adjustment * weight
            cumulative += increment
            valve_at_step = min(95.0, current_valve + cumulative)

            if minute == 1:
                note = "初始小幅试探，避免冷媒冲击引发热振荡"
            elif minute == 2:
                note = "观察夹套换热响应，逐步加量"
            elif minute == 3:
                note = "主调节量注入，抑制温升惯性"
            elif minute == 4:
                note = "微调收敛，锁定稳态区间"
            else:
                note = "末段修正，消除残余超调趋势"

            steps.append(GradualAdjustmentStep(
                minute=minute,
                valve_opening=round(valve_at_step, 2),
                increment=round(increment, 2),
                note=note,
            ))

        return steps

    def _estimate_overshoot_margin(
        self,
        current_temp: float,
        current_slope: float,
        current_valve: float,
        final_valve: float,
    ) -> float:
        cooling_gain = (final_valve - current_valve) * 0.0012
        thermal_inertia = current_slope * 3.0
        residual_heat = max(0.0, current_slope * 2.0 - cooling_gain * 2.0)
        return residual_heat
