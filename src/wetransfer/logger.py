"""Module to create a specific logger for the whole package"""
import logging

LOGGER = logging.getLogger("wetransfer-python-sdk")
LOGGER.addHandler(logging.NullHandler())
