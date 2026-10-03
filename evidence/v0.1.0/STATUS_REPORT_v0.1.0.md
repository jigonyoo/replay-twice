# STATUS_REPORT — replay-twice

## Built

- Installable library, pytest entry point, replay fixture and decorator.
- Named duplicate-delivery, timeout-retry, concurrent and acknowledgement-loss drills.
- Scripted agent loop, SQLite tool and webhook handlers, runnable examples.
- Markdown/JSON matrix with separate runs, exact ranges and individual observations.
- Offline unit tests, transaction rollback checks and pytester subprocess tests.
- English README, MIT license, packaging and exact command evidence.

The reference projects were read for context; their implementation was not copied.
No GitHub repository, push, PyPI upload, publication, outbound message, token
input or paid model/API call was performed.

## Known limits

Effects are real invocations in the user-supplied handler. The bundled handlers
use a synthetic SQLite ledger. The timeout and crash scenarios hide a completed
call's response; they do not terminate a process or exercise a real transport.
Threads and local SQLite do not cover distributed execution, external payment
providers, other DB isolation levels, power loss or every scheduling interleaving.
An observer that counts claims instead of committed effects can give false assurance.
Fresh keys/stores are required between trials. The race delay is intentional.
Concurrency results may vary even with the same seed.

## Blocked locations

Initial dependency download could not resolve the package index inside the
sandbox. The allowed public dependency download then succeeded and offline
installation used the saved wheels. There is no remaining blocker in the
recorded acceptance run. Download errors are preserved below.

## Filesystem scope incident

The initial network dependency download did not pin pip's cache to this
project. A read-only audit confirmed a copy of the downloaded wheel in the
default cache outside the project, matching the wheel's SHA256. Earlier build
and test setup also used the system temporary directory. This did not meet the
requested restriction that writes stay inside this project. Later setup and
acceptance commands pinned PIP_CACHE_DIR and TMPDIR to directories here.
The external cache was not deleted or moved because external writes and file
deletion were prohibited. The evidence is preserved in cache-scope-audit.txt.

## Not done

Publishing and repository creation were prohibited and were not attempted.
No real payment provider or customer flow was tested. Python compatibility
beyond the recorded local interpreters is a declared requirement rather than
a claim of measurements on every supported release.

## Commands and original output

### acceptance-current.txt

````text
$ env PIP_NO_INDEX=1 'PIP_FIND_LINKS=<project>/wheels' 'PIP_CACHE_DIR=<project>/.pip-cache' 'TMPDIR=<project>/.tmp' zsh -c 'source .venv-current/bin/activate && pip install -e . && pytest -q && replay-twice report'
Looking in links: <project>/wheels
Obtaining file://<project>
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Getting requirements to build editable: started
  Getting requirements to build editable: finished with status 'done'
  Preparing editable metadata (pyproject.toml): started
  Preparing editable metadata (pyproject.toml): finished with status 'done'
Processing ./wheels/pytest-9.1.1-py3-none-any.whl
Processing ./wheels/packaging-26.3-py3-none-any.whl
Processing ./wheels/pluggy-1.6.0-py3-none-any.whl
Processing ./wheels/pygments-2.21.0-py3-none-any.whl
Processing ./wheels/iniconfig-2.3.0-py3-none-any.whl
Processing ./wheels/tomli-2.4.1-py3-none-any.whl
Processing ./wheels/exceptiongroup-1.3.1-py3-none-any.whl
Processing ./wheels/typing_extensions-4.16.0-py3-none-any.whl
Building wheels for collected packages: replay-twice
  Building editable for replay-twice (pyproject.toml): started
  Building editable for replay-twice (pyproject.toml): finished with status 'done'
  Created wheel for replay-twice: filename=replay_twice-0.1.0-0.editable-py3-none-any.whl size=6784 sha256=b86515242e1a8618d957cafbbe191a16b24c4fc89a8cd635821c56a16af03a85
  Stored in directory: <project>/.tmp/pip-ephem-wheel-cache-2gf07r_g/wheels/92/d0/32/0127026f4ca118fb94bbb5bd80471a0bfe6b838cb0ccb254ff
