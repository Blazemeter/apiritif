# Changelog

## 0.9.3 <sup>03 May 2020</sup>
- fix cookies processing
- fix threads closing

## 0.9.2 <sup>24 Feb 2020</sup>
- generalize handler interface

## 0.9.1 <sup>17 Jan 2020</sup>
- use zero iterations as infinite
 
## 0.9.0 <sup>29 Oct 2019</sup>
- add smart_transaction block
- add transaction handlers ability

## 0.8.2 <sup>13 Aug 2019</sup>
- fix setup errors logging

## 0.8.1 <sup>22 feb 2018</sup>
- fix threading flow, provide api for using thread-specific storage

## 0.8.0 <sup>19 feb 2018</sup>
- add CSV readers (by @greyfenrir)

## 0.7.0 <sup>20 Dec 2018</sup>
- extend transaction API to provide a way to set start/end time
- introduce `python -m apiritif` launcher

## 0.6.7 <sup>8 Aug 2018</sup>
- fix unicode-related crash for LDJSON-based report
- be more defensive against possible multiprocessing errors, prevent crashing

## 0.6.6 <sup>7 Aug 2018</sup>
- unicode-related fixings for CSV reports
- support CONNECT and OPTIONS methods
- fixup multiprocessing crash

## 0.6.5 <sup>22 May 2018</sup>
- record transactions start/end in logs for Taurus

## 0.6.4 <sup>17 may 2018</sup>
- record iteration beginning/end in logs for Taurus

## 0.6.3 <sup>25 apr 2018</sup>
- correct sample writing in load testing mode

## 0.6.2 <sup>25 apr 2018</sup>
- use correct `latency`/`responseTime` fields format in sample's extras
- write test `path` (used to identify parts of test) to be used by Taurus

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
