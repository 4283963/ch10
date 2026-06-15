export interface FermenterInfo {
  id: string;
  name: string;
  target_temp: number;
  current_temp: number;
  current_pressure: number;
  current_valve: number;
}

export interface DataPoint {
  timestamp: string;
  temperature: number;
  inlet_pressure: number;
  valve_opening: number;
}

export interface PredictionPoint {
  timestamp: string;
  temperature: number;
}

export interface ValveAdjustment {
  suggested_opening: number;
  current_opening: number;
  adjustment_pct: number;
  urgency: 'stable' | 'medium' | 'high';
  reason: string;
}

export interface StabilityAnalysis {
  std_dev: number;
  max_deviation: number;
  mean_derivative: number;
  stability_score: number;
}

export interface GradualAdjustmentStep {
  minute: number;
  valve_opening: number;
  increment: number;
  note: string;
}

export interface RedlineAlert {
  triggered: boolean;
  redline_temp: number;
  breach_minutes: number | null;
  current_slope: number;
  slope_steepening: boolean;
  gradual_steps: GradualAdjustmentStep[];
  overshoot_margin: number;
}

export interface FermenterStreamData {
  info: FermenterInfo;
  latest_history: DataPoint;
  prediction: PredictionPoint[];
  valve_adjustment: ValveAdjustment;
  stability: StabilityAnalysis;
  redline_alert: RedlineAlert;
}

export interface StreamPayload {
  timestamp: string;
  fermenters: FermenterStreamData[];
}
