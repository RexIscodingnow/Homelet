import time
import asyncio
from typing import Optional


class AsyncDeviceController:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.client_address = None

        # The event records the client (ESP32) connection status
        self.connected_event = asyncio.Event()

    @property
    def connected(self):
        return True if self.connected_event.is_set() else False


    async def _handle_client(self,
                             reader: asyncio.StreamReader,
                             writer: asyncio.StreamWriter):
        """
        When the Clinet connection is established,
        the callback function automatically invoked by
        asyncio (Callback)
        """
        self.reader = reader
        self.writer = writer
        self.client_address = writer.get_extra_info('peername')
        self.connected_event.set()

        print(f"\n[Server] Client (ESP32) Connected from: {self.client_address}")

        try:
            # Continuously read data from the ESP32 when available.
            while not reader.at_eof():
                data = await reader.readline()
                if not data:
                    break

                message = data.decode('utf-8').strip()
                if message:
                    print(f"[Received from client (ESP32)]: {message}")

        except asyncio.CancelledError:
            pass

        except Exception as e:
            print(f"[Server] Error handling client: {e}")

        finally:
            print(f"[Server] client (ESP32) Disconnected: {self.client_address}")
            self.connected_event.clear()
            self.reader = None
            self.writer = None
            self.client_address = None


    async def start_server(self) -> bool:
        try:
            self.server = await asyncio.start_server(self._handle_client,
                                                     self.host,
                                                     self.port,
                                                     reuse_address=True)
            print(f"[Server] Async TCP Server running on {self.host}:{self.port}...")
            return True

        except Exception as e:
            print(f"[Server] Failed to start server: {e}")
            return False


    async def wait_for_conn(self, timeout: Optional[float] = None) -> bool:
        if not self.server:
            print("[Server] Server is not running.")
            return False

        if self.connected_event.is_set():
            return True

        print("[Server] Waiting for client (ESP32) to connect...")

        try:
            if timeout is None:
                await self.connected_event.wait()
            else:
                await asyncio.wait_for(self.connected_event.wait(), timeout=timeout)

            return True

        except asyncio.TimeoutError:
            print("[Server] Timeout waiting for client (ESP32) connection.")
            await self.stop_server()
            return False


    async def start_conn(self, timeout: float | None = None) -> bool:
        if not await self.start_server():
            return False

        if await self.wait_for_conn(timeout):
            await self.send_timestamp(int(time.time()))
            await asyncio.sleep(0.5)
            return True
        
        else:
            return False


    async def send_raw_message(self, message: str) -> bool:
        if not self.writer or self.writer.is_closing():
            print("[Server] No active client connection to send message.")
            self.connected_event.clear()
            return False

        try:
            if not message.endswith('\n'):
                message += '\n'

            self.writer.write(message.encode('utf-8'))
            await self.writer.drain()

            print(f"[Sent]: {message.strip()}")
            return True

        except Exception as e:
            print(f"[Server] Failed to send message: {e}")
            return False


    async def send_control_action(self, action: str) -> bool:
        return await self.send_raw_message(f"CONTROL:{action}")


    async def send_timestamp(self, timestamp: int) -> bool:
        return await self.send_raw_message(f"TIMESTAMP:{timestamp}")


    async def stop_server(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("[Server] Async TCP Server stopped.")


if __name__ == "__main__":
    # unit test
    async def background_task():
        """
        Simulate an asynchronous background task running the Raspberry Pi
        while waiting for a connection.
        """
        for i in range(30):
            print(f"[Background Task] Doing other work... ({i+1})")
            await asyncio.sleep(1)


    async def main():
        controller = AsyncDeviceController(host="0.0.0.0", port=8080)

        if await controller.start_server():
            bg_task = asyncio.create_task(background_task())

            if await controller.wait_for_conn(timeout=60.0):
                await controller.send_timestamp(int(time.time()))
                await asyncio.sleep(0.5)

                await controller.send_control_action("START")
                await asyncio.sleep(2)

                await controller.send_control_action("STOP")

            bg_task.cancel()
            await controller.stop_server()

    asyncio.run(main())

