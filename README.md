# WeTransfer Python SDK
A Python SDK for the WeTransfer's Public API
## Installation
Use PYPI to install latest stable version:
```
pip install wetransfer
```

Checkout the repository and inside the repo's root directory use pip to install latest version to your environment with:
```
pip install .
```

## Usage
**Before starting make sure you have an API key acquired from [Developers Portal](https://developers.wetransfer.com/).**

As a first step you need to create a client and fill in your board name:
```python
from wetransfer.client import WTApiClient

kwargs = {"key":  "<my-very-personal-api-key>"},
          "name": "Andreas' very first transfer from python!"}
wt_client = WTApiClient(**kwargs)
```

After you have the client instance you need to authorize using this client:
```python
wt_client.authorize()
```

If authorization is successful you should be able to create an new empty transfer
```python
transfer = wt_client.create_transfer()
```

Afterwards you should be able to add items to it

```python
from wetransfer.items import File

f1 = File("~/test.txt")
f2 = File("~/test2.txt")
transfer.add_items([f1, f2])

print(transfer)

```

After calling `add_items` method the upload process should start. As soon as it returns you should be
able to see details for this transfer and access the url that your transfer is available for download.

The full code snippet is as follows:
```python
import sys
from wetransfer.items import File, Link
from wetransfer.client import WTApiClient

kwargs = {"key": "<my-very-personal-api-key>"}
wt_client = WTApiClient(**kwargs)

if not wt_client.authorize():
    sys.exit(0)

transfer = wt_client.create_transfer()

f1 = File("./test.txt")
l1 = Link("https://wetransfer.com/", "WeTransfer Website")

transfer.add_items([f1, l1])

print(transfer)
```

which if you run it you should see something like:
```
Transfer with id: <id>, can be found in short url: <str>, with following items: ['Transfer item, file type, with size 10, name test.txt, and local path /Users/bla/test.txt, has 1 multi parts']
```

### Helper methods
If you need to upload only file you can skip the `File` objects creation and use a helper function that allows you to specify a list of paths as strings and will add these for you a given `Transfer`
```python
transfer.add_files(["file1.txt", "file2.txt"])
```

Similar method exist for URLs:
```python
transfer.add_links(["https://wetransfer.com/", "http://www.visitgreece.gr/"])
```

## Debugging
If you need to debug or investigate weird behaviours you can enable logs for this SDK by enabling the dedicated python logger
```python
import logging

logging.basicConfig()
logging.getLogger("wetransfer-python-sdk").setLevel(logging.DEBUG)

kwargs = {"key":  "<my-very-personal-api-key>",
          "name": "Andreas' very first transfer from python!"}
wt = WTApiClient(**kwargs)
...
``` 

You can set the severity level accordingly depending on the verbosity you desire.

## Contributing
See [dedicated](./CONTRIBUTING.md) section.
