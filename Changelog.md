# Changelog

## 1.1.4 (22 Feb 2025)

- fix exception handling

## 1.1.3 (22 Feb 2022)

- fix exception handling
- redesign plugin hooks (to nose2 style)

## 1.1.2 (26 Jan 2022)

- fix logging

## 1.1.1 (26 Jan 2022)

- fix empty result handling

## 1.1.0 (26 Jan 2022)

- migrate to Nose2
- fix recording parsing errors
- fix deprecated params

## 1.0.0 (27 Sep 2021)

- add Nose Flow Control
- add GRACEFUL shutdown feature
- add version option

## 0.9.8 (06 Jul 2021)

- fix handlers interface
- add 'graceful shutdown' option

## 0.9.7 (15 Jun 2021)

- add external handlers feature

## 0.9.6 (15 Jan 2021)

- support client-side certificates
- improve error trace info
- fix problem of binary POST tracing
- detect delimiter in csv files automatically

## 0.9.5 (01 Sep 2020)

- add quoting auto detection feature
- add ability to log actions externally
- extend trace context

## 0.9.4 (17 Jul 2020)

- improve csv encoding
- fix assertion trace for multi-asserts
- add 'assert_status_code_in' assertion
- migrate onto modern jsonpath_ng
- add lxml for cssselect
- add CSSSelect assertion

## 0.9.3 (03 May 2020)

- fix cookies processing
- fix threads closing

## 0.9.2 (24 Feb 2020)

- generalize handler interface

## 0.9.1 (17 Jan 2020)

- use zero iterations as infinite

## 0.9.0 (29 Oct 2019)

- add smart_transaction block
- add transaction handlers ability

## 0.8.2 (13 Aug 2019)

- fix setup errors logging

## 0.8.1 (22 Feb 2018)

- fix threading flow, provide api for using thread-specific storage

## 0.8.0 (19 Feb 2018)

- add CSV readers (by @greyfenrir)

## 0.7.0 (20 Dec 2018)

- extend transaction API to provide a way to set start/end time
- introduce `python -m apiritif` launcher

## 0.6.7 (8 Aug 2018)

- fix unicode-related crash for LDJSON-based report
- be more defensive against possible multiprocessing errors, prevent crashing

## 0.6.6 (7 Aug 2018)

- unicode-related fixings for CSV reports
- support CONNECT and OPTIONS methods
- fixup multiprocessing crash

## 0.6.5 (22 May 2018)

- record transactions start/end in logs for Taurus

## 0.6.4 (17 May 2018)

- record iteration beginning/end in logs for Taurus

## 0.6.3 (25 Apr 2018)

- correct sample writing in load testing mode

## 0.6.2 (25 Apr 2018)

- use correct `latency`/`responseTime` fields format in sample's extras
- write test `path` (used to identify parts of test) to be used by Taurus

## 0.6.1 (2 Mar 2018)

- correcting release

## 0.6 (2 Mar 2018)

- add utility functions: `encode_url()`, `base64_encode()`, `base64_decode()` and `uuid()`
- fix sample handling (statuses, error messages, assertions) for nested transactions
- add `assertions` field to samples
- fix `responseMessage` JTL field writing in load testing mode

## 0.5 (10 Nov 2017)

- add utility functions: `format_date()`, `random_uniform()`, `random_gauss()` and `random_string()`
- add loadgen utility

## 0.3 (3 May 2017)

- allow attaching data and status to `transaction` from code

## 0.2 (29 Apr 2017)

- fix package requirement
- refactor HTTPResponse class to contain data fields

## 0.1 (25 Apr 2017)

- extract as standalone project from Taurus

## Roadmap / Ideas

- have field in response for parsed JSON
- handle file upload requests - give sugar
- complete endpoint concept with path component
- support arbitrary python code pieces
