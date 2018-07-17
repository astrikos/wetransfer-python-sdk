import os
from setuptools import setup
from setuptools import find_packages


__version__ = None
exec(open("src/wetransfer/version.py").read())

# Allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="wetransfer",
    version=__version__,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=True,
    description="",
    url="https://github.com/WeTransfer/wetransfer-python-sdk",
    download_url="https://github.com/WeTransfer/wetransfer-python-sdk",
    author="Andreas Strikos",
    author_email="andreas@wetransfer.com",
    maintainer="Andreas Strikos",
    maintainer_email="andreas@wetransfer.com",
    install_requires=[
        "requests>=2.7.0",
    ],
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
