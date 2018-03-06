#!/bin/bash
# Wrapper script to toggle daemon on and off

# ./clipster.py -d -l DEBUG
# ./clipster.py -d

script_home=$(dirname "$(realpath "$0")")
script_name="$script_home/fdb_query.py"
# args="-d" # not used anymore since trimming down of clipster.py
args="" #can be --clipster_debug
pid_file="/tmp/clipster.pid"
# echo "pid path: ${pid_file}"

# returns a boolean and optionally the pid
running() {
    local mystatus="false"
    if [[ -f "${pid_file}" ]]; then
        # check to see it corresponds to the running script
        local pid=$(< "${pid_file}")
        local cmdline="/proc/${pid}/cmdline"
        # you may need to adjust the regexp in the grep command
        if [[ -f "${cmdline}" ]] && grep -q "${script_name}" "${cmdline}"; then
            mystatus="true ${pid}"
        fi
    fi
    echo "${mystatus}"
}

start() {
    #echo "starting $script_name"
    # nohup "$script_name" "$args" >/dev/null 2>&1 &
    #nohup "$script_name" "$args" 2>&1 &
    "$script_name" "$args" &
    echo $! > "$pid_file"
}

stop() {
    # `kill -0 pid` returns successfully if the pid is running, but does not
    # actually kill it.
    kill -0 "$1" && kill -SIGUSR1 "$1" # to emit sound on termination
    rm "$pid_file"
    #echo "stopped"
}

read runningvar pid < <(running)

if [[ "${runningvar}" == "true" ]]; then
    #echo "$script_name was running with PID ${pid}"
    stop "${pid}"
else
    start
fi
