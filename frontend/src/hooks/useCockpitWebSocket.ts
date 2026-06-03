'use client';
// src/hooks/useCockpitWebSocket.ts
// Real-time WebSocket hook for Cockpit events with auto-reconnect

import { useState, useEffect, useCallback, useRef } from 'react';
import type { CockpitWebSocketEvent, CockpitEventType } from '@/lib/types';

const WS_URL =
  (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000')
    .replace(/^http/, 'ws') + '/api/ws/cockpit';

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseCockpitWebSocketReturn {
  events: CockpitWebSocketEvent[];
  latestEvent: CockpitWebSocketEvent | null;
  connectionState: ConnectionState;
  clearEvents: () => void;
}

const MAX_EVENTS = 200;
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 15000]; // Exponential backoff

export function useCockpitWebSocket(
  onEvent?: (event: CockpitWebSocketEvent) => void
): UseCockpitWebSocketReturn {
  const [events, setEvents] = useState<CockpitWebSocketEvent[]>([]);
  const [latestEvent, setLatestEvent] = useState<CockpitWebSocketEvent | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  const clearEvents = useCallback(() => setEvents([]), []);

  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    isMountedRef.current = true;

    function scheduleReconnect() {
      if (!isMountedRef.current) return;
      const delay =
        RECONNECT_DELAYS[
          Math.min(reconnectAttemptRef.current, RECONNECT_DELAYS.length - 1)
        ];
      reconnectAttemptRef.current += 1;
      reconnectTimerRef.current = setTimeout(connect, delay);
    }

    function connect() {
      if (!isMountedRef.current) return;

      setConnectionState('connecting');

      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMountedRef.current) return;
          reconnectAttemptRef.current = 0;
          setConnectionState('connected');
        };

        ws.onmessage = (evt) => {
          if (!isMountedRef.current) return;
          try {
            const parsed = JSON.parse(evt.data) as CockpitWebSocketEvent;
            if (parsed.type) {
              setLatestEvent(parsed);
              setEvents((prev) => {
                const next = [parsed, ...prev];
                return next.slice(0, MAX_EVENTS);
              });
              onEventRef.current?.(parsed);
            }
          } catch {
            // Raw log message — wrap it as a generic event
            const wrapped: CockpitWebSocketEvent = {
              type: 'run_start' as CockpitEventType,
              timestamp: new Date().toISOString(),
              data: { raw: evt.data },
            };
            setLatestEvent(wrapped);
          }
        };

        ws.onclose = () => {
          if (!isMountedRef.current) return;
          setConnectionState('disconnected');
          scheduleReconnect();
        };

        ws.onerror = () => {
          if (!isMountedRef.current) return;
          setConnectionState('error');
          ws.close();
        };
      } catch {
        setConnectionState('error');
        scheduleReconnect();
      }
    }

    connect();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, []);

  return { events, latestEvent, connectionState, clearEvents };
}
