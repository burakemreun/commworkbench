import logging
import time

from commworkbench.constants import FRAME_TIMEOUT_SECS, RING_BUFFER_SIZE
from commworkbench.protocol_codec import ROLE_MSG_ID, ProtocolCodec

log = logging.getLogger(__name__)

SCAN = 0
HEADER = 1
PAYLOAD = 2
CHECKSUM = 3


class Parser:
    def __init__(self, protocol_config: dict):
        self._codec = ProtocolCodec(protocol_config)
        self._checksum_size = self._codec.checksum_size
        self._header_size = self._codec.header_size
        self._buf = bytearray(RING_BUFFER_SIZE)
        self._write_ptr = 0
        self._read_ptr = 0
        self._state = SCAN
        self._frame_start = 0
        self._msg_name: str | None = None
        self._msg_def: dict | None = None
        self._header_bytes = b""
        self._payload_buf = bytearray()
        self._skipped = bytearray()
        self._checksum_buf = bytearray()
        self._output: list[dict] = []
        self._last_feed_time = time.time()

        # one ID can belong to several messages once addressing is in play
        # (same command to two nodes), so candidates are kept as a list
        self._id_to_msg: dict[int, list[tuple[str, dict]]] = {}
        for name, msg_def in protocol_config.get("messages", {}).items():
            if msg_def.get("direction", "rx") == "rx":
                self._id_to_msg.setdefault(msg_def["id"], []).append((name, msg_def))

    def feed(self, data: bytes):
        now = time.time()
        if self._state != SCAN and (now - self._last_feed_time) > FRAME_TIMEOUT_SECS:
            log.debug("frame timeout, resetting to SCAN")
            self._reset_to_scan()
        self._last_feed_time = now

        for b in data:
            self._buf[self._write_ptr] = b
            self._write_ptr = (self._write_ptr + 1) % RING_BUFFER_SIZE

        self._process()

    def get_frames(self) -> list[dict]:
        frames = self._output[:]
        self._output.clear()
        return frames

    def _available(self) -> int:
        return (self._write_ptr - self._read_ptr) % RING_BUFFER_SIZE

    def _read_byte(self) -> int | None:
        if self._available() == 0:
            return None
        b = self._buf[self._read_ptr]
        self._read_ptr = (self._read_ptr + 1) % RING_BUFFER_SIZE
        return b

    def _peek_bytes(self, n: int) -> bytes | None:
        if self._available() < n:
            return None
        out = bytearray()
        ptr = self._read_ptr
        for _ in range(n):
            out.append(self._buf[ptr])
            ptr = (ptr + 1) % RING_BUFFER_SIZE
        return bytes(out)

    def _read_bytes(self, n: int) -> bytes:
        result = bytearray()
        for _ in range(n):
            b = self._read_byte()
            if b is None:
                break
            result.append(b)
        return bytes(result)

    def _reset_to_scan(self):
        self._read_ptr = (self._frame_start + 1) % RING_BUFFER_SIZE
        self._state = SCAN
        self._msg_name = None
        self._msg_def = None
        self._header_bytes = b""
        self._payload_buf.clear()
        self._checksum_buf.clear()

    def _payload_size(self) -> int:
        return self._codec.payload_size(self._msg_def)

    def _process(self):
        while True:
            avail = self._available()

            if self._state == SCAN:
                peek = self._peek_bytes(self._header_size)
                if peek is None:
                    self._flush_skipped()
                    break
                if not self._try_header(peek):
                    # header does not hold here: resync one byte at a time, keeping
                    # the bytes so the traffic log can show what came in
                    self._skipped.append(self._read_byte())

            elif self._state == HEADER:
                self._state = PAYLOAD

            elif self._state == PAYLOAD:
                needed = self._payload_size()
                if len(self._payload_buf) >= needed:
                    self._checksum_buf.clear()
                    self._state = CHECKSUM
                    continue
                to_read = min(avail, needed - len(self._payload_buf))
                if to_read > 0:
                    self._payload_buf.extend(self._read_bytes(to_read))
                if len(self._payload_buf) >= needed:
                    self._checksum_buf.clear()
                    self._state = CHECKSUM
                    continue
                break

            elif self._state == CHECKSUM:
                cs_size = self._checksum_size
                if cs_size == 0:
                    self._decode_and_emit()
                    continue
                if len(self._checksum_buf) >= cs_size:
                    self._decode_and_emit()
                    continue
                to_read = min(avail, cs_size - len(self._checksum_buf))
                if to_read > 0:
                    self._checksum_buf.extend(self._read_bytes(to_read))
                if len(self._checksum_buf) >= cs_size:
                    self._decode_and_emit()
                    continue
                break

    def _flush_skipped(self):
        if not self._skipped:
            return
        self._output.append({
            "type": "unknown",
            "raw_hex": bytes(self._skipped).hex(),
            "direction": "rx",
        })
        self._skipped.clear()

    def _try_header(self, peek: bytes) -> bool:
        """Accept the header at the read pointer, or report that it does not hold.

        A known message ID is not enough on its own: the same ID travels in both
        directions, so every role the header declares (sender, receiver, length)
        has to agree with the message before the frame is claimed.
        """
        header = self._codec.parse_header(peek)
        length_error = None
        for msg_name, msg_def in self._id_to_msg.get(header[ROLE_MSG_ID], ()):
            mismatch = self._codec.header_mismatch(msg_def, header)
            if mismatch is None:
                self._flush_skipped()
                self._frame_start = self._read_ptr
                self._header_bytes = peek
                self._read_ptr = (self._read_ptr + self._header_size) % RING_BUFFER_SIZE
                self._msg_name, self._msg_def = msg_name, msg_def
                self._payload_buf.clear()
                self._state = HEADER
                return True
            if "length" in mismatch and length_error is None:
                length_error = f"{msg_name}: {mismatch}"

        # addressing matched a known message but the declared length did not: that
        # is a real protocol error, not line noise - surface it, then resync
        if length_error is not None:
            self._flush_skipped()
            self._output.append({
                "type": "error",
                "message": length_error,
                "raw_hex": peek.hex(),
            })
            self._skipped.append(self._read_byte())
            return True
        return False

    def _decode_and_emit(self):
        frame_data = self._header_bytes + bytes(self._payload_buf) + bytes(self._checksum_buf)

        try:
            fields = self._codec.decode(self._msg_name, frame_data)
            self._output.append({
                "type": "frame",
                "msg_name": self._msg_name,
                "msg_id": self._msg_def["id"],
                "fields": fields,
                "raw_hex": frame_data.hex(),
                "direction": "rx",
            })
        except ValueError as e:
            self._output.append({
                "type": "error",
                "message": str(e),
                "raw_hex": frame_data.hex(),
            })
            self._read_ptr = (self._frame_start + 1) % RING_BUFFER_SIZE

        self._state = SCAN
        self._msg_name = None
        self._msg_def = None
        self._header_bytes = b""
        self._payload_buf.clear()
        self._checksum_buf.clear()
