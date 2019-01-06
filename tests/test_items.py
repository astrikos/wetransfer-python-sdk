"""Module that implements tests for wetransfer items module."""
import os
import re
import six
import mock
import logging
import tempfile
from unittest import skip, main, TestCase

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
        return {"upload_url": "test_dummy_url"}


class TestFileItem(TestCase):
    """Test class to host main tests for File class in items package."""
    def setUp(self):
        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)
        self.temp_file = tempfile.NamedTemporaryFile()
        with open(self.temp_file.name, 'w') as f:
            f.write("123456")

    def test_init(self):
        """
        Tests the init method of the class and checks if needed properties
        are set after we create the object.
        """
        item = File(self.temp_file.name)

        self.assertEqual(item.filename, os.path.split(self.temp_file.name)[1])
        self.assertEqual(item.filesize, 6)
        self.assertEqual(item.content_identifier, "file")
        self.assertEqual(item.local_identifier, self.temp_file.name)

    def test_serialize(self):
        """
        Tests the serialize method of the class and checks if serialize
        output is returned as expected.
        """
        item = File(self.temp_file.name)
        expected_value = {
            "filename": item.filename,
            "filesize": 6,
            "content_identifier": item.content_identifier,
            "local_identifier": item.local_identifier[-34:]
        }
        self.assertEqual(item.serialize(), expected_value)

    def test_load_info(self):
        """
        Tests the 'load_info' method of the class and checks needed properties
        are set as expected.
        """
        item = File(self.temp_file.name)
        kwargs = {
            "id": 1, "transfer_id": 1,
            "client_options": {},
            "multipart_parts": [],
            "multipart_upload_id": [],
        }
        item.load_info(**kwargs)
        self.assertEqual(item.id, 1)
        self.assertEqual(item.transfer_id, 1)
        self.assertEqual(item.client_options, {})
        self.assertEqual(item.multipart_parts, [])
        self.assertEqual(item.multipart_upload_id, [])

    def test_str(self):
        """Tests the '__str__' representation of the objects of File class"""
        item = File(self.temp_file.name)
        regexp = (
            r"Transfer item, file type, with size 6, name \S+, and local path"
            r" \S+, has None multi parts"
        )
        pattern = re.compile(regexp)
        is_match = pattern.match(str(item))
        self.assertTrue(is_match)


class TestFileUpload(TestCase):
    """
    Test class to host all tests for 'upload' method of File class in items
    package.
    """
    def setUp(self):
        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)

        self.mock_finish_upload = mock.patch(
            "wetransfer.api_requests.FinishUpload.create",
        ).start()
        self.mock_upload_part = mock.patch(
            "wetransfer.items.File.upload_part",
        ).start()

        self.temp_file = tempfile.NamedTemporaryFile()
        with open(self.temp_file.name, 'w') as f:
            f.write("123456")

        self.item = File(self.temp_file.name)
        self.item.client_options = {}
        self.item.id = 1

    def test_upload_all_success(self):
        """
        Tests the usecase where everything is fine, there is no errors and the
        method returns True
        """
        r = FakeResponse()
        self.mock_finish_upload.return_value = r
        self.mock_upload_part.return_value = True
        self.item.CHUNK_SIZE = 2
        res = self.item.upload()
        self.assertEqual(self.mock_finish_upload.call_count, 1)
        self.assertEqual(self.mock_upload_part.call_count, 3)
        expected_call_list = [
            mock.call('12', 1), mock.call('34', 2), mock.call('56', 3),
        ]
        self.assertEqual(
            self.mock_upload_part.call_args_list,
            expected_call_list
        )
        self.assertEqual(
            "Successfully closed upload for item id: 1",
            self.mock_handler.messages["info"][0]
        )
        self.assertTrue(res)

    def test_upload_part_only_success(self):
        """
        Tests the usecase where the FinishUpload API call failed and we exit
        with False
        """
        r = FakeResponse(ok=False)
        self.mock_finish_upload.return_value = r
        self.mock_upload_part.return_value = True
        self.item.CHUNK_SIZE = 2
        res = self.item.upload()
        self.assertEqual(self.mock_finish_upload.call_count, 1)
        self.assertEqual(self.mock_upload_part.call_count, 3)
        expected_call_list = [
            mock.call('12', 1), mock.call('34', 2), mock.call('56', 3),
        ]
        self.assertEqual(
            self.mock_upload_part.call_args_list,
            expected_call_list
        )
        self.assertEqual(
            "Failed closing upload for item id: 1",
            self.mock_handler.messages["error"][0]
        )
        self.assertFalse(res)

    def test_upload_failure(self):
        """
        Tests the usecase where the FinishUpload API call and the upload
        individual parts failed and we exit with False
        """
        r = FakeResponse(ok=False)
        self.mock_finish_upload.return_value = r
        self.mock_upload_part.return_value = False
        self.item.CHUNK_SIZE = 2
        res = self.item.upload()
        self.assertEqual(self.mock_finish_upload.call_count, 0)
        self.assertEqual(self.mock_upload_part.call_count, 1)
        expected_call_list = [mock.call('12', 1)]
        self.assertEqual(
            self.mock_upload_part.call_args_list,
            expected_call_list
        )
        self.assertFalse(res)


