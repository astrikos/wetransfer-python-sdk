from .logger import LOGGER
from .transfer import Transfer
from .api_requests import Authorize


class WTApiClient(object):
    """
    Class implementing logic for the client that connects to WT infrastructure
    It's the main entrypoint for the users, taking care auth and creating bare
    transfer objects.
    """

    def __init__(self, **kwargs):
        self.key = kwargs["key"]
        self.server = kwargs.get("server")
        self.token = None

    def authorize(self):
        """
        Implements authorization with WT API and stores the token returned
        upon success, which we will use for every other HTTP request towards
        WT infra.
        """
        client_options = {
            "key": self.key,
            "server": self.server
        }
        res = Authorize(**client_options).create()
        if not res.ok:
            log = "Failed authorizing"
            LOGGER.error(log)
            return False

        log = "Successfully authorized"
        LOGGER.info(log)

        body = res.json()
        if "token" not in body:
            LOGGER.error("Expected 'token' in Authorize json response")
            return False

        self.token = str(body["token"])

        return True

    def create_transfer(self, transfer_name="WT Transfer"):
        """
        Creates an bare transfer that we will use later to add our items
        and upload them. If creation is successfull it will return a Transfer
        object otherwise None.
        """
        client_options = {
            "key": self.key,
            "name": transfer_name,
            "token": self.token,
            "server": self.server
        }
        transfer = Transfer(**client_options)
        if not transfer.create():
            return None

        return transfer
