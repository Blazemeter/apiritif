# Apiritif

Apiritif is a number of utilities aimed to simplify the process of maintaining API tests. 
Apiritif tests fully based on python nose tests. This library can help you to develop and run your existing tests.
In order to create any valid tests for Apiritif you can read [nose test documentation](https://nose.readthedocs.io/en/latest/testing.html).

Here described some features of Apiritif which can help you to create tests more easily.  

## Overview

## HTTP Requests

Apiritif allows to use simple `requests`-like API for making HTTP requests.

```python
from apiritif import http

response = http.get("http://example.com")
response.assert_ok()  # will raise AssertionError if request wasn't successful
```

`http` object provides the following methods:
```python
from apiritif import http

http.get("http://api.example.com/posts")
http.post("http://api.example.com/posts")
http.put("http://api.example.com/posts/1")
http.patch("http://api.example.com/posts/1")
http.delete("http://api.example.com/posts/1")
http.head("http://api.example.com/posts")
```

All methods (`get`, `post`, `put`, `patch`, `delete`, `head`) support the following arguments:
```python
def get(address,               # URL for the request
        params=None,           # URL params dict
        headers=None,          # HTTP headers
        cookies=None,          # request cookies
        data=None,             # raw request data
        json=None,             # attach JSON object as request body
        encrypted_cert=None,   # certificate to use with request 
        allow_redirects=True,  # automatically follow HTTP redirects
        timeout=30)            # request timeout, by default it's 30 seconds
```

##### Certificate usage
Currently `http` supports `pem` and `pkcs12` certificates. 
Here is an example of certificate usage:
```python
http.get("http://api.example.com/posts", encrypted_cert=('./cert.pem', 'passphrase'))
```
First parameter is path to certificate, second is the passphrase certificate encrypted with.

## HTTP Targets

Target is an object that captures resource name of the URL (protocol, domain, port)
and allows to set some settings applied to all requests made for a target.


```python
from apiritif import http

qa_env = http.target("http://192.160.0.2")
qa_env.get("/api/v4/user")
qa_env.get("/api/v4/user")
```

Target constructor supports the following options:
```python
target = apiritif.http.target(
    address,               # target base address
    base_path=None,        # base path prepended to all paths (e.g. '/api/v2')
    use_cookies=True,      # use cookies
    additional_headers=None,  # additional headers for all requests
    keep_alive=True,       # reuse opened HTTP connection
    auto_assert_ok=True,   # automatically invoke 'assert_ok' after each request
)
```


## Assertions

Apiritif responses provide a lot of useful assertions that can be used on responses.

Here's the list of assertions that can be used:
```python
response = http.get("http://example.com/")

# assert that request succeeded (status code is 2xx or 3xx)
response.assert_ok()
# assert that request has failed
response.assert_failed()

# status code based assertions
response.assert_2xx()
response.assert_3xx()
response.assert_4xx()
response.assert_5xx()
response.assert_status_code(code)
response.assert_not_status_code(code)
response.assert_status_code_in(codes)

# content-based assertions

# assert that response body contains a string
response.assert_in_body(member)

# assert that response body doesn't contain a string
response.assert_not_in_body(member)

# search (or match) response body with a regex
response.assert_regex_in_body(regex, match=False)
response.assert_regex_not_in_body(regex, match=False)

# assert that response has header
response.assert_has_header(header)

# assert that response has header with given value
response.assert_header_value(header, value)

# assert that response's headers contains a string
response.assert_in_headers(member)
response.assert_not_in_headers(member)

# search (or match) response body with a regex
response.assert_regex_in_headers(member)
response.assert_regex_not_in_headers(member)

# assert that response body matches JSONPath query
response.assert_jsonpath(jsonpath_query, expected_value=None)
response.assert_not_jsonpath(jsonpath_query)

# assert that response body matches XPath query
response.assert_xpath(xpath_query, parser_type='html', validate=False)
response.assert_not_xpath(xpath_query, parser_type='html', validate=False)

# assert that HTML response body contains CSS selector item
response.assert_cssselect(selector, expected_value=None, attribute=None)
response.assert_not_cssselect(selector, expected_value=None, attribute=None)

```

Note that assertions can be chained, so the following construction is entirely valid:
```python

response = http.get("http://example.com/")
response.assert_ok().assert_in_body("Example")
```

## Transactions

Apiritif allows to group multiple requests or actions into a transaction using a `transaction` context manager.
For example when we have test action like bellow we want to execute requests according to concrete user as a separate piece.
Also we want to process test for `users/all` page even if something wrong with previous actions.

```python
def test_with_login():
    user_credentials = data_mock.get_my_user()
    http.get("https://blazedemo.com/user/login?id="+user_credentials.id).assert_ok()
    http.get("https://blazedemo.com/user/id/personalPage").assert_ok()
    http.get("https://blazedemo.com/user/id/getPersonalData").assert_ok()

    http.get("https://blazedemo.com/users/all").assert_ok()
```

Here where we can use transaction in order to wrap login process in one block.

```python
def test_with_login():
    with apiritif.transaction('Login'):
        user_credentials = data_mock.get_my_user()
        http.get("https://blazedemo.com/user/login?id="+user_credentials.id).assert_ok()
        http.get("https://blazedemo.com/user/id/personalPage").assert_ok()
        http.get("https://blazedemo.com/user/id/getPersonalData").assert_ok()

    http.get("https://blazedemo.com/users/all").assert_ok()
```
At the same time requests to `users/all` page will be executed outside of transaction even if something inside transaction fails.

Transaction defines the name for the block of code. This name with execution results of this particular block will be displayed in the output report.

#### Smart transactions

`smart_transaction` is advanced option for test flow control (stop or continue after failed test method).
Let see another test method example:

```python
class Tests(TestCase):
    def test_available_pages():
        http.get("https://blazedemo.com/").assert_ok()
        http.get("https://blazedemo.com/users").assert_ok()
    
        http.get("https://blazedemo.com/users/search").assert_ok()
        http.get("https://blazedemo.com/users/count").assert_ok()
        http.get("https://blazedemo.com/users/login").assert_ok()

        http.get("https://blazedemo.com/contactUs").assert_ok()
        http.get("https://blazedemo.com/copyright").assert_ok()
```
In this case we have multiple requests divided into blocks. I do not want to test pages under `users` space if it is not available.
For this purpose we can use `smart_transaction`.

```python
class Tests(TestCase):
    def setUp(self):
        apiritif.put_into_thread_store(func_mode=True)
    
    def test_available_pages():
        http.get("https://blazedemo.com/").assert_ok()

        with apiritif.smart_transaction('Availability check'):
            http.get("https://blazedemo.com/users").assert_ok()
    
        with apiritif.smart_transaction('Test users pages'):
            http.get("https://blazedemo.com/users/search").assert_ok()
            http.get("https://blazedemo.com/users/count").assert_ok()
            http.get("https://blazedemo.com/users/login").assert_ok()

        http.get("https://blazedemo.com/contactUs").assert_ok()
        http.get("https://blazedemo.com/copyright").assert_ok()
```
Now this two blocks are wrapped into `smart_transaction` which would help with error test flow handling and logging.

Also each transaction defines the name for the block of code and will be displayed in the output report.
 
Now about `apiritif.put_into_thread_store(func_mode=True)`, this is test execution mode for apiritif.
We can execute all of the transactions in test no matter what or stop after first failed transaction.
This flag tells to apiritif "Stop execution if some transaction failed". `False` says "Run till the end in any case".


## CSV Reader
In order to use data from csv file as test parameters Apiritif provides two different csv readers.
Simple `CSVReader` helps you to read data from file line by line and use this data wherever you need:

```python
data_reader = apiritif.CSVReader('---path to required file---')
class Tests(TestCase):
    def test_user_page():
        data_reader.read_vars()
        vars = data_reader.get_vars()
        http.get("https://blazedemo.com/users/" + vars.user_id).assert_ok()
```

In case of multithreading testing you may need to deviate data between threads and ysu uniq lines for each thread.
`CSVReaderPerThread` helps to solve this problem: 

```python
data_per_thread_reader = apiritif.CSVReaderPerThread('---path to required file---')
class Tests(TestCase):
    def setUp(self):
        data_per_thread_reader.read_vars()
        self.vars = data_per_thread_reader.get_vars()
    
    def test_user_page():
        http.get("https://blazedemo.com/users/" + self.vars.user_id).assert_ok()
```

## Execution results

Apiritif writes output data from tests in `apiritif.#.csv` files by default. Here `#` is number of executing process.
The output file is similar to this:
```csv
timeStamp,elapsed,Latency,label,responseCode,responseMessage,success,allThreads,bytes
1602759519185,0,0,Correct test,,,true,0,2
1602759519186,0,0,Correct transaction,,,true,0,2
1602759519187,0,0,Test with exception,,Exception: Horrible error,false,0,2
```  
It contains test and transaction results for executed tests by one process.

## Taurus Integration

TODO: describe that Taurus can extract Apiritif's action log and handle it.

## Logging

TODO: Describe that Apiritif creates 'apiritif' logger that can be used to
debug http requests and write test interactively.

TODO: describe how to silence Apiritif logging.

### Environment Variables

There are environment variables to control length of response/request body to be written into traces and logs:
  * `APIRITIF_TRACE_BODY_EXCLIMIT` - limit of body part to include into exception messages, default is 1024
  * `APIRITIF_TRACE_BODY_HARDLIMIT` - limit of body length to include into JSON trace records, default is unlimited
