# Warp Hiring Challenge

## About
This is a programming challenge for candidates who are interested in applying to Warp. It's meant to be short and fun -- we highly encourage you to use Agent Mode in Warp to solve the challenge! There will be fields in the application for you to share your answer and a link to Warp Shared Block containing the command you used to solve the problem.

Participation in the challenge is optional. You can still submit an application without doing the hiring challenge.

Get started by reading the [challenge description](mission_challenge.md). Good luck!

## Solution and checks

[![Mission checks](https://github.com/rclevenger-hm/hiring-challenge/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/rclevenger-hm/hiring-challenge/actions/workflows/ci.yml)

Run `sh lcm_mars.sh space_missions.log` for the short solution, or `sh lcm_mars_hardened.sh space_missions.log` for header-based columns, stricter duration checks, and typo handling.

CI runs lint and correctness checks for both scripts with mawk and gawk. Each script also gets its own benchmark requiring a median below 20 ms.

## Documentation

- [Challenge description](mission_challenge.md) — the original problem, input format, and requirements.
- [Short solution](lcm_mars.md) — choices, caveats, Windows usage, and the original measurements.
- [Hardened solution](lcm_mars_hardened.md) — header handling, typo rules, aliases, exit codes, edge cases, and performance checks.

All project Markdown guides are linked above. Open the workflow badge to see the latest checks and download the benchmark reports.
