import React from 'react';
import { Card, Tag, Typography, Space, Divider } from 'antd';
import { WarningOutlined, ArrowUpOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { RedlineAlert } from '../types';

const { Text, Title } = Typography;

interface Props {
  alert: RedlineAlert;
  fermenterName: string;
  currentValve: number;
}

export const RedlineAlertCard: React.FC<Props> = ({ alert, fermenterName, currentValve }) => {
  if (!alert.triggered || alert.gradual_steps.length === 0) {
    return null;
  }

  return (
    <Card
      size="small"
      style={{
        background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.18) 0%, rgba(239, 68, 68, 0.08) 100%)',
        borderColor: '#ef4444',
        borderWidth: 2,
        borderRadius: 8,
        boxShadow: '0 0 16px rgba(239, 68, 68, 0.2)',
        animation: 'pulse-red 2s ease-in-out infinite',
      }}
      styles={{ body: { padding: 14 } }}
    >
      <style>{`
        @keyframes pulse-red {
          0%, 100% { box-shadow: 0 0 8px rgba(239, 68, 68, 0.15); }
          50% { box-shadow: 0 0 20px rgba(239, 68, 68, 0.35); }
        }
      `}</style>

      <Space direction="vertical" size={10} style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space align="center" size={6}>
            <WarningOutlined style={{ color: '#ef4444', fontSize: 18 }} />
            <Title level={5} style={{ color: '#fca5a5', margin: 0 }}>红线预警</Title>
          </Space>
          <Tag color="red" icon={<ThunderboltOutlined />} style={{ fontSize: 12, padding: '2px 8px' }}>
            {alert.breach_minutes ? `${alert.breach_minutes}分钟后突破` : '已超红线'}
          </Tag>
        </div>

        <div style={{ padding: '8px 10px', backgroundColor: 'rgba(15, 23, 42, 0.5)', borderRadius: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>安全红线</Text>
            <Text strong style={{ color: '#f87171', fontSize: 15 }}>{alert.redline_temp}°C</Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>当前温升斜率</Text>
            <Space size={4} align="center">
              <ArrowUpOutlined style={{ color: '#f87171', fontSize: 12 }} />
              <Text strong style={{ color: '#f87171', fontSize: 14 }}>
                +{alert.current_slope.toFixed(4)} °C/min
              </Text>
            </Space>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>斜率趋势</Text>
            <Tag color={alert.slope_steepening ? 'red' : 'orange'} style={{ margin: 0, fontSize: 11 }}>
              {alert.slope_steepening ? '⚠ 变陡加速中' : '趋缓'}
            </Tag>
          </div>
        </div>

        <Divider style={{ margin: '4px 0', borderColor: 'rgba(239, 68, 68, 0.25)' }} />

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <Text strong style={{ color: '#fbbf24', fontSize: 13 }}>
              阀门渐进微调方案（5分钟）
            </Text>
            <Text type="secondary" style={{ fontSize: 11 }}>
              当前 {currentValve.toFixed(1)}%
            </Text>
          </div>

          {alert.gradual_steps.map((step, idx) => {
            const barWidth = Math.min(100, ((step.valve_opening - currentValve) / (95 - currentValve)) * 100);
            const isLast = idx === alert.gradual_steps.length - 1;
            return (
              <div
                key={step.minute}
                style={{
                  padding: '6px 10px',
                  backgroundColor: isLast ? 'rgba(34, 197, 94, 0.1)' : 'rgba(15, 23, 42, 0.5)',
                  borderRadius: 4,
                  marginBottom: 4,
                  borderLeft: isLast ? '3px solid #22c55e' : '3px solid #475569',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <Space size={6}>
                    <Text style={{ color: '#94a3b8', fontSize: 11, fontWeight: 600 }}>
                      第{step.minute}分钟
                    </Text>
                    <Text style={{ color: isLast ? '#4ade80' : '#e2e8f0', fontSize: 13, fontWeight: 700 }}>
                      {step.valve_opening.toFixed(1)}%
                    </Text>
                    <Tag
                      color={step.increment > 0 ? 'red' : 'blue'}
                      style={{ fontSize: 10, padding: '0 4px', margin: 0, lineHeight: '18px' }}
                    >
                      {step.increment > 0 ? '+' : ''}{step.increment.toFixed(1)}
                    </Tag>
                  </Space>
                </div>
                <div style={{
                  height: 3,
                  backgroundColor: '#1e293b',
                  borderRadius: 2,
                  overflow: 'hidden',
                  marginBottom: 4,
                }}>
                  <div style={{
                    height: '100%',
                    width: `${barWidth}%`,
                    backgroundColor: isLast ? '#22c55e' : '#f59e0b',
                    borderRadius: 2,
                    transition: 'width 0.3s ease',
                  }} />
                </div>
                <Text style={{ color: '#94a3b8', fontSize: 10, lineHeight: 1.3 }}>{step.note}</Text>
              </div>
            );
          })}
        </div>

        {alert.overshoot_margin > 0.01 && (
          <div style={{
            padding: '8px 10px',
            backgroundColor: 'rgba(245, 158, 11, 0.12)',
            borderRadius: 6,
            borderLeft: '3px solid #f59e0b',
          }}>
            <Text style={{ color: '#fbbf24', fontSize: 12 }}>
              预估残余热超调余量: <Text strong style={{ color: '#fbbf24' }}>{alert.overshoot_margin.toFixed(3)} °C</Text>
            </Text>
          </div>
        )}
      </Space>
    </Card>
  );
};
