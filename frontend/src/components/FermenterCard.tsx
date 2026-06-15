import React from 'react';
import { Card, Tag, Typography, Space } from 'antd';
import { WarningOutlined } from '@ant-design/icons';
import type { FermenterStreamData } from '../types';

const { Text } = Typography;

interface Props {
  fermenter: FermenterStreamData;
  selected: boolean;
  onClick: () => void;
}

export const FermenterCard: React.FC<Props> = ({ fermenter, selected, onClick }) => {
  const info = fermenter.info;
  const diff = info.current_temp - info.target_temp;
  const stability = fermenter.stability;
  const redline = fermenter.redline_alert;

  const tempColor = Math.abs(diff) > 0.5 ? '#ef4444' : Math.abs(diff) > 0.2 ? '#eab308' : '#22c55e';
  const stabilityColor = stability.stability_score >= 85 ? '#22c55e' : stability.stability_score >= 60 ? '#eab308' : '#ef4444';

  const isRedlineTriggered = redline?.triggered && redline?.gradual_steps?.length > 0;
  const cardBg = isRedlineTriggered
    ? (selected ? 'rgba(239, 68, 68, 0.2)' : 'rgba(239, 68, 68, 0.1)')
    : (selected ? 'rgba(56, 189, 248, 0.15)' : 'rgba(30, 41, 59, 0.6)');
  const cardBorder = isRedlineTriggered
    ? '#ef4444'
    : (selected ? '#38bdf8' : '#334155');

  return (
    <Card
      hoverable
      size="small"
      onClick={onClick}
      style={{
        backgroundColor: cardBg,
        borderColor: cardBorder,
        borderWidth: isRedlineTriggered ? 2 : (selected ? 2 : 1),
        cursor: 'pointer',
        transition: 'all 0.2s',
        ...(isRedlineTriggered ? { boxShadow: '0 0 12px rgba(239, 68, 68, 0.2)' } : {}),
      }}
      styles={{ body: { padding: 12 } }}
    >
      <Space direction="vertical" size={6} style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space size={4}>
            <Text strong style={{ color: '#f1f5f9', fontSize: 14 }}>{info.name}</Text>
            {isRedlineTriggered && (
              <WarningOutlined style={{ color: '#ef4444', fontSize: 14 }} />
            )}
          </Space>
          <Space size={4}>
            {isRedlineTriggered && (
              <Tag color="red" style={{ margin: 0, fontSize: 10, padding: '0 4px', lineHeight: '16px' }}>
                红线
              </Tag>
            )}
            <Tag color={stabilityColor} style={{ margin: 0, fontSize: 11 }}>
              稳定度 {stability.stability_score.toFixed(0)}
            </Tag>
          </Space>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <Text style={{ color: tempColor, fontSize: 22, fontWeight: 700 }}>
            {info.current_temp.toFixed(2)}°C
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            目标 {info.target_temp}°C
          </Text>
        </div>
        <Text style={{
          color: tempColor,
          fontSize: 12,
          fontWeight: 500
        }}>
          {diff >= 0 ? '+' : ''}{diff.toFixed(2)}°C
        </Text>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            压力 {info.current_pressure.toFixed(3)}MPa
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            阀门 {info.current_valve.toFixed(0)}%
          </Text>
        </div>
      </Space>
    </Card>
  );
};
