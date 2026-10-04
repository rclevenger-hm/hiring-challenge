# longest completed Mars mission

[Back to the README](README.md) · [Hardened version](lcm_mars_hardened.md) · [Original challenge](mission_challenge.md)

I kept this close to the original awk solution. The job is to find one maximum in a documented log format, so a single pass and a couple of variables are enough.

## Run it

Put `lcm_mars.sh` next to the log and run:

```sh
sh lcm_mars.sh
```

Or pass a different path:

```sh
sh lcm_mars.sh /path/to/space_missions.log
```

From PowerShell with Git for Windows installed in its default location:

```powershell
& "C:\Program Files\Git\bin\bash.exe" ./lcm_mars.sh ./space_missions.log
```

This file is a shell script that invokes awk. `gawk -f lcm_mars.sh` will fail because the file also contains shell syntax. The script already sets `LC_ALL=C`.

Without an argument, it reads `space_missions.log` from the current directory. It prints only the security code. On the supplied log, the result is:

```text
XRT-421-ZQP
```

## Why I chose this approach

I use `/Mars/` as a cheap first check. Lines without that text never reach the field checks. Inside that block, I check for `Completed` and reject comments before accessing any fields. That gives awk a chance to avoid splitting most of the file.

Those first checks are only filters. The checks on fields 3 and 4 still require the full values to be `Mars` and `Completed`, allowing whitespace around them. That keeps `Marsville`, `Not Completed`, or `Mars` in a mission ID from qualifying by themselves. Indented comments are skipped too.

The nested shape reads naturally to me: cheap filter, then exact checks, then update the winner. Earlier measurements gave a reason to keep it, but the small timing differences between similar awk layouts depend on the interpreter. I would be fine flattening it if that was the team's preference.

I split on the pipe itself, rather than using a more complicated separator that also consumes whitespace. Awk's numeric conversion handles the padding around the duration. I remove whitespace from the winning code once, at the end.

`max = -1` is the small fix here. Starting at zero would miss a qualifying zero-day mission. With `-1`, zero can become the winner, assuming durations are nonnegative.

`LC_ALL=C` makes the character handling predictable for this ASCII log. The shell wrapper quotes the input path and feeds it through standard input, so filenames with spaces work and awk does not interpret the filename as an option or a variable assignment.

None of these choices depend on knowing the winning code, duration, or line number. The script scans the whole file and finds the maximum from the records it reads.

## Known caveats

I am relying on the documented record format instead of making this a general-purpose log validator.

- `$6 + 0` accepts a numeric prefix. A value like `9994d` becomes `9994`. A blank or nonnumeric value can become zero, which can now win if no positive duration qualifies.
- Equal maximum durations keep the first matching row. There is no tie warning.
- No qualifying row produces a blank line and a successful exit. A file that cannot be opened is a separate shell error.
- There is no field-count check. Extra fields are not rejected, and missing or shifted fields can produce a wrong or blank result.
- The column positions are fixed. The script ignores `# Format:` as a comment; it does not use the header to discover columns.
- Dates, crew sizes, success rates, and security-code structure are not validated. For this task, `Completed` defines success; there is no additional success-rate threshold.
- The final `gsub` removes all whitespace from the code, including whitespace inside it. That matches the expected `ABC-123-XYZ` shape, but it would silently join a malformed code containing spaces.
- The C locale covers the ASCII whitespace expected here, including tabs and carriage returns. It is not intended to normalize every Unicode space character.

For a production tool, I would decide how invalid rows, ties, and no matches should behave before adding checks. For this challenge, these assumptions keep the solution small and easy to explain.

## Performance test

Measured on October 4, 2026, in the provided Linux execution environment. The test ran the actual shell script against the supplied log.

| Item | Result |
| --- | --- |
| Input size | 10,151,813 bytes, about 10.15 MB |
| Input lines | 105,032 |
| Mission records | 100,000 |
| Awk | mawk 1.3.4, build 20240123 |
| Shell | dash, invoked through `sh` |
| Environment | Linux x86-64; reported CPU model AMD EPYC 9V74 |
| Warmup runs | 5 |
| Measured runs | 50 |
| Median | 8.34 ms |
| Mean | 8.48 ms |
| 95th percentile, nearest rank | 10.04 ms |
| Fastest / slowest | 7.54 / 11.22 ms |
| Runs at or below 200 ms | 50 of 50 |

