"""ESI slack bot."""

import os
from setuptools import setup
from setuptools import find_packages
from setuphelpers import git_version
from setuphelpers import test_command
from setuphelpers import long_description

setup(
    name="esi-bot",
    version=git_version(),
    description="ESI slack bot",
    long_description=long_description(),
    packages=find_packages(),
    cmdclass=test_command(cover="esi_bot"),
    author="Adam Talsma",
    author_email="adam@talsma.ca",
    url="https://github.com/esi/esi-bot/",
    download_url="https://github.com/esi/esi-bot/",
    install_requires=[
        "requests >= 2.18.4",
        "slackclient == 1.3.2",
        "gevent >= 1.2.2",
    ],
    setup_requires=["setuphelpers >= 0.1.2"],
    entry_points={"console_scripts": ["esi-bot = esi_bot.bot:main"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
    ],
)
