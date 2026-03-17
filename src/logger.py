import logging
import sys

def setup_logging():
    logger = logging.getLogger("aishub2nmea")
    logger.setLevel(logging.DEBUG)  # change to INFO if too verbose

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger
