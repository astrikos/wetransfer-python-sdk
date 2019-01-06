"""Module to hold different types of transfer items"""
import os
import six

from .logger import LOGGER
from .api_requests import GetUploadURL, UploadPart, FinishUpload


class File(object):
    """
    Class to hold actions and attributes related to a File type transfer item
    """
    def __init__(self, filepath):
        self.CHUNK_SIZE = 6291456  # 6MB
        self.filename = None
        self.filesize = None
        self.content_identifier = "file"
        self.local_identifier = os.path.abspath(os.path.expanduser(filepath))
        self.id = None
        self.transfer_id = None
        self.multipart_parts = None
        self.multipart_upload_id = None
        self.client_options = None

        self._init_file()

    def _init_file(self):
        """Further initialize the File instance with additional details"""

        _, self.filename = os.path.split(self.local_identifier)
        self.filesize = os.path.getsize(self.local_identifier)

    def serialize(self):
        """Serialize object to needed format from the API"""

        return {
            "filename": self.filename,
            "filesize": self.filesize,
            "content_identifier": self.content_identifier,
            "local_identifier": self.local_identifier[-34:]
        }

    def load_info(self, **kwargs):
        """
        Dynamically load attributes with values from details we get from the
        server side from the add items API request.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

    def upload(self):
        """
        Implements logic for uploading item after spliting it into 6M chunks
        and uploading each of them separetly.
        """

        with open(self.local_identifier) as f:
            i = 1
            # Split file into pieces and read sequentially
            for piece in iter(lambda: f.read(self.CHUNK_SIZE), ''):
                res = self.upload_part(piece, i)
                if not res:
                    return False
                i += 1

        kwargs = {"id": self.id, "client_options": self.client_options}
        res = FinishUpload(**kwargs).create()
        if not res.ok:
            log = "Failed closing upload for item id: {0}".format(self.id)
            LOGGER.error(log)
            return False

        log = "Successfully closed upload for item id: {0}".format(self.id)
        LOGGER.info(log)
        return True

    def upload_part(self, part, part_number):
        """
        Uploads specific part after fetching URL from the API for this part
        """
        kwargs = {
            "id": self.id, "part_number": part_number,
            "multipart_upload_id": self.multipart_upload_id,
            "client_options": self.client_options
        }
        res = GetUploadURL(**kwargs).create()
        if not res.ok:
            log = (
                "Failed fetching url for item id: {0}, upload_id: {1}, "
                "part_number: {2}"
            ).format(
                self.id, self.multipart_upload_id, part_number
            )
            LOGGER.error(log)
            return False

        log = (
            "Successfully fetched url for item id: {0}, upload_id: {1}, "
            "part_number: {2}"
        ).format(self.id, self.multipart_upload_id, part_number)
        LOGGER.info(log)

        body = res.json()
        upload_url = body["upload_url"]

        res = UploadPart(upload_url, part).create()

        if not res.ok:
            log = "Failed PUT-ing part-number {0} for item id: {1}".format(
                part_number, self.id)
            LOGGER.error(log)
            return False

        log = (
            "Successfully PUT-ed part-number {0} for item id: {1}"
        ).format(part_number, self.id)
        LOGGER.info(log)

        return True

    def __str__(self):
        log = (
            "Transfer item, file type, with size {0}, name {1}, and local path"
            " {2}, has {3} multi parts"
        ).format(
            self.filesize, self.filename,
            self.local_identifier, self.multipart_parts
        )
        return log


class Link(object):
    """
    Class to hold actions and attributes related to a Link type transfer item
    """
    def __init__(self, url, title):
        self.content_identifier = "web_content"
        self.local_identifier = self._get_hex_repr(url)
        self.url = url
        self.title = title

    def _get_hex_repr(self, url):
        if six.PY2:
            return url.encode("hex")[-34:]
        else:
            return url.encode("utf-8").hex()[-34:]

    def serialize(self):
        """Serialize object to needed format from the API"""
        return {
            "content_identifier": self.content_identifier,
            "local_identifier": self.local_identifier,
            "meta": {"title": self.title},
            "url": self.url
        }

    def __str__(self):
        log = (
            "Transfer item, link type, with title {0}, url {1} and local "
            "identifier {2}"
        ).format(
            self.title, self.url,
            self.local_identifier
        )
        return log
