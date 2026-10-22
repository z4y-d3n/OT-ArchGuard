"""Opt-in verification guard inherited by Python subprocesses; never shipped in the app."""

import os
import sys

if os.environ.get("OTARCHGUARD_OFFLINE_CHECK") == "1":

    def _deny_network(event: str, arguments: tuple[object, ...]) -> None:
        if event in {
            "socket.__new__",
            "socket.connect",
            "socket.bind",
            "socket.getaddrinfo",
            "socket.gethostbyname",
            "http.client.connect",
            "urllib.Request",
        }:
            raise RuntimeError("OFFLINE_GUARD: network operation denied")

    sys.addaudithook(_deny_network)
