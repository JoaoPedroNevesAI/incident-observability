import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):

    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": getattr(record, "service", "unknown"),
            "level": record.levelname,
            "event": getattr(record, "event", "unknown"),
            "message": record.getMessage()
        }

        return json.dumps(log_data)


def configure_logger():
    logger = logging.getLogger()

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    logger.handlers.clear()
    logger.addHandler(handler)

    return logger