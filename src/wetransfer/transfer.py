"""Module that implements logic related to transfers"""
from .logger import LOGGER
from .items import File, Link
from .api_requests import AddItems, CreateTransfer, FinishUpload


class Transfer(object):
    """
    Class to implement logic for all actions and attributes related to a
    transfer object
    """
    def __init__(self, **kwargs):
        self.transfer_id = None
        self.transfer_items = []
        self.transfer_files = []
        self.name = kwargs["name"]
        self.client_options = {
            "name": self.name,
            "key": kwargs["key"],
            "token": kwargs["token"],
            "server": kwargs.get("server"),
        }

    def create(self):
        """
        Creates and returns an empty transfer that will hold your items later on
        """
        res = CreateTransfer(**self.client_options).create()

        if not res.ok:
            log = "Failed creating new transfer"
            LOGGER.error(log)
            return False

        log = "Successfully created new transfer"
        LOGGER.info(log)

        body = res.json()
        self.transfer_id = body["id"]
        self.shortened_url = body["shortened_url"]

        return True

    def add_items(self, items):
        """
        Implement logic for adding items in the given list, upload them, and
        closing the transfer itself.
        """
        self.transfer_items.extend(items)
        kwargs = {
            "items": self.transfer_items, "transfer_id": self.transfer_id
        }
        kwargs.update(self.client_options)

        res = AddItems(**kwargs).create()

        if not self.validate_add_items_response(res):
            return False

        log = "Successfully added items: {0} to transfer {1}".format(
                [str(i) for i in self.transfer_items], self.transfer_id
        )
        LOGGER.info(log)

        returned_items = res.json()

        for index, item in enumerate(returned_items):
            if item["content_identifier"] == "web_content":
                continue

            kwargs = {
                "id": item["id"], "transfer_id": self.transfer_id,
                "client_options": self.client_options,
                "multipart_parts": item["meta"]["multipart_parts"],
                "multipart_upload_id": item["meta"]["multipart_upload_id"],
            }
            self.transfer_items[index].load_info(**kwargs)
            self.transfer_files.append(self.transfer_items[index])

        return self.upload_items()

    def validate_add_items_response(self, response):
        if not response.ok:
            log = "Failed to add items: {0} to transfer {1}".format(
                [str(i) for i in self.transfer_items], self.transfer_id
            )
            LOGGER.error(log)
            return False

        returned_items = response.json()

        if len(returned_items) != len(self.transfer_items):
            log = (
                "Add items API call didn't return same number of items ({0}) "
                "than what we sent ({1})"
            ).format(len(returned_items), len(self.transfer_items))
            LOGGER.error(log)
            return False

        return True

    def upload_items(self):
        """Uploads each item of the instances items list"""
        for item in self.transfer_files:
            r = item.upload()
            if not r:
                log = "Failed to upload item {0}".format(item)
                LOGGER.error(log)
                return False

            log = "Successfully uploaded item {0}".format(item)
            LOGGER.info(log)

        return True

    def add_files(self, file_paths):
        """Helper function to upload file only type items given the paths"""
        if isinstance(file_paths, str):
            self.transfer_items.append(File(file_paths))
        elif isinstance(file_paths, list):
            for path in file_paths:
                self.transfer_items.append(File(path))

        return self.add_items()

    def add_links(self, urls):
        """Helper function to upload link only type items given the URLs"""
        if isinstance(urls, str):
            self.transfer_items.append(Link(urls))
        elif isinstance(urls, list):
            for url in urls:
                self.transfer_items.append(Link(url))

        return self.add_items()

    def __str__(self):
        log = (
            "Transfer with id: {0}, can be found in short url: {1}, with "
            "following items: {2}"
        ).format(
            self.transfer_id, self.shortened_url,
            [str(i) for i in self.transfer_items]
        )
        return log