Successfully built replay-twice
Installing collected packages: typing-extensions, tomli, pygments, pluggy, packaging, iniconfig, exceptiongroup, pytest, replay-twice
Successfully installed exceptiongroup-1.3.1 iniconfig-2.3.0 packaging-26.3 pluggy-1.6.0 pygments-2.21.0 pytest-9.1.1 replay-twice-0.1.0 tomli-2.4.1 typing-extensions-4.16.0
.........................                                                [100%]
25 passed in 1.91s
# replay-twice measurements

Concurrency can vary across runs. Seed controls event IDs, not thread scheduling. check_then_act deliberately sleeps between reading and writing. SQLite ledger rows are simulated effects; no payment API is called.

Environment:

```json
{
  "os": "macOS-26.6.2-arm64-arm-64bit",
  "python": "3.10.22",
  "package_version": "0.1.0",
  "seed": 0,
  "threads": 8,
  "concurrent_repeats": 200,
  "runs": 3,
  "race_delay_seconds": 0.001,
  "utc": "2026-10-03T12:44:37.613702+00:00"
}
```

Ranges below are exact minimum–maximum counts across the recorded runs.

| Flow | Handler | Scenario | Trials/run | Duplicate trials/run range | Failed trials/run range | Effects observed |
|---|---|---|---:|---:|---:|---|
| refund | naive | duplicate | 1 | 1–1 | 1–1 | [2] |
| refund | naive | timeout_retry | 1 | 1–1 | 1–1 | [2] |
| refund | naive | concurrent | 200 | 200–200 | 200–200 | [8] |
| refund | naive | crash_before_ack | 1 | 1–1 | 1–1 | [2] |
| refund | check_then_act | duplicate | 1 | 0–0 | 0–0 | [1] |
| refund | check_then_act | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| refund | check_then_act | concurrent | 200 | 200–200 | 200–200 | [8] |
| refund | check_then_act | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
| refund | guarded | duplicate | 1 | 0–0 | 0–0 | [1] |
| refund | guarded | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| refund | guarded | concurrent | 200 | 0–0 | 0–0 | [1] |
| refund | guarded | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | naive | duplicate | 1 | 1–1 | 1–1 | [2] |
| payment.succeeded | naive | timeout_retry | 1 | 1–1 | 1–1 | [2] |
| payment.succeeded | naive | concurrent | 200 | 200–200 | 200–200 | [8] |
| payment.succeeded | naive | crash_before_ack | 1 | 1–1 | 1–1 | [2] |
| payment.succeeded | check_then_act | duplicate | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | check_then_act | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | check_then_act | concurrent | 200 | 200–200 | 200–200 | [6, 8] |
| payment.succeeded | check_then_act | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | duplicate | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | concurrent | 200 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
JSON: reports/report-20261003T124437615309Z.json
Markdown: reports/report-20261003T124437615309Z.md

[exit_code=0]
````

### acceptance.txt

````text
$ env PIP_NO_INDEX=1 'PIP_FIND_LINKS=<project>/wheels' 'PIP_CACHE_DIR=<project>/.pip-cache' 'TMPDIR=<project>/.tmp' zsh -c 'source .venv-acceptance/bin/activate && pip install -e . && pytest -q && replay-twice report'
Looking in links: <project>/wheels
Obtaining file://<project>
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Getting requirements to build editable: started
  Getting requirements to build editable: finished with status 'done'
  Preparing editable metadata (pyproject.toml): started
  Preparing editable metadata (pyproject.toml): finished with status 'done'
Processing ./wheels/pytest-9.1.1-py3-none-any.whl (from replay-twice==0.1.0)
Processing ./wheels/iniconfig-2.3.0-py3-none-any.whl (from pytest>=7->replay-twice==0.1.0)
Processing ./wheels/packaging-26.3-py3-none-any.whl (from pytest>=7->replay-twice==0.1.0)
Processing ./wheels/pluggy-1.6.0-py3-none-any.whl (from pytest>=7->replay-twice==0.1.0)
Processing ./wheels/pygments-2.21.0-py3-none-any.whl (from pytest>=7->replay-twice==0.1.0)
Building wheels for collected packages: replay-twice
  Building editable for replay-twice (pyproject.toml): started
  Building editable for replay-twice (pyproject.toml): finished with status 'done'
  Created wheel for replay-twice: filename=replay_twice-0.1.0-0.editable-py3-none-any.whl size=6015 sha256=88d0b96262bea9b22b5ff7256fda05f23353938afc05da3d0c6856f2ee08e3a2
  Stored in directory: <project>/.tmp/pip-ephem-wheel-cache-0r3jw5wn/wheels/0d/f6/64/cd76b5d99a1b7c935537bb81570b41d89161011fdbd15b0760
Successfully built replay-twice
Installing collected packages: pygments, pluggy, packaging, iniconfig, pytest, replay-twice
Successfully installed iniconfig-2.3.0 packaging-26.3 pluggy-1.6.0 pygments-2.21.0 pytest-9.1.1 replay-twice-0.1.0
.........................                                                [100%]
25 passed in 1.89s
# replay-twice measurements

Concurrency can vary across runs. Seed controls event IDs, not thread scheduling. check_then_act deliberately sleeps between reading and writing. SQLite ledger rows are simulated effects; no payment API is called.

Environment:

```json
{
  "os": "macOS-26.6.2-arm64-arm-64bit",
  "python": "3.12.14",
  "package_version": "0.1.0",
  "seed": 0,
  "threads": 8,
  "concurrent_repeats": 200,
  "runs": 3,
  "race_delay_seconds": 0.001,
  "utc": "2026-10-03T12:25:47.407248+00:00"
}
```

Ranges below are exact minimum–maximum counts across the recorded runs.

| Flow | Handler | Scenario | Trials/run | Duplicate trials/run range | Failed trials/run range | Effects observed |
|---|---|---|---:|---:|---:|---|
| refund | naive | duplicate | 1 | 1–1 | 1–1 | [2] |
| refund | naive | timeout_retry | 1 | 1–1 | 1–1 | [2] |
| refund | naive | concurrent | 200 | 200–200 | 200–200 | [8] |
| refund | naive | crash_before_ack | 1 | 1–1 | 1–1 | [2] |
| refund | check_then_act | duplicate | 1 | 0–0 | 0–0 | [1] |
| refund | check_then_act | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| refund | check_then_act | concurrent | 200 | 200–200 | 200–200 | [6, 7, 8] |
| refund | check_then_act | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
| refund | guarded | duplicate | 1 | 0–0 | 0–0 | [1] |
| refund | guarded | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| refund | guarded | concurrent | 200 | 0–0 | 0–0 | [1] |
| refund | guarded | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | naive | duplicate | 1 | 1–1 | 1–1 | [2] |
| payment.succeeded | naive | timeout_retry | 1 | 1–1 | 1–1 | [2] |
| payment.succeeded | naive | concurrent | 200 | 200–200 | 200–200 | [8] |
| payment.succeeded | naive | crash_before_ack | 1 | 1–1 | 1–1 | [2] |
| payment.succeeded | check_then_act | duplicate | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | check_then_act | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | check_then_act | concurrent | 200 | 200–200 | 200–200 | [3, 4, 7, 8] |
| payment.succeeded | check_then_act | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | duplicate | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | concurrent | 200 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
JSON: reports/report-20261003T122547407694Z.json
Markdown: reports/report-20261003T122547407694Z.md

[exit_code=0]
````

### agent.txt

````text
$ .venv/bin/python examples/agent_loop.py
naive: effects=2, trace=['tool_call', 'timeout', 'retry_same_arguments', 'tool_call', 'tool_result']
check_then_act: effects=1, trace=['tool_call', 'timeout', 'retry_same_arguments', 'tool_call', 'tool_result']
guarded: effects=1, trace=['tool_call', 'timeout', 'retry_same_arguments', 'tool_call', 'tool_result']

[exit_code=0]
````

### cache-scope-audit.txt

