"""
Module to host implementation of the different WeTransfer API HTTP queries
our SDK is making. Official docs https://developers.wetransfer.com/documentation
"""
import requests

from .version import __version__
from .logger import LOGGER


class HTTPLogger(object):
    """
    Parent class to allow Requests/Resposnes verbose logging.
    Inherit from this class to be able to use logging helper functions to
    debug Response and requests.
    """
    def log_request_details(self, request):
        """Verbose log requests"""
        request_body = request.body
        if request.method == "PUT":
            request_body = ""

        log = (
            "{0} request to <{1}> with headers:<{2}> and body:<{3}>"
        ).format(request.method, request.url, request.headers, request_body)
        LOGGER.debug(log)

    def log_response_details(self, response):
        """Verbose log responses"""
        log = (
            " {0} <{1}> response from <{2}> with headers:<{3}> and body:<{4}>"
        ).format(
            response.request.method, response.status_code,
            response.url, response.headers, response.text
        )
        LOGGER.debug(log)


class WTHTTP(HTTPLogger):
    """
    Parent class that implements some common logic(headers, url) for our
    HTTP queries towards WeTransfer infra.
    """

    def __init__(self, **kwargs):
        self.url = ""
        self.key = kwargs.get("key")
        self.token = kwargs.get("token")
        self.server = kwargs.get("server") or "dev.wetransfer.com"
        self.headers = kwargs.get("headers")

        default_user_agent = "WT python SDK v{0}".format(__version__)
        self.http_agent = kwargs.get("user_agent") or default_user_agent

        self.http_method_args = {
            "headers": self.get_headers(),
        }

        self.build_url()

    def get_headers(self):
        """Return needed headers for the HTTP request."""
        headers = {
            "User-Agent": self.http_agent,
            "Content-Type": "application/json",
            "x-api-key": self.key,
        }
        if self.token:
            headers["Authorization"] = "Bearer {0}".format(self.token)

        if self.headers:
            headers.update(self.headers)

        return headers

    def build_url(self):
        """
        Builds the request's url combining server and url_path
        classes attributes.
        """
        url_path = getattr(self, "url_path", "")
        self.url = "https://{0}{1}".format(self.server, url_path)


class WTGet(WTHTTP):
    """
    Parent class that holds basic logic for GET HTTP requests
    Every GET class should inherit from this one.
    """
    def get(self):
        """
        Makes the HTTP GET based on url attr and arguments.
        """
        response = requests.get(self.url, **self.http_method_args)

        self.log_request_details(response.request)
        self.log_response_details(response)

        return response


class WTPost(WTHTTP):
    """
    Parent class that holds basic logic for POST HTTP requests
    Every POST class should inherit from this one.
    """
    def __init__(self, **kwargs):
        self.post_data = {}
        super(WTPost, self).__init__(**kwargs)

    def post(self):
        """
        Makes the HTTP GET based on url attr, post data and arguments.
        """
        self._construct_post_data()

        post_args = {"json": self.post_data}
        self.http_method_args.update(post_args)

        response = requests.post(self.url, **self.http_method_args)

        self.log_request_details(response.request)
        self.log_response_details(response)

        return response

    def _construct_post_data(self):
        raise NotImplementedError


class Authorize(WTPost):
    """Class to implement Authorize API call"""

    URL_PATH = "/v1/authorize"

    def __init__(self, **kwargs):
        self.url_path = self.URL_PATH
        super(Authorize, self).__init__(**kwargs)

    def _construct_post_data(self):
        pass

    def create(self):
        return self.post()


class CreateTransfer(WTPost):
    """Class to implement create transfer API call"""

    URL_PATH = "/v1/transfers"

    def __init__(self, **kwargs):
        self.url_path = self.URL_PATH
        self.name = kwargs["name"]
        super(CreateTransfer, self).__init__(**kwargs)

    def _construct_post_data(self):
        self.post_data = {"name": self.name}

    def create(self):
        return self.post()


class AddItems(WTPost):
    """Class to implement add items to transfer API call"""

    URL_PATH = "/v1/transfers/{transfer_id}/items"

    def __init__(self, **kwargs):
        self.items = kwargs["items"]
        self.url_path = self.URL_PATH.format(**{"transfer_id": kwargs["transfer_id"]})
        super(AddItems, self).__init__(**kwargs)

    def _construct_post_data(self):
        self.post_data = {"items": []}
        for item in self.items:
            self.post_data["items"].append(item.serialize())

    def create(self):
        return self.post()


class GetUploadURL(WTGet):
    """Class to implement get upload URL for a part API call"""

    URL_PATH = "/v1/files/{file_id}/uploads/{part_number}/{multipart_upload_id}"

    def __init__(self, **kwargs):
        self.url_path = self.URL_PATH.format(**{
            "file_id": kwargs["id"],
            "part_number": kwargs["part_number"],
            "multipart_upload_id": kwargs["multipart_upload_id"]
        })
        super(GetUploadURL, self).__init__(**kwargs["client_options"])

    def create(self):
        return self.get()


class FinishUpload(WTPost):
    """Class to implement closing transfer API call"""

    URL_PATH = "/v1/files/{file_id}/uploads/complete"

    def __init__(self, **kwargs):
        self.url_path = self.URL_PATH.format(**{"file_id": kwargs["id"]})
        super(FinishUpload, self).__init__(**kwargs["client_options"])

    def _construct_post_data(self):
        pass

    def create(self):
        return self.post()


class UploadPart(HTTPLogger):
    """Class to implement upload part PUT API call"""

    def __init__(self, url, data):
        self.url = url
        self.data = data

    def create(self):
        response = requests.put(self.url, data=self.data)
        self.log_request_details(response.request)
        self.log_response_details(response)
        return response
