"""Entry point: python3 -m streamer"""

import logging
import signal
import sys

from .orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

orc = Orchestrator()


def _handle_signal(sig, frame):
    print("\nShutting down...")
    orc.stop()
    sys.exit(0)


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

orc.run()
