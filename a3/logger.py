import logging
import os
import sys

# Create a logger
def get_logger(name, level='INFO'):
    log = logging.getLogger(name)
    log.setLevel(level)
    log.handlers.clear()
    formatter = logging.Formatter('%(message)s')
    fh = logging.FileHandler('{}.out'.format(name), 'w', 'utf-8')
    fh.setFormatter(formatter)
    log.addHandler(fh)
    return log