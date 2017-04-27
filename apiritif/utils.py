import re
import sys

if sys.version_info.major == 2:
    import urlparse as parse
else:
    import urllib.parse as parse


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


def is_absolute_url(url):
    return bool(parse.urlparse(url).netloc)


def extract_embedded_resources(html, base_url):
    # Regex is taken from JMeter's src/protocol/http/org/apache/jmeter/protocol/http/parser/RegexpHTMLParser.java
    resource_re = r"""<(?:!--.*?-->|BASE\s(?:[^>]*\s)?HREF\s*=\s*(?:"([^"]*)"|'([^']*)'|([^"'\s>\\][^\s>]*)(?=[\s>]))|(?:IMG|SCRIPT|FRAME|IFRAME|BGSOUND)\s(?:[^>]*\s)?SRC\s*=\s*(?:"([^"]*)"|'([^']*)'|([^"'\s>\\][^\s>]*)(?=[\s>]))|APPLET\s(?:[^>]*\s)?CODE(?:BASE)?\s*=\s*(?:"([^"]*)"|'([^']*)'|([^"'\s>\\][^\s>]*)(?=[\s>]))|(?:EMBED|OBJECT)\s(?:[^>]*\s)?(?:SRC|CODEBASE|DATA)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^"'\s>\\][^\s>]*)(?=[\s>]))|(?:BODY|TABLE|TR|TD)\s(?:[^>]*\s)?BACKGROUND\s*=\s*(?:"([^"]*)"|'([^']*)'|([^"'\s>\\][^\s>]*)(?=[\s>]))|[^<]+?STYLE\s*=['"].*?URL\(\s*['"](.+?)['"]\s*\)|INPUT(?:\s(?:[^>]*\s)?(?:SRC\s*=\s*(?:"([^"]*)"|'([^']*)'|([^"'\s>\\][^\s>]*)(?=[\s>]))|TYPE\s*=\s*(?:"image"|'image'|image(?=[\s>])))){2,}|LINK(?:\s(?:[^>]*\s)?(?:HREF\s*=\s*(?:"([^"]*)"|'([^']*)'|([^"'\s>\\][^\s>]*)(?=[\s>]))|REL\s*=\s*(?:"stylesheet"|'stylesheet'|stylesheet(?=[\s>])))){2,})"""
    links = [subitem for item in re.findall(resource_re, html, re.IGNORECASE) for subitem in item if subitem]
    return [
        link if is_absolute_url(link) else parse.urljoin(base_url, link)
        for link in links
    ]
