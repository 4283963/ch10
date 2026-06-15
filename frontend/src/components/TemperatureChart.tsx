import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import type { FermenterStreamData } from '../types';

interface Props {
  fermenter: FermenterStreamData;
  historyPoints: { timestamp: string; temperature: number }[];
}

export const TemperatureChart: React.FC<Props> = ({ fermenter, historyPoints }) => {
  const option = useMemo(() => {
    const targetTemp = fermenter.info.target_temp;
    const historyData = historyPoints.map(p => [p.timestamp, p.temperature]);
    const predictionData = fermenter.prediction.map(p => [p.timestamp, p.temperature]);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(30, 41, 59, 0.95)',
        borderColor: '#475569',
        textStyle: { color: '#e2e8f0' },
        formatter: (params: any[]) => {
          let html = `<div style="font-weight:600;margin-bottom:6px">${params[0].axisValueLabel}</div>`;
          params.forEach((p: any) => {
            html += `<div style="display:flex;align-items:center;gap:6px;margin:3px 0">
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color}"></span>
              <span>${p.seriesName}:</span>
              <span style="font-weight:600">${p.value[1].toFixed(3)} °C</span>
            </div>`;
          });
          return html;
        }
      },
      legend: {
        top: 0,
        right: 10,
        textStyle: { color: '#cbd5e1' },
        data: ['历史温度', '预测温度', '目标温度']
      },
      grid: {
        left: 50,
        right: 30,
        top: 40,
        bottom: 40
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: '#475569' } },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        splitLine: { lineStyle: { color: '#1e293b', type: 'dashed' } }
      },
      yAxis: {
        type: 'value',
        name: '温度 (°C)',
        nameTextStyle: { color: '#94a3b8' },
        min: targetTemp - 2,
        max: targetTemp + 2,
        axisLine: { lineStyle: { color: '#475569' } },
        axisLabel: { color: '#94a3b8', formatter: (v: number) => v.toFixed(1) },
        splitLine: { lineStyle: { color: '#1e293b', type: 'dashed' } }
      },
      series: [
        {
          name: '历史温度',
          type: 'line',
          data: historyData,
          smooth: true,
          symbol: 'none',
          lineStyle: { color: '#38bdf8', width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(56, 189, 248, 0.25)' },
                { offset: 1, color: 'rgba(56, 189, 248, 0.0)' }
              ]
            }
          }
        },
        {
          name: '预测温度',
          type: 'line',
          data: predictionData,
          smooth: true,
          symbol: 'none',
          lineStyle: { color: '#f472b6', width: 2.5, type: 'dashed' },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(244, 114, 182, 0.2)' },
                { offset: 1, color: 'rgba(244, 114, 182, 0.0)' }
              ]
            }
          }
        },
        {
          name: '目标温度',
          type: 'line',
          data: historyData.length > 0
            ? [[historyData[0][0], targetTemp], [predictionData.length > 0 ? predictionData[predictionData.length - 1][0] : historyData[historyData.length - 1][0], targetTemp]]
            : [],
          symbol: 'none',
          lineStyle: { color: '#fbbf24', width: 1.5, type: 'dotted' }
        }
      ]
    };
  }, [fermenter, historyPoints]);

  return (
    <ReactECharts
      option={option}
      style={{ height: 380, width: '100%' }}
      notMerge={true}
      lazyUpdate={true}
    />
  );
};
