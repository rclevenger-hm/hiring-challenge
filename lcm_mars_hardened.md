# Hardened Mars mission lookup

[Back to the README](README.md) · [Short version](lcm_mars.md) · [Original challenge](mission_challenge.md)

I kept the short solution and added this as a second option. The short one fits the challenge well. This one is for the extra questions: what if the columns move, a duration is malformed, or a likely typo changes which mission wins?

## Run it

```sh
sh lcm_mars_hardened.sh space_missions.log
```

The filename is optional and defaults to `space_missions.log` in the current directory. From PowerShell with Git for Windows:

```powershell
& "C:\Program Files\Git\bin\bash.exe" ./lcm_mars_hardened.sh ./space_missions.log
```

Use a shell to run the file, not `gawk -f`. The script contains the shell wrapper and sets `LC_ALL=C` itself.

## What changed

The column positions come from `# Format:`. Header names are normalized for case, spaces, and punctuation, so `Duration (days)` and `duration(DAYS)` resolve the same way. `Duration` is also accepted. The four required fields are Destination, Status, Duration, and Security Code. Each record must have the same number of fields as the active header.

There must be a usable header before any pipe-separated data. A missing or ambiguous required column stops the run. Repeated headers are allowed, and a new header can change the column order partway through the file. The existing maximum carries over into the new layout.

Durations must be unsigned whole numbers or decimals with digits on both sides of the decimal point. `9994d`, blanks, negative values, exponents, and values that overflow awk's numeric representation are skipped. Zero is valid. Dates, crew sizes, and success rates are not used to select the winner.

Destination and status comparisons ignore case and surrounding whitespace. That means `MARS` and `COMPLETED` count, while `Marsville` and `Not Completed` do not. The security code is trimmed at the edges; spaces inside it are preserved.

## Handling spelling mistakes

I do not want a plausible misspelling to silently select a different answer.

For headers, an exact normalized name wins. A nearby spelling can be used only when it is the sole candidate, and that produces a warning. A possible misspelled duplicate beside an exact column also produces a warning. Multiple exact matches or ambiguous near matches are errors. Longer header names allow up to two edits; shorter names allow one.

For data values, one insertion, deletion, substitution, or adjacent letter swap marks a value as a possible typo. `Mras` and `Completd` are examples. These rows are not automatically counted:

- If the longest suspect is shorter than the exact winner, print the winner and a warning.
- If a suspect could win, tie, or be the only match, stop without printing a code.

This is a heuristic, not a spelling authority. An unfamiliar legitimate value one edit away can trigger a warning or refusal. Values farther away are treated as unrelated, so this does not catch every possible typo. `Uncompleted` is not treated as `Completed`.

If I have checked the data and know a spelling is an alias, I can opt in explicitly:

```sh
DEST_ALIASES=mras,marz STATUS_ALIASES=completd \
  sh lcm_mars_hardened.sh space_missions.log
```

Aliases are comma-separated, case-insensitive, and trimmed. Empty entries are ignored. They apply to the whole file, so they should only contain values I actually intend to count. The script does not invent aliases on its own.

## Output and exit codes

| Exit | Meaning | Standard output |
| --- | --- | --- |
| 0 | One winning mission | Its code and a newline |
| 1 | No qualifying mission | Empty |
| 2 | Multiple rows share the maximum | Empty |
| 3 | Missing, invalid, or ambiguous header | Empty |
| 4 | A possible data typo could affect the answer | Empty |
| 5 | Input could not be read, or the prefilter failed | Empty |

Warnings and diagnostics go to stderr. A successful result can still have warnings. Ties count rows, including duplicate copies of the same record. If a later row has a larger duration than an earlier tie, that unique larger result wins.

## Keeping the extra checks fast

The full validation loop was too slow for a 20 ms target when it split and normalized every row. The wrapper now uses `grep` to send awk only likely Mars rows and format headers.

The destination filter uses `mar`, `ars`, `ma...s`, `m...rs`, and `mras`, ignoring case. Those fragments cover Mars and every one-edit spelling the validator recognizes, including inserted whitespace and adjacent swaps. They also admit unrelated rows, which is fine: awk still checks the actual destination column. A second cheap check inside awk looks for `com` or `let`, since a single edit to Completed cannot destroy both fragments. Exact fields and durations still decide the result.

Explicit destination aliases bypass the grep filter, and explicit status aliases bypass the status filter. They can be arbitrary words, so filtering them by Mars or Completed fragments would be wrong. An alias-heavy run can therefore be slower than the default benchmark.

Grep includes original line numbers so warnings still point to the original file. The wrapper also forwards grep's exit status through a separate control record; a read or filter error cannot quietly turn a partial result into a successful answer.

Before consuming that stream, awk checks the start of the file up to the first format header. That small extra read prevents the prefilter from hiding data that appears before the header. The normal path is one full grep scan plus that prefix read, not two full scans. The input must be a readable regular file that stays unchanged during the run. This version does not support stdin, named pipes, or a file being modified while it is read. It requires grep with `-a`, `-n`, `-i`, and `-E`, as provided by GNU grep on the CI runner and Git for Windows.

## Remaining caveats

This still is not a full record validator. It skips rows with the wrong field count or invalid duration without listing each skipped row. It does not validate the date, mission ID, crew size, success rate, or security-code format. A malformed code on the winning row can still be printed. Pipes inside values are not escaped or quoted.

Awk uses finite-precision numbers. Ordinary mission durations are fine, but exact comparisons of extremely large values or nearly identical decimals are not guaranteed. Case and whitespace handling use the C locale, not general Unicode normalization.

The script keeps the current result, the most consequential suspect, and small classification caches. Each cache is capped at 256 normalized values, so differences in padding and case share the same entry. After that, new values are checked without being retained, so a file full of distinct values does not make the cache grow forever. That can cost extra processing time. Memory also depends on the current record and header size. There is no 100 GB benchmark or parallel processing implementation here.

## Tests and performance

Both versions run the same 11 core test methods with mawk and gawk. Tie and no-match assertions use each version's documented behavior. The hardened version adds 15 test groups, including all 22 cases from the expanded verification notes.

The added coverage includes reordered columns, swapped duration/rate columns, missing and duplicate headers, header typos, uppercase values, consequential and harmless data typos, and malformed rows. It also checks decimals, numeric overflow, three-way ties, a later winner replacing a tie, explicit aliases, mid-file schema changes, missing final newlines, and classification after the cache fills. Generated single-edit variants exercise each character position, case changes, and whitespace expansion so the prefilters cannot silently drop a suspect. Separate checks cover original line numbers and a failed filter after it has already emitted a candidate winner.

Assertions check the full stdout, exact exit status, and expected diagnostics. The suite does not accept an arbitrary error as a passing error case or inspect only the last output line.

```sh
MISSION_SCRIPT=lcm_mars_hardened.sh python3 -m unittest discover -s tests -v
python3 scripts/benchmark.py --script lcm_mars_hardened.sh \
  --warmups 5 --runs 50 --max-median-ms 20
```

CI benchmarks each script separately with mawk and requires a median below 20 ms. Reports include all 50 samples, timing summaries, interpreter details, file hashes, and the tested commit. They are available in the workflow summary and as separate downloadable artifacts. These are warm-cache measurements on shared runners, not a guarantee for every machine or awk implementation.

The final local 50-run check on the supplied log measured an 18.63 ms median for the hardened script. P95 was 26.22 ms and the slowest sample was 55.47 ms. The 20 ms condition applies to the median, not every individual invocation. The raw measurements and runner details from each subsequent CI run are available in its artifact.
