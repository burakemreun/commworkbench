import logging
import queue
import socket
import threading
import time

log = logging.getLogger(__name__)

PARITY_MAP = {"none": "N", "even": "E", "odd": "O", "mark": "M", "space": "S"}


class ConnectionManager:
    def __init__(self, conn_config: dict, frame_queue: queue.Queue):
        self._config = conn_config
        self._queue = frame_queue
        self._connected = False
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._socket: socket.socket | None = None
        self._server_socket: socket.socket | None = None
        self._serial = None
        self._lock = threading.Lock()

    @property
    def status_text(self) -> str:
        mode = self._config.get("mode", "tcp_client")
        if mode == "serial":
            s = self._config.get("serial", {})
            return f"{s.get('port', '?')}@{s.get('baud_rate', '?')}"
        if mode == "tcp_server":
            t = self._config.get("tcp", {})
            return f"0.0.0.0:{t.get('port', '?')} (server)"
        t = self._config.get("tcp", {})
        return f"{t.get('host', '?')}:{t.get('port', '?')}"

    def connect(self):
        self._stop_event.clear()
        mode = self._config.get("mode", "tcp_client")
        if mode == "tcp_client":
            self._start_thread(self._tcp_client_loop)
        elif mode == "tcp_server":
            self._start_thread(self._tcp_server_loop)
        elif mode == "serial":
            self._start_thread(self._serial_loop)
        else:
            log.error("unknown mode: %s", mode)

    def disconnect(self):
        self._stop_event.set()
        with self._lock:
            self._connected = False
            self._close_sockets()
        for t in self._threads:
            t.join(timeout=2)
        self._threads.clear()
        self._push_status(False, "Disconnected")

    def send(self, data: bytes):
        with self._lock:
            if not self._connected:
                log.warning("send on disconnected connection")
                return
            try:
                if self._socket:
                    self._socket.sendall(data)
                elif self._serial:
                    self._serial.write(data)
            except OSError as e:
                log.error("send failed: %s", e)
                self._connected = False
                self._push_status(False, f"Send error: {e}")

    def is_connected(self) -> bool:
        return self._connected

    def _start_thread(self, target):
        t = threading.Thread(target=target, daemon=True)
        self._threads.append(t)
        t.start()

    def _push_status(self, connected: bool, text: str):
        self._queue.put({"type": "status", "connected": connected, "text": text})

    def _push_data(self, raw: bytes):
        self._queue.put({"type": "data", "raw": raw})

    def _close_sockets(self):
        for s in (self._socket, self._server_socket):
            if s:
                try:
                    s.close()
                except OSError:
                    pass
        self._socket = None
        self._server_socket = None
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def _retry_wait(self):
        retry_ms = self._config.get("tcp", {}).get("retry_interval_ms", 3000)
        self._stop_event.wait(retry_ms / 1000.0)

    def _tcp_client_loop(self):
        cfg = self._config.get("tcp", {})
        host = cfg.get("host", "127.0.0.1")
        port = cfg.get("port", 8080)

        while not self._stop_event.is_set():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5.0)
                s.connect((host, port))
                s.settimeout(None)
                with self._lock:
                    self._socket = s
                    self._connected = True
                self._push_status(True, f"{host}:{port}")
                log.info("connected to %s:%d", host, port)
                self._read_loop(s)
            except OSError as e:
                if not self._stop_event.is_set():
                    log.warning("connection failed: %s", e)
                    self._push_status(False, f"Connection failed: {e}")
            finally:
                with self._lock:
                    self._connected = False
                    self._socket = None
            if not self._stop_event.is_set():
                self._push_status(False, "Reconnecting...")
                self._retry_wait()

    def _tcp_server_loop(self):
        cfg = self._config.get("tcp", {})
        port = cfg.get("port", 8080)

        while not self._stop_event.is_set():
            srv = None
            client = None
            try:
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(("0.0.0.0", port))
                srv.listen(1)
                srv.settimeout(5.0)
                self._server_socket = srv
                self._push_status(False, f"Listening on {port}")
                log.info("listening on port %d", port)
                client, addr = srv.accept()
                client.settimeout(None)
                with self._lock:
                    self._socket = client
                    self._connected = True
                self._push_status(True, f"{addr[0]}:{addr[1]} (server)")
                self._read_loop(client)
            except OSError as e:
                if not self._stop_event.is_set():
                    log.warning("server error: %s", e)
            finally:
                with self._lock:
                    self._connected = False
                    self._socket = None
                if srv:
                    try:
                        srv.close()
                    except OSError:
                        pass
                    self._server_socket = None
                if client:
                    try:
                        client.close()
                    except OSError:
                        pass
            if not self._stop_event.is_set():
                self._retry_wait()

    def _serial_loop(self):
        cfg = self._config.get("serial", {})
        parity = PARITY_MAP.get(cfg.get("parity", "none"), "N")

        while not self._stop_event.is_set():
            try:
                import serial
                ser = serial.Serial(
                    port=cfg.get("port", "COM1"),
                    baudrate=cfg.get("baud_rate", 115200),
                    bytesize=cfg.get("data_bits", 8),
                    stopbits=cfg.get("stop_bits", 1),
                    parity=parity,
                )
                with self._lock:
                    self._serial = ser
                    self._connected = True
                self._push_status(True, f"{cfg.get('port', 'COM1')}@{cfg.get('baud_rate', 115200)}")
                log.info("serial connected to %s", cfg.get("port"))
                self._serial_read_loop(ser)
            except Exception as e:
                if not self._stop_event.is_set():
                    log.warning("serial connection failed: %s", e)
                    self._push_status(False, f"Serial error: {e}")
            finally:
                with self._lock:
                    self._connected = False
                    self._serial = None
            if not self._stop_event.is_set():
                self._retry_wait()

    def _read_loop(self, sock: socket.socket):
        while not self._stop_event.is_set():
            try:
                data = sock.recv(4096)
                if not data:
                    log.info("connection closed by remote")
                    break
                self._push_data(data)
            except OSError as e:
                if not self._stop_event.is_set():
                    log.error("recv error: %s", e)
                break

    def _serial_read_loop(self, ser):
        while not self._stop_event.is_set():
            try:
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting)
                    if data:
                        self._push_data(data)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if not self._stop_event.is_set():
                    log.error("serial read error: %s", e)
                break

    @staticmethod
    def list_serial_ports() -> list[str]:
        try:
            from serial.tools.list_ports import comports
            return [p.device for p in comports()]
        except ImportError:
            log.warning("pyserial not installed")
            return []
