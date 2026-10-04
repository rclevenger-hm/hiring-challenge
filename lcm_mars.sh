#!/bin/sh
# Usage: sh lcm_mars.sh [space_missions.log]

LC_ALL=C awk '
BEGIN { FS = "|"; max = -1 }
/Mars/ {
    if (/Completed/ && !/^[[:space:]]*#/ &&
        $3 ~ /^[[:space:]]*Mars[[:space:]]*$/ &&
        $4 ~ /^[[:space:]]*Completed[[:space:]]*$/ &&
        $6 + 0 > max) {
        max = $6 + 0
        code = $8
    }
}
END {
    gsub(/[[:space:]]/, "", code)
    print code
}
' < "${1:-space_missions.log}"
