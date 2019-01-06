"""Module that implements tests for wetransfer transfer module."""
import os
import re
import mock
import logging
import tempfile
from unittest import skip, main, TestCase
from wetransfer.transfer import Transfer
from wetransfer.items import File, Link
from wetransfer.logger import LOGGER


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
    def __init__(self, ok=True):
        self.ok = ok

    def json(self):
        return {"id": "dummy_id", "shortened_url": "dummy_url"}


class TestTransfer(TestCase):
    """Test class to host main tests for Transfer class in transfer package."""
    def setUp(self):
        self.key = "dummy_key"
        self.token = "dummy_token"
        self.server = "dummy_server"
        self.name = "Dummy Transfer"
        self.transfer = Transfer(**{
            "key": self.key, "token": self.token, "server": self.server, "name": self.name
        })

        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)

    def test_init(self):
        """
        Tests the init method of the class and checks if needed properties
        are set after we create the object.
        """
        self.assertEqual(
            self.transfer.client_options,
            {"key": self.key, "token": self.token, "server": self.server, "name": "Dummy Transfer"}
        )
        self.assertEqual(self.transfer.transfer_id, None)
        self.assertEqual(self.transfer.transfer_items, [])
        self.assertEqual(self.transfer.transfer_files, [])

    def test_create_success(self):
        """
        Tests the create function when the CreateTransfer API call succeeded
        and we returned True.
        """
        res = FakeResponse()
        with mock.patch('wetransfer.api_requests.CreateTransfer.create') as mock_create:
            mock_create.return_value = res
            r = self.transfer.create()
            self.assertEqual(
                "Successfully created new transfer",
                self.mock_handler.messages["info"][0]
            )
            self.assertEqual(self.transfer.transfer_id, "dummy_id")
            self.assertEqual(self.transfer.shortened_url, "dummy_url")
            self.assertTrue(r)

    def test_create_fail(self):
        """
        Tests the create function when the CreateTransfer API call failed
        and we returned False.
        """
        res = FakeResponse(ok=False)
        with mock.patch('wetransfer.api_requests.CreateTransfer.create') as mock_create:
            mock_create.return_value = res
            r = self.transfer.create()
            self.assertEqual(
                "Failed creating new transfer",
                self.mock_handler.messages["error"][0]
            )
            # None of the below properties should be set
            self.assertEqual(self.transfer.transfer_id, None)
            self.assertFalse(getattr(self.transfer, "shortened_url", False))

            self.assertFalse(r)

    def test_validate_add_items_response_success(self):
        """
        Tests the `validate_add_items` method in cases where everything goes
        fine.
        """
        add_items_response = [
            {
                "content_identifier": "file",
                "id": "dummy_id",
                "meta": {"multipart_parts": "dummy", "multipart_upload_id": "dummy"}
            },
            {
                "content_identifier": "web_content",
                "id": "dummy_id",
                "meta": {"multipart_parts": "dummy", "multipart_upload_id": "dummy"}
            },
        ]
        fake_res = FakeAddItemsResponse(ok=True, response=add_items_response)
        self.transfer.transfer_items = add_items_response
        res = self.transfer.validate_add_items_response(fake_res)
        self.assertTrue(res)

    def test_validate_add_items_response_fail1(self):
        """
        Tests the `validate_add_items` method in cases where `AddItems` API
        call has failed and we return False.
        """
        add_items_response = []
        fake_res = FakeAddItemsResponse(ok=False, response=add_items_response)
        res = self.transfer.validate_add_items_response(fake_res)
        self.assertFalse(res)
        self.assertEqual(
            "Failed to add items: [] to transfer None",
            self.mock_handler.messages["error"][0]
        )

    def test_validate_add_items_response_fail2(self):
        """
        Tests the `validate_add_items` method in cases where response has more
        items than the ones we send.
        """
        add_items_response = [1, 2]
        fake_res = FakeAddItemsResponse(ok=True, response=add_items_response)
        self.transfer.transfer_items = add_items_response + [3]
        res = self.transfer.validate_add_items_response(fake_res)
        self.assertFalse(res)
        self.assertEqual(
            "Add items API call didn't return same number of items (2) than what we sent (3)",
            self.mock_handler.messages["error"][0]
        )


class FakeAddItemsResponse(object):
    """
    Mock response object from the different API calls that we do inside Item
    classes
    """
    def __init__(self, ok=True, response=[]):
        self.ok = ok
        self.response = response

    def json(self):
        return self.response


