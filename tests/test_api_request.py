import os
import logging
import mock
import requests
from unittest import skip, main, TestCase
from wetransfer.api_requests import (
    HTTPLogger, WTHTTP, WTGet, WTPost, Authorize, CreateTransfer, AddItems,
    UploadPart, FinishUpload, GetUploadURL
)
from wetransfer.logger import LOGGER
from wetransfer.version import __version__
from wetransfer.items import File, Link


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


class FakeRequest(object):
    def __init__(self, method="GET"):
        self.body = "Test body"
        self.url = "testURL"
        self.headers = {"header1": "test1"}
        self.method = method


class FakeResponse(object):
    def __init__(self, request_method="GET"):
        self.request = FakeRequest(method=request_method)
        self.status_code = 200
        self.url = "testURL"
        self.headers = {"header2": "test2"}
        self.text = "test_text"


class TestHTTPLogger(TestCase):

    def setUp(self):
        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)
        self.httpLogger = HTTPLogger()

    def test_log_request_details(self):
        """Tests the function that logs the request"""
        request = FakeRequest()
        expected_output = (
            "{0} request to <{1}> with headers:<{2}> and "
            "body:<{3}>"
        ).format(request.method, request.url, request.headers, request.body)
        self.httpLogger.log_request_details(request)
        self.assertEqual(
            expected_output, self.mock_handler.messages["debug"][0]
        )

    def test_log_request_details_put(self):
        """Tests the function that logs the PUT request"""
        request = FakeRequest(method="PUT")
        expected_output = (
            "{0} request to <{1}> with headers:<{2}> and "
            "body:<>"
        ).format(request.method, request.url, request.headers)
        self.httpLogger.log_request_details(request)
        self.assertEqual(
            expected_output, self.mock_handler.messages["debug"][0]
        )

    def test_log_response_details(self):
        """Tests the function that logs the response"""
        response = FakeResponse()
        expected_output = (
            " {0} <{1}> response from <{2}> with headers:<{3}> and "
            "body:<{4}>"
        ).format(
            response.request.method, response.status_code, response.url,
            response.headers, response.text
        )
        self.httpLogger.log_response_details(response)
        self.assertEqual(
            expected_output, self.mock_handler.messages["debug"][0]
        )


class TestWTHTTP(TestCase):
    def setUp(self):
        self.kwargs = {
            "key": "test_key",
            "token": "test_token",
            "server": "test_server",
        }
        self.expected_agent = "WT python SDK v{0}".format(__version__)
        self.expected_headers = {
            "User-Agent": self.expected_agent,
            "Content-Type": "application/json",
            "x-api-key": self.kwargs["key"],
            "Authorization": "Bearer {0}".format(self.kwargs["token"])
        }

    def test_init(self):
        wthttp = WTHTTP(**self.kwargs)
        self.assertEqual(wthttp.url, "https://test_server")
        self.assertEqual(wthttp.key, self.kwargs["key"])
        self.assertEqual(wthttp.token, self.kwargs["token"])
        self.assertEqual(wthttp.server, self.kwargs["server"])
        self.assertEqual(wthttp.http_agent, self.expected_agent)
        self.assertEqual(wthttp.headers, None)
        self.assertEqual(
            wthttp.http_method_args,
            {"headers": self.expected_headers}
        )

    def test_init_server(self):
        kwargs = self.kwargs
        del kwargs["server"]
        wthttp = WTHTTP(**kwargs)
        self.assertEqual(wthttp.server, "dev.wetransfer.com")

    def test_init_empty_kwargs(self):
        kwargs = {}
        wthttp = WTHTTP(**kwargs)
        self.assertEqual(wthttp.url, "https://dev.wetransfer.com")
        self.assertEqual(wthttp.key, None)
        self.assertEqual(wthttp.token, None)
        self.assertEqual(wthttp.server, "dev.wetransfer.com")
        self.assertEqual(wthttp.http_agent, self.expected_agent)
        self.assertEqual(wthttp.headers, None)
        expected_headers = {
            "User-Agent": self.expected_agent,
            "Content-Type": "application/json",
            "x-api-key": None,
        }
        self.assertEqual(
            wthttp.http_method_args,
            {"headers": expected_headers}
        )

    def test_init_http_agent(self):
        kwargs = self.kwargs
        self.kwargs["user_agent"] = "test_agent"
        wthttp = WTHTTP(**kwargs)
        self.assertEqual(wthttp.http_agent, "test_agent")

        del kwargs["user_agent"]
        wthttp = WTHTTP(**kwargs)
        self.assertEqual(wthttp.http_agent, self.expected_agent)

    def test_get_headers(self):
        kwargs = self.kwargs
        wthttp = WTHTTP(**kwargs)
        headers = wthttp.get_headers()
        self.assertEqual(headers, self.expected_headers)

        kwargs = self.kwargs.copy()
        del kwargs["token"]
        expected_headers = {
            "User-Agent": self.expected_agent,
            "Content-Type": "application/json",
            "x-api-key": "test_key",
        }
        wthttp = WTHTTP(**kwargs)
        headers = wthttp.get_headers()
        self.assertEqual(headers, expected_headers)

        kwargs = self.kwargs.copy()
        custom_headers = {"my_header": "my_value"}
        kwargs["headers"] = custom_headers
        wthttp = WTHTTP(**kwargs)
        headers = wthttp.get_headers()
        self.expected_headers["my_header"] = "my_value"
        self.assertEqual(headers, self.expected_headers)

    def test_build_url(self):
        kwargs = self.kwargs
        wthttp = WTHTTP(**kwargs)
        wthttp.build_url()
        self.assertEqual(wthttp.url, "https://test_server")


class TestWTGet(TestCase):
    def setUp(self):
        self.kwargs = {
            "key": "test_key",
            "token": "test_token",
            "server": "test_server",
        }
        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)

    def test_get(self):
        exp_res = FakeResponse()

        expected_request_output = (
            "{0} request to <{1}> with headers:<{2}> and "
            "body:<{3}>"
        ).format(
            exp_res.request.method, exp_res.request.url,
            exp_res.request.headers, exp_res.request.body
        )

        expected_response_output = (
            " {0} <{1}> response from <{2}> with headers:<{3}> and "
            "body:<{4}>"
        ).format(
            exp_res.request.method, exp_res.status_code, exp_res.url,
            exp_res.headers, exp_res.text
        )

        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = exp_res
            wtget = WTGet(**self.kwargs)
            res = wtget.get()

            self.assertEqual(res, exp_res)

            self.assertEqual(
                expected_request_output, self.mock_handler.messages["debug"][0]
            )

            self.assertEqual(
                expected_response_output, self.mock_handler.messages["debug"][1]
            )


class TestWTPost(TestCase):

    def setUp(self):
        self.kwargs = {
            "key": "test_key",
            "token": "test_token",
            "server": "test_server",
        }
        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)
        self.expected_agent = "WT python SDK v{0}".format(__version__)
        self.expected_headers = {
            "User-Agent": self.expected_agent,
            "Content-Type": "application/json",
            "x-api-key": self.kwargs["key"],
            "Authorization": "Bearer {0}".format(self.kwargs["token"])
        }

    def test_init(self):
        wtpost = WTPost(**self.kwargs)
        self.assertEqual(wtpost.post_data, {})

    def test_construct_post_data(self):
        wtpost = WTPost(**self.kwargs)
        self.assertRaises(NotImplementedError, wtpost._construct_post_data)

    def test_post(self):

        class FakeWTPostImplementation(WTPost):

            def _construct_post_data(self):
                pass

        exp_res = FakeResponse(request_method="POST")

        expected_request_output = (
            "{0} request to <{1}> with headers:<{2}> and "
            "body:<{3}>"
        ).format(
            exp_res.request.method, exp_res.request.url,
            exp_res.request.headers, exp_res.request.body
        )

        expected_response_output = (
            " {0} <{1}> response from <{2}> with headers:<{3}> and "
            "body:<{4}>"
        ).format(
            exp_res.request.method, exp_res.status_code, exp_res.url,
            exp_res.headers, exp_res.text
        )

        with mock.patch('requests.post') as mock_post:
            mock_post.return_value = exp_res
            cl = FakeWTPostImplementation(**self.kwargs)
            res = cl.post()
            self.assertEqual(res, exp_res)
            expected_method_args = {
                "headers": self.expected_headers,
                "json": {},
            }
            self.assertEqual(cl.http_method_args, expected_method_args)
            self.assertEqual(
                expected_request_output, self.mock_handler.messages["debug"][0]
            )

            self.assertEqual(
                expected_response_output, self.mock_handler.messages["debug"][1]
            )


class WTPostTestBase(object):

    def setUp(self):
        self.kwargs = {
            "key": "test_key",
            "token": "test_token",
            "server": "test_server",
        }
        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)
        self.expected_agent = "WT python SDK v{0}".format(__version__)
        self.expected_headers = {
            "User-Agent": self.expected_agent,
            "Content-Type": "application/json",
            "x-api-key": self.kwargs["key"],
            "Authorization": "Bearer {0}".format(self.kwargs["token"])
        }

    def get_test_object(self):
        pass

    def get_mock_path(self):
        pass

    def test_init(self):
        obj = self.get_test_object()
        self.assertEqual(obj.url_path, obj.URL_PATH)

    def test_create(self):
        exp_res = FakeResponse(request_method="POST")
        with mock.patch('requests.post') as mock_post:
            mock_post.return_value = exp_res
            obj = self.get_test_object()
            res = obj.create()
            self.assertEqual(res, exp_res)

        path = self.get_mock_path()
        with mock.patch(path) as mock_ok:
            obj = self.get_test_object()
            res = obj.create()
            mock_ok.assert_called_once()


class TestAuthorize(WTPostTestBase, TestCase):

    def get_test_object(self):
        return Authorize(**self.kwargs)

    def get_mock_path(self):
        return "wetransfer.api_requests.Authorize.post"


class TestCreateTransfer(WTPostTestBase, TestCase):

    def get_test_object(self):
        self.kwargs.update({"name": "Dummy Transfer"})
        return CreateTransfer(**self.kwargs)

    def get_mock_path(self):
        return "wetransfer.api_requests.CreateTransfer.post"

    def test_construct_data(self):
        self.kwargs.update({"name": "Dummy Transfer"})
        ct = CreateTransfer(**self.kwargs)
        ct._construct_post_data()
        expected_post_data = {"name": "Dummy Transfer"}
        self.assertEqual(ct.post_data, expected_post_data)


class TestAddItems(WTPostTestBase, TestCase):

    def setUp(self):
        super(TestAddItems, self).setUp()
        print(os.path.abspath(__file__))
        print(__file__)
        self.kwargs.update({
            "transfer_id": 1,
            "items": [
                Link("https://wetransfer.com/", "WeTransfer Website"),
                File(__file__)
            ]
        })

    def get_test_object(self):
        return AddItems(**self.kwargs)

    def get_mock_path(self):
        return "wetransfer.api_requests.AddItems.post"

    def test_init(self):
        obj = self.get_test_object()
        self.assertEqual(
            obj.url_path,
            obj.URL_PATH.format(**{"transfer_id": self.kwargs["transfer_id"]})
        )

    def test_construct_data(self):
        obj = AddItems(**self.kwargs)
        obj._construct_post_data()
        expected_post_data = {"items": [
            self.kwargs["items"][0].serialize(),
            self.kwargs["items"][1].serialize()
        ]}
        self.assertEqual(obj.post_data, expected_post_data)


class TestFinishUpload(WTPostTestBase, TestCase):

    def setUp(self):
        super(TestFinishUpload, self).setUp()
        self.kwargs = {
            "client_options": {
                "key": "test_key",
                "token": "test_token",
                "server": "test_server",
            },
            "id": 1
        }

    def get_test_object(self):
        return FinishUpload(**self.kwargs)

    def get_mock_path(self):
        return "wetransfer.api_requests.FinishUpload.post"

    def test_init(self):
        obj = self.get_test_object()
        self.assertEqual(
            obj.url_path,
            obj.URL_PATH.format(**{"file_id": self.kwargs["id"]})
        )


class TestUploadPart(TestCase):

    def setUp(self):
        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)

    def test_init(self):
        test_url = "test_url"
        test_data = "test_data"
        wtupload = UploadPart(test_url, test_data)
        self.assertEqual(wtupload.url, test_url)
        self.assertEqual(wtupload.data, test_data)

    def test_create(self):
        exp_res = FakeResponse(request_method="PUT")

        expected_request_output = (
            "{0} request to <{1}> with headers:<{2}> and "
            "body:<>"
        ).format(
            exp_res.request.method, exp_res.request.url,
            exp_res.request.headers
        )

        expected_response_output = (
            " {0} <{1}> response from <{2}> with headers:<{3}> and "
            "body:<{4}>"
        ).format(
            exp_res.request.method, exp_res.status_code, exp_res.url,
            exp_res.headers, exp_res.text
        )

        with mock.patch('requests.put') as mock_put:
            mock_put.return_value = exp_res
            test_url = "test_url"
            test_data = "test_data"
            wtupload = UploadPart(test_url, test_data)
            res = wtupload.create()
            self.assertEqual(res, exp_res)
            self.assertEqual(
                expected_request_output, self.mock_handler.messages["debug"][0]
            )

            self.assertEqual(
                expected_response_output, self.mock_handler.messages["debug"][1]
            )


class TestGetUploadURL(TestCase):

    def setUp(self):
        self.kwargs = {
            "client_options": {
                "key": "test_key",
                "token": "test_token",
                "server": "test_server",
            },
            "id": 1,
            "part_number": 1,
            "multipart_upload_id": 1
        }
        logging.basicConfig()
        logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)
        self.mock_handler = MockLoggingHandler()
        LOGGER.addHandler(self.mock_handler)

    def test_init(self):
        obj = GetUploadURL(**self.kwargs)
        self.assertEqual(
            obj.url_path,
            obj.URL_PATH.format(**{
                "file_id": self.kwargs["id"],
                "part_number": self.kwargs["part_number"],
                "multipart_upload_id": self.kwargs["multipart_upload_id"]
            })
        )

    def test_create(self):
        exp_res = FakeResponse(request_method="GET")
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = exp_res
            obj = GetUploadURL(**self.kwargs)
            res = obj.create()
            self.assertEqual(res, exp_res)

        path = "wetransfer.api_requests.GetUploadURL.get"
        with mock.patch(path) as mock_ok:
            obj = GetUploadURL(**self.kwargs)
            res = obj.create()
            mock_ok.assert_called_once()


if __name__ == '__main__':
    main()
