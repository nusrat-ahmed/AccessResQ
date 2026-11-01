"""Optional lab relay bridge for AccessResQ NET.

Reads ONE JSON SOS payload per line from stdin or an attached serial receiver,
then sends it to an authenticated backend endpoint. It does NOT implement LoRa
RF, Bluetooth mesh, sensor firmware or rescue dispatch.

Usage:
  set ACCESSRESQ_RELAY_TOKEN=your-relay-token    (Windows cmd)
  python bridge/relay_gateway.py --stdin --url http://127.0.0.1:8000
  python -m pip install pyserial  # only if using --port
  python bridge/relay_gateway.py --port COM5 --baud 115200 --url http://127.0.0.1:8000

On every line, the sender MUST supply a consented SOSIn payload with client_id.
The gateway never logs the raw message or private contact information.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def transmit(line: str, base_url: str, token: str) -> None:
    try:
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError("Expected a JSON object")
        if not obj.get("consent"):
            raise ValueError("Consent is required")
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        if len(raw) > 8192:
            raise ValueError("Message exceeds 8192-byte limit")
        req = urllib.request.Request(
            base_url.rstrip("/") + "/api/relay/ingest",
            data=raw,
            headers={"X-Relay-Token": token, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.load(resp)
        print("Server accepted signal:", data.get("public_id"), "(not rescue dispatched)", flush=True)
    except (json.JSONDecodeError, ValueError, UnicodeError) as e:
        print("Invalid relay input:", str(e), file=sys.stderr, flush=True)
    except urllib.error.HTTPError as e:
        print("Server rejected relay packet; HTTP", e.code, file=sys.stderr, flush=True)
    except (urllib.error.URLError, TimeoutError) as e:
        print("Network unavailable; packet not delivered. Retry requires sender-side storage.", file=sys.stderr, flush=True)


def main():
    parser = argparse.ArgumentParser(description="AccessResQ lab-only JSON/serial-to-HTTP gateway")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--stdin", action="store_true", help="Read newline-delimited JSON from stdin")
    inputs.add_argument("--port", help="Serial receiver port, e.g. COM5 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    token = os.environ.get("ACCESSRESQ_RELAY_TOKEN")
    if not token:
        parser.error("Set ACCESSRESQ_RELAY_TOKEN in the environment")
    url = urlsplit(args.url)
    if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost"}):
        parser.error("Use HTTPS except for a local development server")
    if args.stdin:
        for line in sys.stdin:
            if line.strip():
                transmit(line, args.url, token)
    else:
        try:
            import serial
        except ImportError:
            parser.error("Install pyserial for a physical serial port: python -m pip install pyserial")
        with serial.Serial(args.port, args.baud, timeout=1) as port:
            print("Listening for JSON lines on serial receiver", flush=True)
            while True:
                line = port.readline()
                if line:
                    transmit(line.decode("utf-8", errors="replace").strip(), args.url, token)


if __name__ == "__main__":
    main()
