import { useEffect, useRef, useState, useCallback } from 'react';
import type { StreamPayload, FermenterStreamData } from '../types';

async function fetchAllFermenters(): Promise<FermenterStreamData[]> {
  try {
    const listRes = await fetch('/api/fermenters');
    if (!listRes.ok) return [];
    const list = await listRes.json();
    const result: FermenterStreamData[] = [];
    for (const info of list) {
      try {
        const detailRes = await fetch(`/api/fermenters/${info.id}`);
        if (!detailRes.ok) continue;
        const detail = await detailRes.json();
        const stabilityRes = await fetch(`/api/fermenters/${info.id}/stability`);
        const stability = stabilityRes.ok ? await stabilityRes.json() : {
          std_dev: 0, max_deviation: 0, mean_derivative: 0, stability_score: 70
        };
        const history = detail.history || [];
        const latest = history.length > 0 ? history[history.length - 1] : null;
        result.push({
          info: detail.info,
          latest_history: latest || {
            timestamp: new Date().toISOString(),
            temperature: info.current_temp,
            inlet_pressure: info.current_pressure,
            valve_opening: info.current_valve,
          },
          prediction: detail.prediction || [],
          valve_adjustment: detail.valve_adjustment || {
            suggested_opening: info.current_valve,
            current_opening: info.current_valve,
            adjustment_pct: 0,
            urgency: 'stable',
            reason: '状态稳定',
          },
          stability: {
            std_dev: stability.std_dev,
            max_deviation: stability.max_deviation,
            mean_derivative: stability.mean_derivative,
            stability_score: stability.stability_score,
          },
        });
      } catch (e) {
        console.error(`Failed to fetch ${info.id}:`, e);
      }
    }
    return result;
  } catch (e) {
    console.error('Failed to fetch fermenters:', e);
    return [];
  }
}

export function useFermenterStream() {
  const [data, setData] = useState<FermenterStreamData[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return;
    const doFetch = async () => {
      const result = await fetchAllFermenters();
      if (result.length > 0) {
        setData(result);
      }
    };
    doFetch();
    pollTimerRef.current = window.setInterval(doFetch, 3000);
  }, []);

  const connect = useCallback(() => {
    const wsUrl = `ws://localhost:8000/ws/stream`;
    try {
      wsRef.current = new WebSocket(wsUrl);
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      startPolling();
      return;
    }

    let opened = false;

    wsRef.current.onopen = () => {
      opened = true;
      setConnected(true);
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    wsRef.current.onmessage = (event) => {
      try {
        const payload: StreamPayload = JSON.parse(event.data);
        setData(payload.fermenters);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
      if (!opened) {
        startPolling();
      }
    };

    wsRef.current.onclose = () => {
      setConnected(false);
      if (!pollTimerRef.current) {
        startPolling();
      }
      reconnectTimerRef.current = window.setTimeout(connect, 5000);
    };
  }, [startPolling]);

  useEffect(() => {
    startPolling();
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [connect, startPolling]);

  return { data, connected };
}
