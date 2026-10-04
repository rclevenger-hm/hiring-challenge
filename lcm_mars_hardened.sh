#!/bin/sh
# Usage: sh lcm_mars_hardened.sh [space_missions.log]
# Optional explicit aliases: DEST_ALIASES=mras,marz STATUS_ALIASES=completd
# Exit: 0 winner, 1 no match, 2 tie, 3 header, 4 consequential typo, 5 read/filter error.

input=${1:-space_missions.log}
if [ ! -f "$input" ] || [ ! -r "$input" ]; then
    printf 'cannot read regular file: %s\n' "$input" >&2
    exit 5
fi
[ "$input" != - ] || input=./-
export LC_ALL=C

# Every one-edit Mars spelling contains one of these fragments, including
# transpositions and inserted whitespace. Retain headers in any column layout.
pattern='mar|ars|ma[^|]*s|m[^|]*rs|mras|format:'
[ -z "${DEST_ALIASES:-}" ] || pattern=''
{
    grep -a -n -i -E "$pattern" -- "$input"
    # Keep grep errors visible to awk without relying on non-POSIX pipefail.
    printf '!FILTER_STATUS=%s\n' "$?"
} | MISSION_INPUT="$input" awk '
function trim(s) {
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", s)
    return s
}
function header_name(s) {
    s = tolower(s)
    gsub(/[^a-z0-9]/, "", s)
    return s
}
function value_name(s) {
    s = tolower(trim(s))
    gsub(/[[:space:]]+/, " ", s)
    return s
}
# Optimal string alignment: insertion, deletion, substitution, or adjacent swap.
function distance(a, b, limit,    la, lb, i, j, cost, best, table) {
    la = length(a); lb = length(b)
    if (la - lb > limit || lb - la > limit) return limit + 1
    for (i = 0; i <= la; i++) table[i, 0] = i
    for (j = 0; j <= lb; j++) table[0, j] = j
    for (i = 1; i <= la; i++) {
        for (j = 1; j <= lb; j++) {
            cost = substr(a, i, 1) != substr(b, j, 1)
            best = table[i-1, j] + 1
            if (table[i, j-1] + 1 < best) best = table[i, j-1] + 1
            if (table[i-1, j-1] + cost < best) best = table[i-1, j-1] + cost
            if (i > 1 && j > 1 && substr(a, i, 1) == substr(b, j-1, 1) &&
                substr(a, i-1, 1) == substr(b, j, 1) && table[i-2, j-2] + 1 < best)
                best = table[i-2, j-2] + 1
            table[i, j] = best
        }
    }
    return table[la, lb]
}
function header_error(message) {
    print "invalid header at line " source_line ": " message > "/dev/stderr"
    error = 3
    return 0
}
function column(want, alternate,    i, name, hits, position, near, near_position, limit) {
    limit = length(want) > 6 ? 2 : 1
    for (i = 1; i <= width; i++) {
        name = header_name(headers[i])
        if (name == want || (alternate != "" && name == alternate)) {
            hits++; position = i
        } else if (distance(name, want, limit) <= limit) {
            near++; near_position = i
        }
    }
    if (hits > 1) return header_error("duplicate " want " columns")
    if (hits == 1) {
        if (near) print "warning: header contains a possible misspelled duplicate of " want "; using the exact column" > "/dev/stderr"
        return position
    }
    if (near != 1) return header_error(near ? "ambiguous " want " column" : "missing " want " column")
    print "warning: treating header column " trim(headers[near_position]) " as " want > "/dev/stderr"
    return near_position
}
# 3 = exact/explicit alias; 2 = possible typo; 1 = unrelated.
function classify(raw, want, aliases, cache,    name, result) {
    name = value_name(raw)
    if (name in cache) return cache[name]
    if (name == want || name in aliases) result = 3
    else result = distance(name, want, 1) <= 1 ? 2 : 1
    # Bound the cache instead of retaining every distinct value in a large log.
    if (cache_count[want] < 256) {
        cache[name] = result
        cache_count[want]++
    }
    return result
}
function load_aliases(raw, aliases,    values, count, i, name) {
    count = split(raw, values, ",")
    for (i = 1; i <= count; i++) {
        name = value_name(values[i])
        if (name != "") aliases[name] = 1
    }
}
BEGIN {
    FS = "|"
    load_aliases(ENVIRON["DEST_ALIASES"], destination_aliases)
    load_aliases(ENVIRON["STATUS_ALIASES"], status_aliases)
    custom_statuses = trim(ENVIRON["STATUS_ALIASES"]) != ""
    # Check the prefix directly so filtering cannot hide data before the header.
    while ((read_status = (getline prefix < ENVIRON["MISSION_INPUT"])) > 0) {
        source_line++
        if (tolower(prefix) ~ /^[[:space:]]*#[[:space:]]*format:/) {
            prefix_header = 1
            break
        }
        if (prefix !~ /^[[:space:]]*#/ && index(prefix, "|")) {
            header_error("data appears before a usable # Format: header")
            break
        }
    }
    close(ENVIRON["MISSION_INPUT"])
    if (read_status < 0) {
        print "cannot read input" > "/dev/stderr"
        error = 5
    } else if (!error && !prefix_header) {
        header_error("no usable # Format: header")
    }
    if (error) exit
}
/^!FILTER_STATUS=/ {
    filter_complete = 1
    if ($0 != "!FILTER_STATUS=0" && $0 != "!FILTER_STATUS=1") {
        print "input filter failed" > "/dev/stderr"
        error = 5
    }
    next
}
{
    separator = index($0, ":")
    source_line = substr($0, 1, separator - 1) + 0
    $0 = substr($0, separator + 1)
}
/^[[:space:]]*#/ {
    if (tolower($0) !~ /^[[:space:]]*#[[:space:]]*format:/) next
    header = $0
    sub(/^[^:]*:/, "", header)
    width = split(header, headers, "|")
    destination = column("destination")
    status = column("status")
    duration = column("durationdays", "duration")
    security_code = column("securitycode")
    if (!error && (destination == status || destination == duration || destination == security_code ||
                  status == duration || status == security_code || duration == security_code))
        header_error("required fields map to the same column")
    if (error) exit
    have_header = 1
    next
}
/^[[:space:]]*$/ { next }
{
    if (!have_header) {
        if (index($0, "|")) { header_error("data appears before a usable # Format: header"); exit }
        next
    }
    # A one-edit Completed retains "com" or "let". Explicit aliases bypass it.
    if (!custom_statuses && $0 !~ /[Cc][Oo][Mm]|[Ll][Ee][Tt]/) next
    if (NF != width) next
    dc = ($destination ~ /^[[:space:]]*[Mm][Aa][Rr][Ss][[:space:]]*$/) ? 3 : classify($destination, "mars", destination_aliases, destination_cache)
    if (dc == 1) next
    sc = ($status ~ /^[[:space:]]*[Cc][Oo][Mm][Pp][Ll][Ee][Tt][Ee][Dd][[:space:]]*$/) ? 3 : classify($status, "completed", status_aliases, status_cache)
    if (sc == 1 || $duration !~ /^[[:space:]]*[0-9]+([.][0-9]+)?[[:space:]]*$/) next
    days = $duration + 0
    if (tolower(sprintf("%g", days)) ~ /inf|nan/) next
    if (dc == 3 && sc == 3) {
        if (!count || days > maximum) { maximum = days; code = $security_code; count = 0 }
        if (days == maximum) count++
    } else {
        suspects++
        if (!have_suspect || days > suspect_max) {
            suspect_max = days; suspect_line = source_line; have_suspect = 1
        }
    }
}
END {
    if (error) exit error
    if (!filter_complete) {
        print "input filter did not finish" > "/dev/stderr"
        exit 5
    }
    if (!have_header) {
        print "no usable # Format: header" > "/dev/stderr"
        exit 3
    }
    if (suspects) {
        message = suspects " possible misspelled Mars/Completed row(s); longest at line " suspect_line
        if (!count || suspect_max >= maximum) {
            print "refusing to answer: " message "; fix the data or set explicit aliases" > "/dev/stderr"
            exit 4
        }
        print "warning: " message "; shorter than the winner and not counted" > "/dev/stderr"
    }
    if (count != 1) {
        print (count ? count " missions tie at " maximum " days" : "no qualifying missions") > "/dev/stderr"
        exit (count ? 2 : 1)
    }
    print trim(code)
}
'
