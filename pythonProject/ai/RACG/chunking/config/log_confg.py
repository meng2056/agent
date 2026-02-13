import logging
import sys


def setup_logging(name: str = "RACG_CORE") -> logging.Logger:
    logger_instance = logging.getLogger(name)

    if not logger_instance.handlers:
        logger_instance.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] '
            '[%(module)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger_instance.addHandler(handler)

    return logger_instance


logger = setup_logging()