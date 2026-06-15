import React from 'react';
import { Card, Tag, Progress, Space, Typography, Divider } from 'antd';
import type { FermenterStreamData } from '../types';

const { Text, Title } = Typography;

interface Props {
  fermenter: FermenterStreamData;
}

const getUrgencyColor = (urgency: string) => {
  switch (urgency) {
    case 'high': return 'red';
    case 'medium': return 'orange';
    default: return 'green';
  }
};

const getUrgencyText = (urgency: string) => {
  switch (urgency) {
    case 'high': return '紧急调整';
    case 'medium': return '建议微调';
    default: return '状态稳定';
  }
};

export const ValvePanel: React.FC<Props> = ({ fermenter }) => {
  const adj = fermenter.valve_adjustment;
  const stability = fermenter.stability;
  const scoreColor = stability.stability_score >= 85 ? '#22c55e' : stability.stability_score >= 60 ? '#eab308' : '#ef4444';

  return (
    <Card
      size="small"
      style={{ backgroundColor: 'rgba(30, 41, 59, 0.6)', borderColor: '#334155' }}
      bodyStyle={{ padding: 16 }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div>
          <Space align="center" style={{ marginBottom: 12 }}>
            <Title level={5} style={{ margin: 0, color: '#f1f5f9' }}>阀门开度建议</Title>
            <Tag color={getUrgencyColor(adj.urgency)} style={{ margin: 0 }}>
              {getUrgencyText(adj.urgency)}
            </Tag>
          </Space>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>当前开度</Text>
            <Text strong style={{ color: '#e2e8f0', fontSize: 16 }}>{adj.current_opening.toFixed(1)}%</Text>
          </div>
          <Progress
            percent={adj.current_opening}
            showInfo={false}
            strokeColor="#38bdf8"
            trailColor="#1e293b"
            size="small"
            style={{ marginBottom: 16 }}
          />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>建议开度</Text>
            <Text strong style={{ color: adj.urgency === 'stable' ? '#4ade80' : adj.urgency === 'medium' ? '#fbbf24' : '#f87171', fontSize: 18 }}>
              {adj.suggested_opening.toFixed(1)}%
            </Text>
          </div>
          <Progress
            percent={adj.suggested_opening}
            showInfo={false}
            strokeColor={adj.urgency === 'stable' ? '#4ade80' : adj.urgency === 'medium' ? '#fbbf24' : '#f87171'}
            trailColor="#1e293b"
            size="small"
            style={{ marginBottom: 12 }}
          />
          <div style={{
            padding: '10px 12px',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            borderRadius: 6,
            borderLeft: `3px solid ${adj.urgency === 'stable' ? '#22c55e' : adj.urgency === 'medium' ? '#eab308' : '#ef4444'}`
          }}>
            <Text style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.5 }}>{adj.reason}</Text>
          </div>
          {Math.abs(adj.adjustment_pct) >= 0.5 && (
            <div style={{ marginTop: 12, textAlign: 'center' }}>
              <Tag color={adj.adjustment_pct > 0 ? 'red' : 'blue'} style={{ fontSize: 13, padding: '4px 12px' }}>
                {adj.adjustment_pct > 0 ? '↑ 调大' : '↓ 调小'} {Math.abs(adj.adjustment_pct).toFixed(1)} 个百分点
              </Tag>
            </div>
          )}
        </div>

        <Divider style={{ margin: '4px 0', borderColor: '#334155' }} />

        <div>
          <Title level={5} style={{ margin: '0 0 12px 0', color: '#f1f5f9' }}>温度稳定性分析</Title>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
            <Progress
              type="dashboard"
              percent={stability.stability_score}
              strokeColor={scoreColor}
              trailColor="#1e293b"
              width={120}
              format={(p) => <span style={{ color: scoreColor, fontSize: 22, fontWeight: 700 }}>{p}</span>}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <div style={{ padding: 8, backgroundColor: 'rgba(15, 23, 42, 0.5)', borderRadius: 4 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>温度标准差</Text>
              <div><Text strong style={{ color: '#e2e8f0' }}>{stability.std_dev.toFixed(4)} °C</Text></div>
            </div>
            <div style={{ padding: 8, backgroundColor: 'rgba(15, 23, 42, 0.5)', borderRadius: 4 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>最大偏差</Text>
              <div><Text strong style={{ color: '#e2e8f0' }}>{stability.max_deviation.toFixed(3)} °C</Text></div>
            </div>
            <div style={{ gridColumn: '1 / -1', padding: 8, backgroundColor: 'rgba(15, 23, 42, 0.5)', borderRadius: 4 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>温度变化率 (dT/dt)</Text>
              <div><Text strong style={{ color: stability.mean_derivative > 0.01 ? '#f87171' : stability.mean_derivative < -0.01 ? '#60a5fa' : '#4ade80' }}>
                {stability.mean_derivative >= 0 ? '+' : ''}{stability.mean_derivative.toFixed(5)} °C/min
              </Text></div>
            </div>
          </div>
        </div>
      </Space>
    </Card>
  );
};
