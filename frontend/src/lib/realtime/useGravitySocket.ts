import { useEffect, useState, useRef, useCallback } from 'react';

type ConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export function useGravitySocket(urlPath: string | null) {
  const [state, setState] = useState<ConnectionState>('disconnected');
  const [lastMessage, setLastMessage] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const isComponentMounted = useRef(true);

  // Maximum backoff is ~15-30 seconds
  const maxReconnectDelay = 30000;

  const connect = useCallback(() => {
    if (!urlPath) {
      if (wsRef.current) {
        wsRef.current.close(1000, 'URL Path removed');
        wsRef.current = null;
        setState('disconnected');
      }
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      // If URL changed, we need to reconnect, but let's assume it's handled by useEffect below closing the old one
      return;
    }

    setState('connecting');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const baseHost = import.meta.env.VITE_API_URL 
        ? new URL(import.meta.env.VITE_API_URL).host 
        : window.location.host;
        
    const wsUrl = `${protocol}//${baseHost}${urlPath}`;
    
    console.log(`[WebSocket] Connecting to ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`[WebSocket] Connected to ${urlPath}`);
      if (isComponentMounted.current) {
        setState('connected');
        reconnectAttempts.current = 0; // Reset backoff
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (isComponentMounted.current) {
          setLastMessage(data);
        }
      } catch (err) {
        console.error('[WebSocket] Failed to parse message', err);
      }
    };

    ws.onclose = (event) => {
      if (!isComponentMounted.current) return;
      console.log(`[WebSocket] Disconnected from ${urlPath}`, event.code);
      setState('disconnected');

      // Do not reconnect on normal closes or auth failure (4003)
      if (event.code !== 1000 && event.code !== 4003 && urlPath) {
        setState('reconnecting');
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), maxReconnectDelay);
        reconnectAttempts.current += 1;
        console.log(`[WebSocket] Reconnecting in ${delay}ms...`);
        setTimeout(() => {
          if (isComponentMounted.current && urlPath) {
            connect();
          }
        }, delay);
      }
    };

    ws.onerror = (err) => {
      console.error(`[WebSocket] Error on ${urlPath}`, err);
    };
  }, [urlPath]);

  useEffect(() => {
    isComponentMounted.current = true;
    
    // Close old connection if URL changes
    if (wsRef.current && wsRef.current.url.indexOf(urlPath || 'null') === -1) {
       wsRef.current.close(1000, 'URL changed');
       wsRef.current = null;
    }

    connect();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && urlPath) {
        // We just woke up / foregrounded.
        if (wsRef.current?.readyState !== WebSocket.OPEN && wsRef.current?.readyState !== WebSocket.CONNECTING) {
           reconnectAttempts.current = 0;
           connect();
        }
      }
    };

    const handleOnline = () => {
      if (urlPath && wsRef.current?.readyState !== WebSocket.OPEN && wsRef.current?.readyState !== WebSocket.CONNECTING) {
        reconnectAttempts.current = 0;
        connect();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('online', handleOnline);

    return () => {
      isComponentMounted.current = false;
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('online', handleOnline);
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
    };
  }, [urlPath, connect]);

  return { state, lastMessage };
}
