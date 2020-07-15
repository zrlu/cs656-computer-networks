import logging
import os
import sys

# returns a logger
def get_logger(name, level='INFO', stdout=True):
    log = logging.getLogger(name)
    log.setLevel(level)
    log.handlers.clear()
    formatter = logging.Formatter('%(message)s')
    fh = logging.FileHandler('{}.txt'.format(name), 'a', 'utf-8')
    fh.setFormatter(formatter)
    log.addHandler(fh)

    # print to stdout
    if stdout:
        stdoutHandler = logging.StreamHandler(sys.stdout)
        stdoutHandler.setFormatter(formatter)
        log.addHandler(stdoutHandler)
    return log