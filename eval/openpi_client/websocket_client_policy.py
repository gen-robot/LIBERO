import logging
import time
from typing import Dict, Optional, Tuple

from typing_extensions import override
import websockets.sync.client
from websockets.exceptions import ConnectionClosedError

from openpi_client import base_policy as _base_policy
from openpi_client import msgpack_numpy


class WebsocketClientPolicy(_base_policy.BasePolicy):
    """Implements the Policy interface by communicating with a server over websocket.

    See WebsocketPolicyServer for a corresponding server implementation.
    """

    def __init__(self, host: str = "0.0.0.0", port: Optional[int] = None, api_key: Optional[str] = None) -> None:
        if host.startswith("ws"):
            self._uri = host
        else:
            self._uri = f"ws://{host}"
        if port is not None:
            self._uri += f":{port}"
        self._packer = msgpack_numpy.Packer()
        self._api_key = api_key
        self._ws, self._server_metadata = self._wait_for_server()

    def get_server_metadata(self) -> Dict:
        return self._server_metadata

    def _wait_for_server(self) -> Tuple[websockets.sync.client.ClientConnection, Dict]:
        logging.info(f"Waiting for server at {self._uri}...")
        while True:
            try:
                headers = {"Authorization": f"Api-Key {self._api_key}"} if self._api_key else None
                conn = websockets.sync.client.connect(
                    self._uri,
                    compression=None,
                    max_size=None,
                    additional_headers=headers,
                    # Increase timeouts to be more tolerant of slow server startup / shutdown.
                    open_timeout=300,
                    close_timeout=300,
                )
                metadata = msgpack_numpy.unpackb(conn.recv())
                return conn, metadata
            except (ConnectionRefusedError, EOFError) as exc:
                # Server may close the TCP connection during handshake under load;
                # treat this the same as "not ready yet" and retry after a short delay.
                logging.info("Still waiting for server ({type(exc).__name__}: {exc})...")
                time.sleep(5)

    @override
    def infer(self, obs: Dict) -> Dict:  # noqa: UP006
        """Send one inference request, with automatic reconnect & up to 10 retries.

        This makes parallel evaluation more robust to transient keepalive
        timeouts and short connectivity hiccups.
        """
        data = self._packer.pack(obs)

        last_exc: BaseException | None = None
        max_attempts = 10

        for attempt in range(1, max_attempts + 1):
            try:
                self._ws.send(data)
                response = self._ws.recv()
                if isinstance(response, str):
                    raise RuntimeError(f"Error in inference server:\n{response}")
                return msgpack_numpy.unpackb(response)
            except ConnectionClosedError as exc:
                # Server closed the connection (often due to keepalive timeout).
                # Reconnect once and retry, up to max_attempts times.
                last_exc = exc
                logging.warning(
                    "WebSocket connection closed during infer (attempt %d/%d): %s",
                    attempt,
                    max_attempts,
                    exc,
                )

                # Best-effort close of current connection.
                try:
                    self._ws.close()
                except Exception:
                    pass

                # Attempt to reconnect before next retry.
                try:
                    self._ws, self._server_metadata = self._wait_for_server()
                except Exception as reconnect_exc:  # pragma: no cover - defensive
                    last_exc = reconnect_exc
                    logging.warning(
                        "Failed to reconnect WebSocket (attempt %d/%d): %s",
                        attempt,
                        max_attempts,
                        reconnect_exc,
                    )

                # Small backoff to avoid tight retry loop under persistent failure.
                time.sleep(min(1.0 * attempt, 5.0))

        raise RuntimeError("WebSocket infer failed after 10 attempts") from last_exc

    @override
    def reset(self) -> None:
        pass
