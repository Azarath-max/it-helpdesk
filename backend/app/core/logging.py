import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Configure stdout logging once per process."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
