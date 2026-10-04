# Warp Hiring Challenge

## About
This is a programming challenge for candidates who are interested in applying to Warp. It's meant to be short and fun -- we highly encourage you to use Agent Mode in Warp to solve the challenge! There will be fields in the application for you to share your answer and a link to Warp Shared Block containing the command you used to solve the problem.

Participation in the challenge is optional. You can still submit an application without doing the hiring challenge.

Get started by reading the [challenge description](mission_challenge.md). Good luck!

## Solution and checks

[![Mission checks](https://github.com/rclevenger-hm/hiring-challenge/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/rclevenger-hm/hiring-challenge/actions/workflows/ci.yml)

Run `sh lcm_mars.sh space_missions.log`. The [solution notes](lcm_mars.md) explain the choices, caveats, Windows command, and performance measurements.

CI runs lint, correctness checks with mawk and gawk, and a benchmark with a 200 ms median limit. The [checks section](lcm_mars.md#automated-checks) has the local commands and details.
