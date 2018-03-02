# Changelog

## 0.6.1 <sup>2 mar 2018</sup>
- correcting release

## 0.6 <sup>2 mar 2018</sup>

- add utility functions: `encode_url()`, `base64_encode()`, `base64_decode()` and `uuid()`
- fix sample handling (statuses, error messages, assertions) for nested transactions
- add `assertions` field to samples
- fix `responseMessage` JTL field writing in load testing mode

## 0.5 <sup>10 nov 2017</sup>

- add utility functions: `format_date()`, `random_uniform()`, `random_gauss()` and `random_string()`
- add loadgen utility


## 0.3 <sup>3 may 2017</sup>

- allow attaching data and status to `transaction` from code


## 0.2 <sup>29 apr 2017</sup>

- fix package requirement
- refactor HTTPResponse class to contain data fields


## 0.1 <sup>25 apr 2017</sup>

- extract as standalone project from Taurus


# Roadmap / Ideas

- have field in response for parsed JSON 
- handle file upload requests - give sugar 
- complete endpoint concept with path component
- support arbitrary python code pieces
