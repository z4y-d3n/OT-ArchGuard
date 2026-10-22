# Installation and offline use

Python 3.12 is the minimum. Consult [verification results](verification.md)
for the tested Windows interpreters. Use a regular installed package, not
an editable import, for release acceptance. Full executable paths avoid activation.

For offline installation, prepare a compatible wheelhouse on an authorized
connected machine, retaining dependency distributions and license files.
No wheelhouse or environment is included in the source project.

~~~powershell
.\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse otarchguard==1.0.1
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\otarchguard.exe --version
.\.venv\Scripts\otarchguard.exe --help
~~~

Native dependency wheels must match Python/OS/CPU. Installation may need acquired
dependencies; runtime analysis/reports remain offline. See [README](../README.md),
[reporting](reporting.md) and [testing](testing-strategy.md).
