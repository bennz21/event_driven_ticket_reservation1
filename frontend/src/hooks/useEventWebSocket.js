import { useEffect, useState, useRef, useCallback } from 'react';

/**
 * Custom hook managing WebSocket connection for live seat updates and event broadcasts.
 */
export function useEventWebSocket(eventId) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [eventFeed, setEventFeed] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (!eventId) return;

    let wsUrl = '';
    const customWsUrl = import.meta.env.VITE_WS_URL;
    if (customWsUrl) {
      const cleanWsUrl = customWsUrl.replace(/\/+$/, '');
      wsUrl = `${cleanWsUrl}/api/v1/ws/events/${eventId}`;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/api/v1/ws/events/${eventId}`;
    }

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      // Append connection event to feed
      setEventFeed((prev) => [
        {
          id: Date.now(),
          type: 'INFO',
          message: `Connected to live event stream for event #${eventId}`,
          timestamp: new Date().toLocaleTimeString(),
        },
        ...prev.slice(0, 49),
      ]);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);

        // Format activity feed item based on domain event type
        let feedText = '';
        if (data.type === 'seat.held') {
          feedText = `Locked seats [${data.payload.seat_ids.join(', ')}] (Hold expires in 5m)`;
        } else if (data.type === 'seat.released') {
          feedText = `Released seats [${data.payload.seat_ids.join(', ')}] (${data.payload.reason || 'unlocked'})`;
        } else if (data.type === 'reservation.confirmed') {
          feedText = `Booking Confirmed: Reservation #${data.payload.reservation_id} for ${data.payload.customer_name}!`;
        }

        if (feedText) {
          setEventFeed((prev) => [
            {
              id: Date.now() + Math.random(),
              type: data.type,
              message: feedText,
              timestamp: new Date().toLocaleTimeString(),
            },
            ...prev.slice(0, 49),
          ]);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.onerror = (err) => {
      console.warn('WebSocket encountered error:', err);
      ws.close();
    };
  }, [eventId]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return { isConnected, lastMessage, eventFeed };
}
