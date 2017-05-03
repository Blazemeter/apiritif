import random
import re
import string
from datetime import datetime


def headers_as_text(headers_dict):
    return "\n".join("%s: %s" % (key, value) for key, value in headers_dict.items())


def shorten(string, upto, end_with="..."):
    return string[:upto - len(end_with)] + end_with if len(string) > upto else string


def assert_regexp(regex, text, match=False, msg=None):
    if match:
        if re.match(regex, text) is None:
            msg = msg or "Regex %r didn't match expected value: %r" % (regex, shorten(text, 100))
            raise AssertionError(msg)
    else:
        if not re.findall(regex, text):
            msg = msg or "Regex %r didn't find anything in text %r" % (regex, shorten(text, 100))
            raise AssertionError(msg)


def assert_not_regexp(regex, text, match=False, msg=None):
    if match:
        if re.match(regex, text) is not None:
            msg = msg or "Regex %r unexpectedly matched expected value: %r" % (regex, shorten(text, 100))
            raise AssertionError(msg)
    else:
        if re.findall(regex, text):
            msg = msg or "Regex %r unexpectedly found something in text %r" % (regex, shorten(text, 100))
            raise AssertionError(msg)


def random_uniform(start, stop=None):
    return random.randrange(start, stop=stop)


def random_normal(sigma, mu):
    return random.gauss(sigma, mu)


def random_string(size, chars=string.printable):
    return "".join(random.choice(chars) for _ in range(size))


class SimpleDateFormat(object):
    def __init__(self, format):
        self.format = format

    @staticmethod
    def _replacer(match):
        what = match.group(0)
        if what.startswith("y") or what.startswith("Y"):
            if len(what) < 4:
                return "%y"
            else:
                return "%Y"
        elif what.startswith("M"):
            return "%m"
        elif what.startswith("d"):
            return "%d"
        elif what.startswith("h"):
            return "%I"
        elif what.startswith("H"):
            return "%H"
        elif what.startswith("m"):
            return "%M"
        elif what.startswith("s"):
            return "%S"
        elif what.startswith("S"):
            return what
        elif what.startswith("E"):
            if len("E") <= 3:
                return "%a"
            else:
                return "%A"
        elif what.startswith("D"):
            return "%j"
        elif what.startswith("w"):
            return "%U"
        elif what.startswith("a"):
            return "%p"
        elif what.startswith("z"):
            return "%z"
        elif what.startswith("Z"):
            return "%Z"

    def format_datetime(self, datetime):
        letters = "yYMdhHmsSEDwazZ"  # TODO: moar
        regex = "(" + "|".join(letter + "+" for letter in letters) + ")"
        strftime_fmt = re.sub(regex, self._replacer, self.format)
        return datetime.strftime(strftime_fmt)


def formatted_date(format_string):
    formatter = SimpleDateFormat(format_string)
    return formatter.format_datetime(datetime.now())