Python's `time.perf_counter_ns()` measured elapsed time around each fresh `sh lcm_mars.sh <log-path>` process. That includes process startup, the shell, awk, and captured output. Every run exited successfully and printed the expected code.

These are warm-cache results on this machine. They do not measure cold disk reads, establish a speedup over another solution, or guarantee the same timing with another awk. No memory benchmark or 100 GB test was run.

I also checked shell syntax and a small input containing a zero-day winner, regular and indented comments, misleading destination/status values, tabs, and CRLF endings. The script selected the zero-day row correctly. Both the default filename and an explicit path containing spaces worked.

The script reads the input once and keeps only the current maximum and winning code, plus awk's current record and fields. Its working state does not grow with the number of rows, though an unusually long individual line still needs memory. At 100 GB, I would measure storage throughput and the actual awk implementation before deciding whether parallel workers were worth adding.

## Repeat the timing locally

This needs Python 3 and uses the same five warmups and fifty measured runs:

```sh
python3 - <<'PY'
import statistics
import subprocess
import time

command = ["sh", "lcm_mars.sh", "space_missions.log"]
reference = None
for _ in range(5):
    result = subprocess.run(command, capture_output=True, check=True)
    reference = result.stdout

samples = []
for _ in range(50):
    start = time.perf_counter_ns()
    result = subprocess.run(command, capture_output=True, check=True)
    samples.append((time.perf_counter_ns() - start) / 1_000_000)
    assert result.stdout == reference

print("Output:", reference.decode().strip())
print(f"Median: {statistics.median(samples):.2f} ms")
print(f"Mean: {statistics.mean(samples):.2f} ms")
print(f"P95: {sorted(samples)[47]:.2f} ms")
print(f"Range: {min(samples):.2f}–{max(samples):.2f} ms")
PY
```

The repeat-timing snippet checks that output stays consistent. Correctness is checked separately by the tests below.

## Automated checks

The `Mission checks` workflow runs on pushes to `dev` and pull requests targeting `dev` or `main`.

- Shell syntax and ShellCheck cover both shell scripts. Ruff checks the Python test and benchmark code, and actionlint checks the workflow itself.
- Both scripts run the same 11 core test methods with mawk and gawk. They cover the supplied log, a new winner appended to it, numeric ordering, exact field matching, comments, whitespace, CRLF, zero days, ties, no matches, filenames, and missing input. Tie and no-match expectations follow each script's documented behavior. The hardened script also runs its own expanded edge cases; those are skipped for this short version.
- Each script gets a performance job using mawk, with 5 warmups and 50 measured runs. The median must be below 20 ms. Every run must also return the full expected output, exit successfully, and leave stderr empty on the supplied log.

I use the median for the timing limit because an occasional slow run on a shared runner does not say much about the script. The report still includes the slowest run and P95. This is a broad regression check, not a promise that every invocation finishes within 200 ms or a comparison against earlier runs.

The run summary shows the timings. The downloadable benchmark artifact contains every sample, interpreter details, input and script hashes, and the commit being tested. Reports are kept for 30 days, including when the timing limit fails.

The expected code belongs in the checks for the supplied fixture; it is not in the solution. The test that appends a different winning mission helps catch an implementation that just prints the known answer. The tests follow the behavior documented above. They do not require the script to reject every malformed record.

Run these from the repository root on Linux or another environment with Python 3.9+, `sh`, and awk:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/benchmark.py --warmups 5 --runs 50 --max-median-ms 20
```

These commands default to the short script. Use `MISSION_SCRIPT=lcm_mars_hardened.sh` before the test command and `--script lcm_mars_hardened.sh` with the benchmark to check the other version. See the [hardened guide](lcm_mars_hardened.md#tests-and-performance) for complete commands.

The benchmark runs whichever `awk` is on `PATH` and records its resolved path and version. CI selects the named interpreter through a temporary `awk` symlink, so the solution does not need a new interpreter flag. To time a different log, pass `--log path/to/file.log --expected-code ABC-123-XYZ` with that file's independently checked result.

For local lint, install ShellCheck, Ruff 0.16.10, and actionlint 1.7.12, then run:

```sh
sh -n lcm_mars.sh
sh -n lcm_mars_hardened.sh
shellcheck --shell=sh lcm_mars.sh lcm_mars_hardened.sh
ruff check scripts tests
actionlint
```

The workflow uses read-only repository permissions and pinned action revisions. Shell files are checked out with LF endings so a Windows checkout does not change the shell script's line endings.
