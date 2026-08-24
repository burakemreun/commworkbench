#!/usr/bin/env python3
"""Device simulator for CommWorkbench.

Listens on TCP, receives TX messages, responds with RX messages.
Usage: python simulator.py [config_dir]
Default config: configs/_example
"""

import json
import logging
import random
import socket
import struct
import sys
from pathlib import Path

from commworkbench.protocol_codec import ProtocolCodec

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("simulator")

HOST = "127.0.0.1"
PORT = 8080


def load_config(config_dir: Path) -> dict:
    protocol_path = config_dir / "protocol.json"
    with open(protocol_path) as f:
        return json.load(f)


def find_tx_rx_messages(protocol_config: dict) -> tuple[str | None, str | None]:
    tx_name = None
    rx_name = None
    for name, msg_def in protocol_config.get("messages", {}).items():
        direction = msg_def.get("direction", "")
        if direction == "tx":
            tx_name = name
        elif direction == "rx":
            rx_name = name
    return tx_name, rx_name


def calc_field_size(field_def: dict) -> int:
    ft = field_def["type"]
    if ft in ("uint8", "int8"):
        return 1
    if ft in ("uint16", "int16"):
        return 2
    if ft in ("uint32", "int32", "float32"):
        return 4
    if ft in ("uint64", "int64", "float64"):
        return 8
    if ft == "enum":
        underlying = field_def.get("enum_underlying", "uint16")
        return 2 if underlying in ("uint16", "int16") else 1
    if ft == "bitfield":
        bits = field_def["bitfield"]["total_bits"]
        if bits <= 8:
            return 1
        if bits <= 16:
            return 2
        return 4
    raise ValueError(f"unknown type: {ft}")


def calc_frame_size(codec: ProtocolCodec, msg_name: str) -> int:
    msg_def = codec.messages[msg_name]
    payload_size = sum(calc_field_size(f) for f in msg_def["fields"])
    return codec.id_size + payload_size + codec.checksum_size


def generate_response(rx_name: str, request_fields: dict) -> dict:
    device_id = request_fields.get("device_id", 0)
    return {
        "device_id": device_id,
        "temperature": round(random.uniform(18.0, 35.0), 2),
        "humidity": random.randint(20, 90),
        "mode": random.choice(["IDLE", "ACTIVE"]),
        "battery_level": random.randint(10, 100),
    }


def recv_exact(sock: socket.socket, n: int) -> bytes | None:
    buf = bytearray()
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except (ConnectionResetError, OSError):
            return None
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def handle_client(conn: socket.socket, addr: tuple, codec: ProtocolCodec,
                  tx_name: str, rx_name: str):
    log.info("Client connected: %s:%d", *addr)

    tx_size = calc_frame_size(codec, tx_name)
    rx_size = calc_frame_size(codec, rx_name)
    log.info("Expecting %d-byte TX frames (%s)", tx_size, tx_name)
    log.info("Sending %d-byte RX frames (%s)", rx_size, rx_name)

    try:
        while True:
            data = recv_exact(conn, tx_size)
            if data is None:
                log.info("Client disconnected: %s:%d", *addr)
                break

            try:
                fields = codec.decode(tx_name, data)
                log.info("RX %s: %s", tx_name, fields)

                resp_fields = generate_response(rx_name, fields)
                log.info("TX %s: %s", rx_name, resp_fields)

                response = codec.encode(rx_name, resp_fields)
                conn.sendall(response)
            except ValueError as e:
                log.warning("Decode error: %s (raw: %s)", e, data.hex())
    finally:
        conn.close()


def main():
    config_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("configs/_example")
    log.info("Loading config from: %s", config_dir)

    protocol_config = load_config(config_dir)
    codec = ProtocolCodec(protocol_config)
    tx_name, rx_name = find_tx_rx_messages(protocol_config)

    if not tx_name or not rx_name:
        log.error("Config must have one 'tx' and one 'rx' message")
        log.error("Found tx=%s, rx=%s", tx_name, rx_name)
        sys.exit(1)

    log.info("Protocol: %s v%s", protocol_config["protocol"]["name"],
             protocol_config["protocol"]["version"])
    log.info("TX message: %s, RX message: %s", tx_name, rx_name)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    log.info("Listening on %s:%d", HOST, PORT)

    try:
        while True:
            conn, addr = srv.accept()
            handle_client(conn, addr, codec, tx_name, rx_name)
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        srv.close()


if __name__ == "__main__":
    main()
