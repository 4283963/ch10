import React, { useState, useMemo, useRef, useEffect } from 'react';
import { Layout, Typography, Row, Col, Space, Badge, Spin, Empty, Tag, Divider } from 'antd';
import { EnvironmentOutlined, ThunderboltOutlined, WarningOutlined } from '@ant-design/icons';
import { useFermenterStream } from './hooks/useFermenterStream';
import { FermenterCard } from './components/FermenterCard';
import { TemperatureChart } from './components/TemperatureChart';
import { ValvePanel } from './components/ValvePanel';
import { RedlineAlertCard } from './components/RedlineAlertCard';
import type { FermenterStreamData } from './types';
import './App.css';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

const HISTORY_BUFFER_SIZE = 120;

function App() {
  const { data, connected } = useFermenterStream();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const historyBufferRef = useRef<Record<string, { timestamp: string; temperature: number }[]>>({});

  useEffect(() => {
    if (!selectedId && data.length > 0) {
      setSelectedId(data[0].info.id);
    }
  }, [data, selectedId]);

  useEffect(() => {
    data.forEach(f => {
      if (!historyBufferRef.current[f.info.id]) {
        historyBufferRef.current[f.info.id] = [];
      }
      const buf = historyBufferRef.current[f.info.id];
      const lastTs = buf.length > 0 ? buf[buf.length - 1].timestamp : null;
      if (lastTs !== f.latest_history.timestamp) {
        buf.push({
          timestamp: f.latest_history.timestamp,
          temperature: f.latest_history.temperature
        });
        if (buf.length > HISTORY_BUFFER_SIZE) {
          buf.splice(0, buf.length - HISTORY_BUFFER_SIZE);
        }
      }
    });
  }, [data]);

  const selected: FermenterStreamData | null = useMemo(() => {
    if (!selectedId) return null;
    return data.find(f => f.info.id === selectedId) || null;
  }, [data, selectedId]);

  const selectedHistory = useMemo(() => {
    if (!selectedId) return [];
    return historyBufferRef.current[selectedId] || [];
  }, [selected, selectedId]);

  const summary = useMemo(() => {
    if (data.length === 0) return { stable: 0, warn: 0, alarm: 0, redline: 0 };
    let stable = 0, warn = 0, alarm = 0, redline = 0;
    data.forEach(f => {
      const diff = Math.abs(f.info.current_temp - f.info.target_temp);
      const isRedline = f.redline_alert?.triggered && f.redline_alert?.gradual_steps?.length > 0;
      if (isRedline) redline++;
      else if (diff > 0.5) alarm++;
      else if (diff > 0.2) warn++;
      else stable++;
    });
    return { stable, warn, alarm, redline };
  }, [data]);

  const redlineFermenters = useMemo(() => {
    return data.filter(f => f.redline_alert?.triggered && f.redline_alert?.gradual_steps?.length > 0);
  }, [data]);

  return (
    <Layout style={{ minHeight: '100vh', backgroundColor: '#0f172a' }}>
      <Header style={{
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        borderBottom: '1px solid #1e293b',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 64
      }}>
        <Space size="large" align="center">
          <EnvironmentOutlined style={{ fontSize: 28, color: '#38bdf8' }} />
          <div>
            <Title level={4} style={{ color: '#f1f5f9', margin: 0 }}>发酵温度质量工艺台</Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              夹套冷却水电动阀微调与温度稳定性分析系统
            </Text>
          </div>
        </Space>
        <Space size="large">
          <Space size="middle">
            <Badge status="success" text={<span style={{ color: '#4ade80' }}>正常 {summary.stable}</span>} />
            <Badge status="warning" text={<span style={{ color: '#fbbf24' }}>预警 {summary.warn}</span>} />
            <Badge status="error" text={<span style={{ color: '#f87171' }}>告警 {summary.alarm}</span>} />
            {summary.redline > 0 && (
              <Badge color="red" text={
                <span style={{ color: '#ef4444', fontWeight: 600 }}>
                  <WarningOutlined style={{ marginRight: 4 }} />
                  红线 {summary.redline}
                </span>
              } />
            )}
          </Space>
          <Space align="center">
            <Spin size="small" spinning={!connected} />
            <Tag color={connected ? 'green' : 'red'} icon={<ThunderboltOutlined />}>
              {connected ? '实时数据已连接' : '连接中...'}
            </Tag>
          </Space>
        </Space>
      </Header>

      <Layout>
        <Sider
          width={300}
          style={{
            backgroundColor: 'rgba(15, 23, 42, 0.7)',
            borderRight: '1px solid #1e293b',
            overflow: 'auto',
            height: 'calc(100vh - 64px)',
            padding: 16
          }}
        >
          {redlineFermenters.length > 0 && (
            <>
              <Title level={5} style={{ color: '#ef4444', margin: '0 0 10px 0' }}>
                <WarningOutlined style={{ marginRight: 6 }} />
                红线预警 ({redlineFermenters.length})
              </Title>
              <Space direction="vertical" size={10} style={{ width: '100%', marginBottom: 12 }}>
                {redlineFermenters.map(f => (
                  <RedlineAlertCard
                    key={f.info.id}
                    alert={f.redline_alert}
                    fermenterName={f.info.name}
                    currentValve={f.info.current_valve}
                  />
                ))}
              </Space>
              <Divider style={{ margin: '8px 0', borderColor: '#334155' }} />
            </>
          )}

          <Title level={5} style={{ color: '#cbd5e1', margin: '0 0 12px 0' }}>
            发酵罐列表 ({data.length})
          </Title>
          {data.length === 0 ? (
            <Empty
              description={<Text type="secondary">等待数据...</Text>}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ marginTop: 40 }}
            />
          ) : (
            <Space direction="vertical" size={10} style={{ width: '100%' }}>
              {data.map(f => (
                <FermenterCard
                  key={f.info.id}
                  fermenter={f}
                  selected={selectedId === f.info.id}
                  onClick={() => setSelectedId(f.info.id)}
                />
              ))}
            </Space>
          )}
        </Sider>

        <Content style={{ padding: 20, backgroundColor: 'transparent' }}>
          {selected ? (
            <Row gutter={20}>
              <Col span={17}>
                <div style={{
                  backgroundColor: 'rgba(30, 41, 59, 0.6)',
                  border: '1px solid #334155',
                  borderRadius: 8,
                  padding: 16
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Space>
                      <Title level={4} style={{ color: '#f1f5f9', margin: 0 }}>
                        {selected.info.name} — 温度趋势
                      </Title>
                      <Tag color="blue">目标 {selected.info.target_temp}°C</Tag>
                      {selected.redline_alert?.triggered && selected.redline_alert?.gradual_steps?.length > 0 && (
                        <Tag color="red" icon={<WarningOutlined />}>
                          红线 {selected.redline_alert.redline_temp}°C
                        </Tag>
                      )}
                    </Space>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      过去 2 小时实测 · 未来 15 分钟预测
                    </Text>
                  </div>
                  <TemperatureChart fermenter={selected} historyPoints={selectedHistory} />
                </div>
              </Col>
              <Col span={7}>
                <ValvePanel fermenter={selected} />
              </Col>
            </Row>
          ) : (
            <Empty
              description={<Text type="secondary">请从左侧选择发酵罐查看详情</Text>}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ marginTop: 200 }}
            />
          )}
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
