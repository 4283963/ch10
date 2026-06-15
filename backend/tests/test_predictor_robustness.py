import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.predictor import TemperaturePredictor
from app.models import FermenterDataPoint
from datetime import datetime, timedelta


def make_history(temperatures):
    now = datetime.now()
    history = []
    for i, t in enumerate(temperatures):
        history.append(FermenterDataPoint(
            timestamp=now - timedelta(minutes=len(temperatures) - 1 - i),
            temperature=float(t),
            inlet_pressure=0.35,
            valve_opening=50.0,
        ))
    return history


def test_all_constant():
    """测试完全平坦的数据（零斜率，最容易触发零分母的情况）"""
    predictor = TemperaturePredictor()
    temps = np.full(100, 37.0)
    derivs = predictor.compute_sliding_derivative(temps)

    assert np.all(np.isfinite(derivs)), "导数数组包含 inf/nan"
    assert np.all(np.abs(derivs) < 1e-6), "全常数数据导数应接近0"
    print("✅  test_all_constant passed")


def test_linear_ramp():
    """测试完美线性增长数据，斜率应恒定"""
    predictor = TemperaturePredictor()
    temps = np.linspace(37.0, 38.0, 100)
    derivs = predictor.compute_sliding_derivative(temps)

    valid = derivs[np.isfinite(derivs)]
    assert len(valid) > 50, "有效数据点不足"
    expected_slope = 1.0 / 99.0
    mid_val = valid[len(valid) // 2]
    assert abs(mid_val - expected_slope) < 0.01, f"斜率偏差过大: {mid_val} vs {expected_slope}"
    print("✅  test_linear_ramp passed")


def test_with_nan():
    """测试输入含 NaN 的情况"""
    predictor = TemperaturePredictor()
    temps = np.full(100, 37.0)
    temps[10:15] = np.nan
    temps[50] = np.inf
    temps[80] = -np.inf

    derivs = predictor.compute_sliding_derivative(temps)
    assert np.all(np.isfinite(derivs)), "含NaN输入的导数结果仍有inf/nan"
    print("✅  test_with_nan passed")


def test_all_nan():
    """测试全 NaN 输入"""
    predictor = TemperaturePredictor()
    temps = np.full(50, np.nan)
    derivs = predictor.compute_sliding_derivative(temps)
    assert np.all(np.isfinite(derivs)), "全NaN输入的导数结果有inf/nan"
    print("✅  test_all_nan passed")


def test_single_point():
    """测试极少数据点"""
    predictor = TemperaturePredictor()
    temps = np.array([37.0])
    derivs = predictor.compute_sliding_derivative(temps)
    assert len(derivs) == 1
    assert np.isfinite(derivs[0])
    print("✅  test_single_point passed")


def test_extreme_jump():
    """测试极端跳变数据（模拟剧烈噪声）"""
    predictor = TemperaturePredictor()
    temps = np.full(200, 37.0)
    for i in range(20, 180, 3):
        temps[i] = 37.0 + np.random.uniform(-50, 50)

    derivs = predictor.compute_sliding_derivative(temps)
    assert np.all(np.isfinite(derivs)), "极端跳变数据产生了inf/nan"
    print("✅  test_extreme_jump passed")


def test_predict_temperature_normal():
    """测试正常数据下的预测函数"""
    predictor = TemperaturePredictor()
    temps = np.linspace(37.0, 37.5, 200)
    history = make_history(temps)

    predictions, valve_adj = predictor.predict_temperature(history, 37.0)

    assert len(predictions) == 15
    for p in predictions:
        assert np.isfinite(p.temperature)
    assert np.isfinite(valve_adj.suggested_opening)
    assert 0 <= valve_adj.suggested_opening <= 100
    print("✅  test_predict_temperature_normal passed")


def test_predict_temperature_noisy():
    """测试高噪声数据下预测函数不崩溃"""
    predictor = TemperaturePredictor()
    np.random.seed(42)
    temps = 37.0 + np.random.randn(720) * 5.0
    temps[100] = np.inf
    temps[300] = np.nan
    temps[500] = 1e9

    history = make_history(temps)
    predictions, valve_adj = predictor.predict_temperature(history, 37.0)

    assert len(predictions) == 15
    for p in predictions:
        assert np.isfinite(p.temperature), f"预测温度非有限值: {p.temperature}"
    assert np.isfinite(valve_adj.suggested_opening)
    assert 0 <= valve_adj.suggested_opening <= 100
    print("✅  test_predict_temperature_noisy passed")


def test_predict_empty_history():
    """测试空历史数据"""
    predictor = TemperaturePredictor()
    predictions, valve_adj = predictor.predict_temperature([], 37.0)
    assert len(predictions) == 15
    assert np.isfinite(valve_adj.suggested_opening)
    print("✅  test_predict_empty_history passed")


def test_analyze_stability():
    """测试稳定性分析"""
    predictor = TemperaturePredictor()
    temps = 37.0 + np.random.randn(720) * 0.1
    temps[50] = np.inf

    history = make_history(temps)
    result = predictor.analyze_stability(history, 37.0)

    for key in ['std_dev', 'max_deviation', 'mean_derivative', 'stability_score']:
        assert key in result
        assert np.isfinite(result[key]), f"{key} 非有限值: {result[key]}"
    assert 0 <= result['stability_score'] <= 100
    print("✅  test_analyze_stability passed")


def test_floating_point_error_simulation():
    """模拟零分母极端情况：所有y值完全相同但x也相同（退化情况）"""
    predictor = TemperaturePredictor()

    slope = predictor._robust_slope(np.array([5.0]))
    assert np.isfinite(slope)
    assert slope == 0.0

    slope = predictor._robust_slope(np.array([3.0, 3.0, 3.0]))
    assert np.isfinite(slope)
    assert abs(slope) < 1e-10

    print("✅  test_floating_point_error_simulation passed")


def main():
    print("=" * 60)
    print("运行数值鲁棒性测试套件")
    print("=" * 60)

    tests = [
        test_all_constant,
        test_linear_ramp,
        test_with_nan,
        test_all_nan,
        test_single_point,
        test_extreme_jump,
        test_predict_temperature_normal,
        test_predict_temperature_noisy,
        test_predict_empty_history,
        test_analyze_stability,
        test_floating_point_error_simulation,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌  {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"测试结果: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