````text
$ .venv-current/bin/python -c 'from pathlib import Path; import hashlib; log=Path("evidence/download-network.txt"); end=log.stat().st_mtime; target=Path("wheels/wheel-0.48.0-py3-none-any.whl"); digest=hashlib.sha256(target.read_bytes()).hexdigest(); cache=Path("~/Library/Caches/pip"); matches=[]; recent=[]; print("checked cache:",cache); print("download log mtime:",end); print("downloaded wheel SHA256:",digest); 
for p in cache.rglob("*"):
    if p.is_file() and end-10 <= p.stat().st_mtime <= end+2:
        recent.append(str(p.relative_to(cache)))
        if p.stat().st_size == target.stat().st_size and hashlib.sha256(p.read_bytes()).hexdigest()==digest:
            matches.append(str(p.relative_to(cache)))
print("recent cache files:",recent); print("wheel-matching cache files:",matches)'
checked cache: ~/Library/Caches/pip
download log mtime: 1791029924.7957897
downloaded wheel SHA256: 3217dcc807155e45db462d7ef2431f5ddda0d7273b700d05a67b271ceb1287ab
recent cache files: ['http-v2/0/7/5/9/3/07593bb905dded4b84aacb1d96c1e64704669d6bab658dcaeab79c36', 'http-v2/0/c/2/1/8/0c218d526767991766d9b365a4f3e4449ce3579fd8b0f96a707d5a52', 'http-v2/0/4/1/8/c/0418c83b80f7f7bfaec2738bfbbee53d2c1562196c0781702f6eddc8', 'http-v2/7/a/5/f/7/7a5f717e7b3fb99ec006f4d173aad55224eb063005c662c586ba0518', 'http-v2/1/8/3/9/9/1839911afa3a298741e207e7e99aea7177030d328debd377548f19e2.body', 'http-v2/1/8/3/9/9/1839911afa3a298741e207e7e99aea7177030d328debd377548f19e2', 'http-v2/a/1/9/5/3/a19537d3cf37c122db841d6fe4cd322bc10d1a558bb00d146b85cb9a.body', 'http-v2/a/1/9/5/3/a19537d3cf37c122db841d6fe4cd322bc10d1a558bb00d146b85cb9a', 'http-v2/d/8/c/d/8/d8cd8c62e690ab29b773948431329e5f9e2455966700cac81c8b0ff3', 'http-v2/d/8/c/d/8/d8cd8c62e690ab29b773948431329e5f9e2455966700cac81c8b0ff3.body', 'http-v2/4/d/2/7/2/4d272e6453941ce8b0a37a02cdb1685fc612c33441fa74691fb40656', 'http-v2/4/d/2/7/2/4d272e6453941ce8b0a37a02cdb1685fc612c33441fa74691fb40656.body', 'http-v2/4/4/e/5/b/44e5b11a6caa92636d8ccfe658d420ba4ed8f67f7f4e835b214255aa', 'http-v2/4/4/e/5/b/44e5b11a6caa92636d8ccfe658d420ba4ed8f67f7f4e835b214255aa.body', 'http-v2/3/3/9/7/4/33974f84394d9a943f68359da08431dab4af9f86c33962982ea21b5f', 'selfcheck/41471adbd50165900ffb3f6dbbd337b3ea136f656904e600ed3a9749']
wheel-matching cache files: ['http-v2/d/8/c/d/8/d8cd8c62e690ab29b773948431329e5f9e2455966700cac81c8b0ff3.body']

[exit_code=0]
````

### create-acceptance-venv.txt

````text
$ .venv/bin/python -m venv .venv-acceptance

[exit_code=0]
````

### create-current-venv.txt

````text
$ '<review-dir>/runtimes/cpython-3.10.22-macos-aarch64-none/bin/python3.10' -m venv .venv-current

[exit_code=0]
````

### create-venv.txt

````text
$ ~/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m venv .venv

[exit_code=0]
````

### download-network.txt

````text
$ python3 -m pip download --dest wheels pytest setuptools wheel
WARNING: Cache entry deserialization failed, entry ignored
Collecting pytest
  Using cached pytest-9.1.1-py3-none-any.whl.metadata (7.6 kB)
Collecting setuptools
  Using cached setuptools-84.0.0-py3-none-any.whl.metadata (6.6 kB)
Collecting wheel
  Downloading wheel-0.48.0-py3-none-any.whl.metadata (2.3 kB)
Collecting iniconfig>=1.0.1 (from pytest)
  Using cached iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
