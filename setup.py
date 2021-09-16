"""
Copyright 2017 BlazeMeter Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from setuptools import setup

from apiritif.utils import VERSION

with open("requirements.txt") as reqs_file:
    requirements = [package for package in reqs_file.read().strip().split("\n")]

setup(
    name="apiritif",
    packages=['apiritif'],
    version=VERSION,
    description='Python framework for API testing',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    license='Apache 2.0',
    platform='any',
    author='Dmitri Pribysh',
    author_email='pribysh@blazemeter.com',
    url='https://github.com/Blazemeter/apiritif',
    download_url='https://github.com/Blazemeter/apiritif',
    docs_url='https://github.com/Blazemeter/apiritif',
    install_requires=requirements,
    entry_points={
        'pytest11': [
            'pytest_apiritif = apiritif.pytest_plugin',
        ]
    },
)
