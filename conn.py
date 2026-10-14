import socket
from typing import Optional


class ESP32Controller:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.client_address = None


    def start_server(self) -> bool:
        try:
            self.server_socket = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM)

            # Allow Port can quickly reuse to avoid print "Address already in use" when restart the connection.
            self.server_socket.setsockopt(socket.SOL_SOCKET,
                                          socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            print(f"TCP Server running on {self.host}:{self.port}...")
            return True

        except Exception as e:
            print(f"Failed to start server: {e}")
            return False


    def wait_for_esp32(self) -> bool:
        if not self.server_socket:
            print("Server socket is not initialized.")
            return False

        try:
            print("Waiting for ESP32 to connect...")
            self.client_socket, self.client_address = self.server_socket.accept()
            print(f"ESP32 Connected from: {self.client_address}")
            return True

        except Exception as e:
            print(f"Connection accept failed: {e}")
            return False


    def send_raw_message(self, message: str) -> bool:
        if not self.client_socket:
            print("No client connected.")
            return False

        try:
            if not message.endswith("\n"):
                message += "\n"

            self.client_socket.sendall(message.encode("utf-8"))
            print(f"Sent: {message.strip()}")
            return True

        except Exception as e:
            print(f"Failed to send data: {e}")
            self.close_client()
            return False


    def send_control_action(self, action: str) -> bool:
        return self.send_raw_message(f"CONTROL:{action}")


    def send_timestamp(self, timestamp: int) -> bool:
        return self.send_raw_message(f"TIMESTAMP:{timestamp}")


    def close_client(self):
        if self.client_socket:
            try:
                self.client_socket.close()
                print(f"Client connection closed: {self.client_address}")

            except Exception as e:
                print(f"Error closing client socket: {e}")

            finally:
                self.client_socket = None
                self.client_address = None


    def stop_server(self):
        self.close_client()

        if self.server_socket:
            try:
                self.server_socket.close()
                print("TCP Server stopped.")

            except Exception as e:
                print(f"Error closing server socket: {e}")

            finally:
                self.server_socket = None


if __name__ == "__main__":
    import time

    controller = ESP32Controller(host="0.0.0.0", port=8080)

    if controller.start_server():
        try:
            if controller.wait_for_esp32():
                controller.send_timestamp(int(time.time()))
                time.sleep(0.5)

                controller.send_control_action("START")
                time.sleep(2)

                controller.send_control_action("STOP")

        except KeyboardInterrupt:
            print("\nUser interrupted execution.")
        finally:
            controller.stop_server()