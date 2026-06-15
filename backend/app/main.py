from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
from datetime import datetime
from typing import List

from .models import (
    FermenterInfo, FermenterStatus, FermenterDataPoint,
    PredictionPoint, ValveAdjustment, RedlineAlert
)
from .timeseries_db import TimeSeriesDBSimulator
from .predictor import TemperaturePredictor


app = FastAPI(
    title="发酵罐组夹套冷却水电动阀微调与温度稳定性分析系统",
    description="生物制药厂发酵车间温度监控与预测系统",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = TimeSeriesDBSimulator()
predictor = TemperaturePredictor()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(db.start_simulation())


@app.get("/api/fermenters", response_model=List[FermenterInfo])
async def get_all_fermenters():
    result = []
    for fid in db.get_fermenter_ids():
        cfg = db.get_fermenter_config(fid)
        history = db.get_history(fid, hours=0.1)
        if history:
            latest = history[-1]
            result.append(FermenterInfo(
                id=fid,
                name=cfg.get("name", fid),
                target_temp=cfg.get("target_temp", 37.0),
                current_temp=latest.temperature,
                current_pressure=latest.inlet_pressure,
                current_valve=latest.valve_opening,
            ))
    return result


@app.get("/api/fermenters/{fid}", response_model=FermenterStatus)
async def get_fermenter_status(fid: str):
    if fid not in db.get_fermenter_ids():
        raise HTTPException(status_code=404, detail=f"发酵罐 {fid} 不存在")

    cfg = db.get_fermenter_config(fid)
    history = db.get_history(fid, hours=12.0)
    if not history:
        raise HTTPException(status_code=404, detail=f"发酵罐 {fid} 暂无数据")

    latest = history[-1]
    prediction, valve_adj = predictor.predict_temperature(history, cfg.get("target_temp", 37.0))
    redline_alert = predictor.compute_redline_alert(history, prediction, redline_temp=37.5)

    return FermenterStatus(
        info=FermenterInfo(
            id=fid,
            name=cfg.get("name", fid),
            target_temp=cfg.get("target_temp", 37.0),
            current_temp=latest.temperature,
            current_pressure=latest.inlet_pressure,
            current_valve=latest.valve_opening,
        ),
        history=history,
        prediction=prediction,
        valve_adjustment=valve_adj,
        redline_alert=redline_alert,
    )


@app.get("/api/fermenters/{fid}/stability")
async def get_fermenter_stability(fid: str):
    if fid not in db.get_fermenter_ids():
        raise HTTPException(status_code=404, detail=f"发酵罐 {fid} 不存在")

    cfg = db.get_fermenter_config(fid)
    history = db.get_history(fid, hours=12.0)
    if not history:
        raise HTTPException(status_code=404, detail=f"发酵罐 {fid} 暂无数据")

    stability = predictor.analyze_stability(history, cfg.get("target_temp", 37.0))
    return {"fermenter_id": fid, **stability}


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            all_status = []
            for fid in db.get_fermenter_ids():
                cfg = db.get_fermenter_config(fid)
                history = db.get_history(fid, hours=12.0)
                if not history:
                    continue
                latest = history[-1]
                prediction, valve_adj = predictor.predict_temperature(history, cfg.get("target_temp", 37.0))
                stability = predictor.analyze_stability(history, cfg.get("target_temp", 37.0))
                redline_alert = predictor.compute_redline_alert(history, prediction, redline_temp=37.5)

                all_status.append({
                    "info": {
                        "id": fid,
                        "name": cfg.get("name", fid),
                        "target_temp": cfg.get("target_temp", 37.0),
                        "current_temp": latest.temperature,
                        "current_pressure": latest.inlet_pressure,
                        "current_valve": latest.valve_opening,
                    },
                    "latest_history": {
                        "timestamp": latest.timestamp.isoformat(),
                        "temperature": latest.temperature,
                        "inlet_pressure": latest.inlet_pressure,
                        "valve_opening": latest.valve_opening,
                    },
                    "prediction": [
                        {"timestamp": p.timestamp.isoformat(), "temperature": p.temperature}
                        for p in prediction
                    ],
                    "valve_adjustment": {
                        "suggested_opening": valve_adj.suggested_opening,
                        "current_opening": valve_adj.current_opening,
                        "adjustment_pct": valve_adj.adjustment_pct,
                        "urgency": valve_adj.urgency,
                        "reason": valve_adj.reason,
                    },
                    "stability": stability,
                    "redline_alert": {
                        "triggered": redline_alert.triggered,
                        "redline_temp": redline_alert.redline_temp,
                        "breach_minutes": redline_alert.breach_minutes,
                        "current_slope": redline_alert.current_slope,
                        "slope_steepening": redline_alert.slope_steepening,
                        "gradual_steps": [
                            {
                                "minute": s.minute,
                                "valve_opening": s.valve_opening,
                                "increment": s.increment,
                                "note": s.note,
                            }
                            for s in redline_alert.gradual_steps
                        ],
                        "overshoot_margin": redline_alert.overshoot_margin,
                    },
                })

            payload = json.dumps({
                "timestamp": datetime.now().isoformat(),
                "fermenters": all_status,
            }, ensure_ascii=False)
            await websocket.send_text(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.get("/")
async def root():
    return {
        "name": "发酵罐组夹套冷却水电动阀微调与温度稳定性分析系统",
        "version": "1.0.0",
        "endpoints": {
            "fermenters_list": "/api/fermenters",
            "fermenter_detail": "/api/fermenters/{fid}",
            "fermenter_stability": "/api/fermenters/{fid}/stability",
            "realtime_stream": "/ws/stream",
        }
    }
