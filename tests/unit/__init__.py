import os

from urllib3 import disable_warnings

disable_warnings()

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)) + "/../resources/"))