class TestFileUploadChunks(TestCase):
    """
    Test class to host all tests for reading part in chunks inside the
    upload method of File class in items package.
    """
    def setUp(self):
        finish_response = FakeResponse(ok=True)

        mock.patch(
            "wetransfer.api_requests.FinishUpload.create",
            response_value=finish_response
        ).start()
        self.mock_upload_part = mock.patch(
            "wetransfer.items.File.upload_part",
            response_value=True
        ).start()

        self.temp_file = tempfile.NamedTemporaryFile()
        with open(self.temp_file.name, 'w') as f:
            f.write("123456")

        self.item = File(self.temp_file.name)
        self.item.client_options = {}
        self.item.id = 1

    def tearDown(self):
        mock.patch.stopall()

    def test_upload_chunks(self):
        """
        Tests the usecase where chunk size is smaller than size of file.
        """
        self.item.CHUNK_SIZE = 2
        r = self.item.upload()
        self.assertEqual(self.mock_upload_part.call_count, 3)
        expected_call_list = [
            mock.call('12', 1), mock.call('34', 2), mock.call('56', 3),
        ]
        self.assertEqual(
            self.mock_upload_part.call_args_list,
            expected_call_list
        )
        self.assertTrue(r)

    def test_upload_chunks1(self):
        """
        Tests the usecase where chunk size is smaller than size of file.
        """
        self.item.CHUNK_SIZE = 1
        r = self.item.upload()
        self.assertEqual(self.mock_upload_part.call_count, 6)
        expected_call_list = [
            mock.call('1', 1), mock.call('2', 2), mock.call('3', 3),
            mock.call('4', 4), mock.call('5', 5), mock.call('6', 6)
        ]
        self.assertEqual(
            self.mock_upload_part.call_args_list,
            expected_call_list
        )
        self.assertTrue(r)

    def test_upload_chunks2(self):
        """
        Tests the usecase where chunk size is smaller than size of file.
        """
        self.item.CHUNK_SIZE = 3
        r = self.item.upload()
        self.assertEqual(self.mock_upload_part.call_count, 2)
        expected_call_list = [mock.call('123', 1), mock.call('456', 2)]
        self.assertEqual(
            self.mock_upload_part.call_args_list,
            expected_call_list
        )
        self.assertTrue(r)

    def test_upload_chunks3(self):
        """
        Tests the usecase where chunk size is smaller than size of file.
        """
        self.item.CHUNK_SIZE = 4
        r = self.item.upload()
        self.assertEqual(self.mock_upload_part.call_count, 2)
        expected_call_list = [mock.call('1234', 1), mock.call('56', 2)]
        self.assertEqual(
            self.mock_upload_part.call_args_list,
            expected_call_list
        )
        self.assertTrue(r)

    def test_upload_chunks4(self):
        """
        Tests the usecase where chunk size is smaller than size of file.
        """
        self.item.CHUNK_SIZE = 5
        r = self.item.upload()
        self.assertEqual(self.mock_upload_part.call_count, 2)
        expected_call_list = [mock.call('12345', 1), mock.call('6', 2)]
        self.assertEqual(
            self.mock_upload_part.call_args_list,
            expected_call_list
        )
        self.assertTrue(r)

    def test_upload_chunks5(self):
        """
        Tests the usecase where chunk size is equal to the size of file.
        """
        self.item.CHUNK_SIZE = 6
        r = self.item.upload()
        self.mock_upload_part.assert_called_once_with(
          "123456", 1
        )
        self.assertTrue(r)

    def test_upload_chunks6(self):
        """
        Tests the usecase where chunk size is bigger than size of file.
        """
        self.item.CHUNK_SIZE = 7
        r = self.item.upload()
        self.mock_upload_part.assert_called_once_with(
          "123456", 1
        )
        self.assertTrue(r)

    def test_upload_chunks7(self):
        """
        Tests the usecase where chunk size is bigger than size of file.
        """
        self.item.CHUNK_SIZE = 30
        r = self.item.upload()
        self.mock_upload_part.assert_called_once_with(
          "123456", 1
        )
        self.assertTrue(r)


