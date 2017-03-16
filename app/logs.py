
import sys
import logging
import logging.config
import os
import io
import yaml

CONFIG_PATH = 'loggers.yaml'
DEFAULT_FORMAT = '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"'


def load_config(path=CONFIG_PATH):
    if path and os.path.exists(path):
        with io.open(path) as f:
            conf = f.read()
        logging.config.dictConfig(yaml.load(conf))


class StdHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)

        if record.levelno >= logging.WARNING:
            stream = sys.stderr
        else:
            stream = sys.stdout

        stream.write(msg)
        stream.write('\n')
        self.flush()


def set_basic_config():
    logging.basicConfig(level=logging.DEBUG)


def add_std_handler(name='', level='DEBUG'):
    level = level.upper()
    logger = logging.getLogger(name)
    h = StdHandler()
    h.setLevel(getattr(logging, level))
    logger.addHandler(h)


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger
