import asyncio
import json
import os
import tzlocal
from datetime import datetime

import websockets


class SimpleRealtime:
    def __init__(self, event_loop=None, debug=False):
        self.url = 'wss://api.openai.com/v1/realtime'
        self.debug = debug
        self.event_loop = event_loop
        self.logs = []
        self.ws = None
        self._message_handler_task = None


    def is_connected(self):
        return self.ws is not None and self.ws.open


    def log_event(self, event_type, event):
        if self.debug:
            local_timezone = tzlocal.get_localzone() 
            now = datetime.now(local_timezone).strftime("%H:%M:%S")
            msg = json.dumps(event)
            self.logs.append((now, event_type, msg))

        return True

    async def connect(self, model="gpt-4o-realtime-preview-2024-10-01"):
        if self.is_connected():
            raise Exception("Already connected")

        headers = {
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        self.ws = await websockets.connect(f"{self.url}?model={model}", extra_headers=headers)
        
        # Start the message handler in the same loop as the websocket
        self._message_handler_task = self.event_loop.create_task(self._message_handler())
        
        return True


    async def _message_handler(self):
        try:
            while True:
                if not self.ws:
                    await asyncio.sleep(0.1)
                    continue
                    
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=0.1)
                    data = json.loads(message)
                    self.receive(data)
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
        except Exception as e:
            print(f"Message handler error: {e}")
            await self.disconnect()


    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.ws = None
        if self._message_handler_task:
            self._message_handler_task.cancel()
            try:
                await self._message_handler_task
            except asyncio.CancelledError:
                pass
        self._message_handler_task = None
        return True


    def receive(self, event):
        self.log_event("server", event)
        #self.dispatch(f"server.{event_name}", event)
        #self.dispatch("server.*", event)
        return True


    def send(self, event_name, data=None):
        if not self.is_connected():
            raise Exception("RealtimeAPI is not connected")
        
        data = data or {}
        if not isinstance(data, dict):
            raise ValueError("data must be a dictionary")
        
        event = {
            "type": event_name,
            **data
        }
        
        #self.dispatch(f"client.{event_name}", event)
        #self.dispatch("client.*", event)
        self.log_event("client", event)
        
        self.event_loop.create_task(self.ws.send(json.dumps(event)))

        return True
    