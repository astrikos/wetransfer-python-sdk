import os
from setuptools import setup
from setuptools import find_packages


__version__ = None
with open("src/wetransfer/version.py", "r") as f:
    exec(f.read())

# Allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# Get proper long description for package
with open("README.md", "r") as f:
    description = f.read()


setup(
    name="wetransfer",
    version=__version__,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=True,
    description="A Python SDK for WeTransfer's Public API",
    long_description=description,
    long_description_content_type='text/markdown',
    url="https://github.com/astrikos/wetransfer-python-sdk",
    download_url="https://github.com/astrikos/wetransfer-python-sdk",
    author="Andreas Strikos",
    author_email="andreas@wetransfer.com",
    maintainer="Andreas Strikos",
    maintainer_email="andreas@wetransfer.com",
    test_suite="tests",
    install_requires=[
        "requests>=2.7.0",
        "six"
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