WARNING: Cache entry deserialization failed, entry ignored
Collecting packaging>=22 (from pytest)
  Using cached packaging-26.3-py3-none-any.whl.metadata (3.5 kB)
Collecting pluggy<2,>=1.5 (from pytest)
  Using cached pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
Collecting pygments>=2.7.2 (from pytest)
  Using cached pygments-2.21.0-py3-none-any.whl.metadata (2.5 kB)
Using cached pytest-9.1.1-py3-none-any.whl (386 kB)
Using cached pluggy-1.6.0-py3-none-any.whl (20 kB)
Using cached setuptools-84.0.0-py3-none-any.whl (818 kB)
Downloading wheel-0.48.0-py3-none-any.whl (33 kB)
Using cached iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
Using cached packaging-26.3-py3-none-any.whl (129 kB)
Using cached pygments-2.21.0-py3-none-any.whl (1.3 MB)
Saved ./wheels/pytest-9.1.1-py3-none-any.whl
Saved ./wheels/pluggy-1.6.0-py3-none-any.whl
Saved ./wheels/setuptools-84.0.0-py3-none-any.whl
Saved ./wheels/wheel-0.48.0-py3-none-any.whl
Saved ./wheels/iniconfig-2.3.0-py3-none-any.whl
Saved ./wheels/packaging-26.3-py3-none-any.whl
Saved ./wheels/pygments-2.21.0-py3-none-any.whl
Successfully downloaded pytest pluggy setuptools wheel iniconfig packaging pygments

[notice] A new release of pip is available: 26.1.1 -> 26.2.1
[notice] To update, run: python3 -m pip install --upgrade pip

[exit_code=0]
````

### download.txt