class TestFileUploadPart(TestCase):
    """
    Test class to host all tests for  'upload_part' method of File class in
    items package.
    """

    def setUp(self):
        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)
        finish_response = FakeResponse(ok=True)
        self.mock_get_upload_url = mock.patch(
            "wetransfer.api_requests.GetUploadURL.create"
        ).start()
        self.mock_upload_part = mock.patch(
            "wetransfer.api_requests.UploadPart.create"
        ).start()
        self.temp_file = tempfile.NamedTemporaryFile()
        with open(self.temp_file.name, 'w') as f:
            f.write("123456")
        self.item = File(self.temp_file.name)
        self.item.client_options = {}
        self.item.id = 1

    def test_upload_part1(self):
        """
        Tests the usecase where everything is fine and there is no errors from
        the two API calls
        """
        r = FakeResponse(ok=True)
        self.mock_get_upload_url.return_value = r
        self.mock_upload_part.return_value = r
        res = self.item.upload_part("as", 1)

        self.assertEqual(self.mock_get_upload_url.call_count, 1)
        self.assertEqual(self.mock_upload_part.call_count, 1)
        self.assertEqual(
            "Successfully fetched url for item id: 1, upload_id: None, part_number: 1",
            self.mock_handler.messages["info"][0]
        )
        self.assertEqual(
            "Successfully PUT-ed part-number 1 for item id: 1",
            self.mock_handler.messages["info"][1]
        )
        self.assertTrue(res)

    def test_upload_part2(self):
        """
        Tests the usecase where GetUploadURL call returns an error and the
        method needs to exit with an error
        """
        r_true = FakeResponse(ok=True)
        r_false = FakeResponse(ok=False)
        self.mock_get_upload_url.return_value = r_false
        self.mock_upload_part.return_value = r_true
        res = self.item.upload_part("as", 1)

        self.assertEqual(self.mock_get_upload_url.call_count, 1)
        self.assertEqual(self.mock_upload_part.call_count, 0)
        self.assertEqual(
            "Failed fetching url for item id: 1, upload_id: None, part_number: 1",
            self.mock_handler.messages["error"][0]
        )
        self.assertFalse(res)

    def test_upload_part3(self):
        """
        Tests the usecase where UploadPart call returns an error and the method
        needs to exit with an error
        """
        r_true = FakeResponse(ok=True)
        r_false = FakeResponse(ok=False)
        self.mock_get_upload_url.return_value = r_true
        self.mock_upload_part.return_value = r_false
        res = self.item.upload_part("as", 1)

        self.assertEqual(self.mock_get_upload_url.call_count, 1)
        self.assertEqual(self.mock_upload_part.call_count, 1)
        self.assertEqual(
            "Successfully fetched url for item id: 1, upload_id: None, part_number: 1",
            self.mock_handler.messages["info"][0]
        )
        self.assertEqual(
            "Failed PUT-ing part-number 1 for item id: 1",
            self.mock_handler.messages["error"][0]
        )
        self.assertFalse(res)

    def test_upload_part4(self):
        """
        Tests the usecase where both GetUploadURL and UploadPart calls return
        an error and the method needs to exit with an error
        """
        r = FakeResponse(ok=False)
        self.mock_get_upload_url.return_value = r
        self.mock_upload_part.return_value = r
        res = self.item.upload_part("as", 1)

        self.assertEqual(self.mock_get_upload_url.call_count, 1)
        self.assertEqual(self.mock_upload_part.call_count, 0)
        self.assertEqual(
            "Failed fetching url for item id: 1, upload_id: None, part_number: 1",
            self.mock_handler.messages["error"][0]
        )
        self.assertFalse(res)


class TestLinkItem(TestCase):
    """Test class to host main tests for Link class in items package."""

    def setUp(self):
        dummy_url = "http://dummy.url"
        dummy_title = "Dummy Title"
        self.item = Link(dummy_url, dummy_title)

    def test_serialize(self):
        """
        Tests the serialize method of the class and checks if serialize
        output is returned as expected.
        """
        expected_value = {
            "content_identifier": self.item.content_identifier,
            "local_identifier": self.item.local_identifier,
            "meta": {"title": self.item.title},
            "url": self.item.url
        }
        self.assertEqual(self.item.serialize(), expected_value)

    def test__get_hex_repr(self):
        """
        Tests the _get_hex_repr method that give us back a specific length
        hex string for a given string.
        """
        test_url = "x" * 37
        r = self.item._get_hex_repr(test_url)
        self.assertEqual(r, "7878787878787878787878787878787878")
        test_url1 = "y" * 3
        r = self.item._get_hex_repr(test_url1)
        self.assertEqual(r, "797979")
        test_url2 = "z" * 17
        r = self.item._get_hex_repr(test_url2)
        self.assertEqual(r, "7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a")
        test_url3 = "z" * 16
        r = self.item._get_hex_repr(test_url3)
        self.assertEqual(r, "7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a")

    def test_str(self):
        """Tests the '__str__' representation of the objects of Link class"""
        regexp = (
            r"Transfer item, link type, with title \S+ \S+, url \S+ and local "
            r"identifier \S+"
        )
        pattern = re.compile(regexp)
        is_match = pattern.match(str(self.item))
        self.assertTrue(is_match)

    def test_init(self):
        """
        Tests the init method of the class and checks if needed properties
        are set after we create the object.
        """

        url = "http://dummy.url"
        title = "Dummy Title"
        item = Link(url, title)
        self.assertEqual(item.content_identifier, "web_content")
        self.assertEqual(item.url, url)
        self.assertEqual(item.title, title)
        if six.PY2:
            self.assertEqual(item.local_identifier, url.encode("hex")[-34:])
        else:
            self.assertEqual(item.local_identifier, url.encode("utf-8").hex()[-34:])


if __name__ == '__main__':
    main()
