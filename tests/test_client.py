"""Module that implements tests for wetransfer client module."""
import os
import re
import mock
import logging
import tempfile
from unittest import skip, main, TestCase
from wetransfer.client import WTApiClient
from wetransfer.logger import LOGGER
from wetransfer.transfer import Transfer


class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs."""

    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def reset(self):
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': [],
        }


class FakeResponse(object):
    """
    Mock response object from the different API calls that we do inside Item
    classes
    """
    def __init__(self, ok=True, json=None):
        self.ok = ok
        if json is None:
            json = {"token": "dummy_token"}
        self.json_res = json

    def json(self):
        return self.json_res


class TestTransfer(TestCase):
    """Test class to host main tests for Transfer class in client package."""
    def setUp(self):
        self.key = "dummy_key"
        self.server = "dummy_server"
        self.client = WTApiClient(**{"key": self.key, "server": self.server})

        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)

    def test_init(self):
        """
        Tests the init method of the class and checks if needed properties
        are set after we create the object.
        """
        self.assertEqual(self.client.server, self.server)
        self.assertEqual(self.client.key, self.key)

    def test_authorize_fail(self):
        """
        Tests the autorize method of the class in case Authorize API call fails and
        we return False.
        """
        with mock.patch('wetransfer.api_requests.Authorize.create') as mock_create:
            mock_create.return_value = FakeResponse(ok=False)
            r = self.client.authorize()
            self.assertFalse(r)
            self.assertEqual(
                "Failed authorizing",
                self.mock_handler.messages["error"][0]
            )

    def test_authorize_fail1(self):
        """
        Tests the autorize method of the class in case Authorize API call succeeds
        but there is no "token" keyword in response.
        """
        with mock.patch('wetransfer.api_requests.Authorize.create') as mock_create:
            mock_create.return_value = FakeResponse(ok=True, json={})
            r = self.client.authorize()
            self.assertFalse(r)
            self.assertEqual(
                "Expected 'token' in Authorize json response",
                self.mock_handler.messages["error"][0]
            )

    def test_authorize_success(self):
        """
        Tests the autorize method of the class in case Authorize API call succeeds
        and json response is valid and we return True.
        """
        with mock.patch('wetransfer.api_requests.Authorize.create') as mock_create:
            mock_create.return_value = FakeResponse(ok=True)
            r = self.client.authorize()
            self.assertTrue(r)
            self.assertEqual(
                "Successfully authorized",
                self.mock_handler.messages["info"][0]
            )

    def test_create_success(self):
        """
        Tests the create method of the class in cases where everything goes well and
         we return True.
        """
        with mock.patch('wetransfer.transfer.Transfer.create') as mock_create:
            mock_create.return_value = True
            r = self.client.create_transfer()
            self.assertTrue(isinstance(r, Transfer))
            self.assertEqual(r.name, "WT Transfer")

    def test_create_success1(self):
        """
        Tests the create method of the class in cases where everything goes well
        and we specify a different name than the default for the Transfer
        """
        with mock.patch('wetransfer.transfer.Transfer.create') as mock_create:
            mock_create.return_value = True
            r = self.client.create_transfer(transfer_name="Dummy Transfer")
            self.assertTrue(isinstance(r, Transfer))
            self.assertEqual(r.name, "Dummy Transfer")

    def test_create_fail(self):
        """
        Tests the create method of the class in cases where Transfer API call fails
        and we return None.
        """
        with mock.patch('wetransfer.transfer.Transfer.create') as mock_create:
            mock_create.return_value = None
            r = self.client.create_transfer()
            self.assertIsNone(r)


if __name__ == '__main__':
    main()