````text
$ python3 -m pip download --dest wheels pytest setuptools wheel
WARNING: The directory '~/Library/Caches/pip' or its parent directory is not owned or is not writable by the current user. The cache has been disabled. Check the permissions and owner of that directory. If executing pip with sudo, you should use sudo's -H flag.
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("HTTPSConnection(host='pypi.org', port=443): Failed to resolve 'pypi.org' ([Errno 8] nodename nor servname provided, or not known)")': /simple/pytest/
WARNING: Retrying (Retry(total=3, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("HTTPSConnection(host='pypi.org', port=443): Failed to resolve 'pypi.org' ([Errno 8] nodename nor servname provided, or not known)")': /simple/pytest/
WARNING: Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("HTTPSConnection(host='pypi.org', port=443): Failed to resolve 'pypi.org' ([Errno 8] nodename nor servname provided, or not known)")': /simple/pytest/
WARNING: Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("HTTPSConnection(host='pypi.org', port=443): Failed to resolve 'pypi.org' ([Errno 8] nodename nor servname provided, or not known)")': /simple/pytest/
WARNING: Retrying (Retry(total=0, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("HTTPSConnection(host='pypi.org', port=443): Failed to resolve 'pypi.org' ([Errno 8] nodename nor servname provided, or not known)")': /simple/pytest/
ERROR: Could not find a version that satisfies the requirement pytest (from versions: none)
ERROR: No matching distribution found for pytest

[exit_code=1]
````

### entrypoint-metadata.txt

````text
$ .venv-current/bin/python -c 'from importlib.metadata import entry_points,metadata; print("pytest entry point:", list(entry_points(group="pytest11").select(name="replay_twice"))); print("runtime dependencies:", metadata("replay-twice").get_all("Requires-Dist"))'
pytest entry point: [EntryPoint(name='replay_twice', value='replay_twice.plugin', group='pytest11')]
runtime dependencies: ['pytest>=7']

[exit_code=0]
````

### examples.txt

````text
$ .venv/bin/pytest -q examples/test_usage.py
..                                                                       [100%]
2 passed in 0.07s

[exit_code=0]
````

### install.txt

````text
$ env PIP_NO_INDEX=1 'PIP_FIND_LINKS=<project>/wheels' 'PIP_CACHE_DIR=<project>/.pip-cache' .venv/bin/pip install -e .
Looking in links: <project>/wheels
Obtaining file://<project>
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Getting requirements to build editable: started
  Getting requirements to build editable: finished with status 'done'
  Preparing editable metadata (pyproject.toml): started
  Preparing editable metadata (pyproject.toml): finished with status 'done'
Processing ./wheels/pytest-9.1.1-py3-none-any.whl (from replay-twice==0.1.0)
Processing ./wheels/iniconfig-2.3.0-py3-none-any.whl (from pytest>=7->replay-twice==0.1.0)
Processing ./wheels/packaging-26.3-py3-none-any.whl (from pytest>=7->replay-twice==0.1.0)
Processing ./wheels/pluggy-1.6.0-py3-none-any.whl (from pytest>=7->replay-twice==0.1.0)
Processing ./wheels/pygments-2.21.0-py3-none-any.whl (from pytest>=7->replay-twice==0.1.0)
Building wheels for collected packages: replay-twice
  Building editable for replay-twice (pyproject.toml): started
  Building editable for replay-twice (pyproject.toml): finished with status 'done'
  Created wheel for replay-twice: filename=replay_twice-0.1.0-0.editable-py3-none-any.whl size=2614 sha256=4e4e5a719f8438c82e01b9ad66ef2a0aaba282bb748160bf989f320c8edf6d3f
  Stored in directory: /private/var/folders/d5/7w8056vj74l7_p42y38p7_9w0000gn/T/pip-ephem-wheel-cache-tmiahxzv/wheels/0d/f6/64/cd76b5d99a1b7c935537bb81570b41d89161011fdbd15b0760
Successfully built replay-twice
Installing collected packages: pygments, pluggy, packaging, iniconfig, pytest, replay-twice
Successfully installed iniconfig-2.3.0 packaging-26.3 pluggy-1.6.0 pygments-2.21.0 pytest-9.1.1 replay-twice-0.1.0

[exit_code=0]
````

### metadata.txt

````text
$ .venv/bin/python -c 'from importlib.metadata import metadata; from replay_twice import Replay, SCENARIOS; m=metadata("replay-twice"); print("package:", m["Name"]); print("version:", m["Version"]); print("Python requirement:", m["Requires-Python"]); print("runtime dependencies:", m.get_all("Requires-Dist")); print("scenarios:", SCENARIOS); print("default threads:", Replay().threads); print("default repeats:", Replay().repeats); print("demo amount:", 800); print("Want this run against your real refund, charge or webhook flow? Fixed-scope diagnostic from $800 — https://jigonyoo.com")'
package: replay-twice
version: 0.1.0
Python requirement: >=3.10
runtime dependencies: ['pytest>=7']
scenarios: ('duplicate', 'timeout_retry', 'concurrent', 'crash_before_ack')
default threads: 8
default repeats: 1
demo amount: 800
Want this run against your real refund, charge or webhook flow? Fixed-scope diagnostic from $800 — https://jigonyoo.com

[exit_code=0]
````

### pytest-final-current.txt

````text
$ env 'TMPDIR=<project>/.tmp' .venv-current/bin/pytest -q
.........................                                                [100%]
25 passed in 2.00s

[exit_code=0]
````

### pytest-final.txt

````text
$ env 'TMPDIR=<project>/.tmp' .venv-acceptance/bin/pytest -q
.........................                                                [100%]
25 passed in 1.63s

[exit_code=0]
````

### pytest-initial.txt

````text
$ .venv/bin/pytest -q
.........................                                                [100%]
25 passed in 1.81s

[exit_code=0]
````

### report-default.txt

````text
$ .venv/bin/replay-twice report
# replay-twice measurements

Concurrency can vary across runs. Seed controls event IDs, not thread scheduling. check_then_act deliberately sleeps between reading and writing. SQLite ledger rows are simulated effects; no payment API is called.

Environment:

```json
{
  "os": "macOS-26.6.2-arm64-arm-64bit",
  "python": "3.12.14",
  "package_version": "0.1.0",
  "seed": 0,
  "threads": 8,
  "concurrent_repeats": 200,
  "runs": 3,
  "race_delay_seconds": 0.001,
  "utc": "2026-10-03T12:21:54.617281+00:00"
}
```

Ranges below are exact minimum–maximum counts across the recorded runs.

| Flow | Handler | Scenario | Trials/run | Duplicate trials/run range | Failed trials/run range | Effects observed |
|---|---|---|---:|---:|---:|---|
| refund | naive | duplicate | 1 | 1–1 | 1–1 | [2] |
| refund | naive | timeout_retry | 1 | 1–1 | 1–1 | [2] |
| refund | naive | concurrent | 200 | 200–200 | 200–200 | [8] |
| refund | naive | crash_before_ack | 1 | 1–1 | 1–1 | [2] |
| refund | check_then_act | duplicate | 1 | 0–0 | 0–0 | [1] |
| refund | check_then_act | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| refund | check_then_act | concurrent | 200 | 200–200 | 200–200 | [8] |
| refund | check_then_act | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
| refund | guarded | duplicate | 1 | 0–0 | 0–0 | [1] |
| refund | guarded | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| refund | guarded | concurrent | 200 | 0–0 | 0–0 | [1] |
| refund | guarded | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | naive | duplicate | 1 | 1–1 | 1–1 | [2] |
| payment.succeeded | naive | timeout_retry | 1 | 1–1 | 1–1 | [2] |
| payment.succeeded | naive | concurrent | 200 | 200–200 | 200–200 | [8] |
| payment.succeeded | naive | crash_before_ack | 1 | 1–1 | 1–1 | [2] |
| payment.succeeded | check_then_act | duplicate | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | check_then_act | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | check_then_act | concurrent | 200 | 200–200 | 200–200 | [2, 4, 6, 7, 8] |
| payment.succeeded | check_then_act | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | duplicate | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | timeout_retry | 1 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | concurrent | 200 | 0–0 | 0–0 | [1] |
| payment.succeeded | guarded | crash_before_ack | 1 | 0–0 | 0–0 | [1] |
JSON: reports/report-20261003T122154618157Z.json
Markdown: reports/report-20261003T122154618157Z.md

[exit_code=0]
````

### wheels-python310.txt

````text
$ env 'TMPDIR=<project>/.tmp' 'PIP_CACHE_DIR=<project>/.pip-cache' '<review-dir>/.venv/bin/python' -m pip download --dest wheels pytest setuptools wheel
Collecting pytest
  File was already downloaded <project>/wheels/pytest-9.1.1-py3-none-any.whl
Collecting setuptools
  File was already downloaded <project>/wheels/setuptools-84.0.0-py3-none-any.whl
Collecting wheel
  File was already downloaded <project>/wheels/wheel-0.48.0-py3-none-any.whl
Collecting exceptiongroup>=1
  Downloading exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Collecting packaging>=22
  File was already downloaded <project>/wheels/packaging-26.3-py3-none-any.whl
Collecting tomli>=1
  Downloading tomli-2.4.1-py3-none-any.whl (14 kB)
Collecting pluggy<2,>=1.5
  File was already downloaded <project>/wheels/pluggy-1.6.0-py3-none-any.whl
Collecting pygments>=2.7.2
  File was already downloaded <project>/wheels/pygments-2.21.0-py3-none-any.whl
Collecting iniconfig>=1.0.1
  File was already downloaded <project>/wheels/iniconfig-2.3.0-py3-none-any.whl
Collecting typing-extensions>=4.6.0
  Downloading typing_extensions-4.16.0-py3-none-any.whl (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.6/45.6 kB 4.2 MB/s eta 0:00:00
Saved ./wheels/exceptiongroup-1.3.1-py3-none-any.whl
Saved ./wheels/tomli-2.4.1-py3-none-any.whl
Saved ./wheels/typing_extensions-4.16.0-py3-none-any.whl
Successfully downloaded pytest wheel exceptiongroup iniconfig packaging pluggy pygments tomli typing-extensions setuptools

[notice] A new release of pip is available: 23.0.1 -> 26.2.1
[notice] To update, run: <review-dir>/.venv/bin/python -m pip install --upgrade pip

[exit_code=0]
````

## Final full-suite pytest result

```text
$ env 'TMPDIR=<project>/.tmp' .venv-current/bin/pytest -q
.........................                                                [100%]
25 passed in 2.00s

[exit_code=0]
```

Final pytest -q full suite: PASS.