class TestTransferAddItems(TestCase):
    """
    Test class to host all tests for 'add_items' method of Transfer class in transfer
    package.
    """

    def setUp(self):
        self.key = "dummy_key"
        self.token = "dummy_token"
        self.server = "dummy_server"
        self.name = "Dummy Transfer"
        self.transfer = Transfer(**{
            "key": self.key, "token": self.token, "server": self.server, "name": self.name
        })

        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)

        self.mock_add_items = mock.patch(
            "wetransfer.api_requests.AddItems.create",
        ).start()
        self.mock_upload_part = mock.patch(
            "wetransfer.transfer.Transfer.upload_items",
        ).start()
        self.mock_validate_add_items = mock.patch(
            "wetransfer.transfer.Transfer.validate_add_items_response",
        ).start()

    def test_add_items1(self):
        """
        Tests the usecase where response of AddItems API call is not valid and
        validate method returns false.
        """
        items = [1, 2]
        self.mock_validate_add_items.return_value = False
        self.mock_upload_part.return_value = True
        self.mock_add_items.return_value = None
        r = self.transfer.add_items(items)
        self.assertFalse(r)
        self.assertEqual(len(self.transfer.transfer_items), 2)
        self.assertEqual(len(self.transfer.transfer_files), 0)

    def test_add_items2(self):
        """
        Tests the usecase where we have a valid response and we return
        True."""
        temp_file1 = tempfile.NamedTemporaryFile()
        f1 = File(temp_file1.name)
        temp_file2 = tempfile.NamedTemporaryFile()
        f2 = File(temp_file2.name)
        dummy_url1 = "http://dummy.url"
        dummy_title1 = "Dummy Title"
        link1 = Link(dummy_url1, dummy_title1)
        dummy_url2 = "http://dummy.url"
        dummy_title2 = "Dummy Title"
        link2 = Link(dummy_url2, dummy_title2)
        items = [f1, link1, f2, link2]
        add_items_response = [
            {
                "content_identifier": "file",
                "id": "dummy_id1",
                "meta": {"multipart_parts": "dummy", "multipart_upload_id": "dummy"}
            },
            {
                "content_identifier": "web_content",
                "id": "dummy_id2",
                "meta": {"multipart_parts": "dummy", "multipart_upload_id": "dummy"}
            },
            {
                "content_identifier": "file",
                "id": "dummy_id3",
                "meta": {"multipart_parts": "dummy", "multipart_upload_id": "dummy"}
            },

            {
                "content_identifier": "web_content",
                "id": "dummy_id4",
                "meta": {"multipart_parts": "dummy", "multipart_upload_id": "dummy"}
            },
        ]
        self.mock_upload_part.return_value = True
        self.mock_add_items.return_value = FakeAddItemsResponse(
            ok=True, response=add_items_response)
        r = self.transfer.add_items(items)
        self.assertTrue(r)
        self.assertTrue(
            self.mock_handler.messages["info"][0].startswith(
                "Successfully added items:")
        )
        self.assertEqual(len(self.transfer.transfer_items), 4)
        self.assertEqual(len(self.transfer.transfer_files), 2)
        self.assertTrue(isinstance(self.transfer.transfer_items[0], File))
        self.assertTrue(isinstance(self.transfer.transfer_items[2], File))
        self.assertTrue(isinstance(self.transfer.transfer_items[1], Link))
        self.assertTrue(isinstance(self.transfer.transfer_items[3], Link))
        self.assertTrue(self.check_items())
        self.assertEqual(self.mock_upload_part.call_count, 1)

    def check_items(self):
        """Checks if File objects properties are set as expected"""
        client_options = {
            "token": "dummy_token", "key": "dummy_key",
            "server": "dummy_server", "name": "Dummy Transfer"
        }
        for index, item in enumerate(self.transfer.transfer_items):
            if item.content_identifier == "web_content":
                continue
            self.assertEqual(item.id, "dummy_id{}".format(index + 1))
            self.assertEqual(item.transfer_id, self.transfer.transfer_id)
            self.assertEqual(item.client_options, client_options)
            self.assertEqual(item.multipart_parts, "dummy")
            self.assertEqual(item.multipart_upload_id, "dummy")

        return True

    def tearDown(self):
        mock.patch.stopall()


if __name__ == "__main__":
    main()
