#!/bin/bash
# Wrapper script to toggle daemon on and off
# Call this script as e.g. "$0 --venv --no-terminal-output"
# --venv is only used by this shell script to activate a venv if found
# other arguments are passed to clipster first, then passed to clipfdb
# You can then start the clipster client independently like 
# "/path/to/clipfdb/clipster/clipster -sc"

script_base_dir=$(realpath "$0")
script_home=$(dirname "$(realpath "$0")")
# script_name="fdb_query.py"
script_name="clipster.py"
script_full_path="$script_home/$script_name"
#echo "script full path: ${script_full_path}"
USERID=$(id -u)
pidfile_path="/run/user/${USERID}/clipfdb.pid"

# Find params for us, but keep other params intact to pass them to child proc
declare -a PARAMS
PARAM_COUNT=0
while (( "$#" )); do
  case "$1" in
    --venv) # shuffle path passed
      WANT_VENV=1
      shift
      ;;
    --toggle) # shuffle path passed
      TOGGLE=1
      shift
      ;;
    *) # preserve positional arguments
      PARAMS+=("$1")
      PARAM_COUNT=$((PARAM_COUNT+1))
      shift
      ;;
  esac
done
# set positional arguments in their proper place
eval set -- "${PARAMS[@]}"

# returns a boolean and the pid number, otherwise force_kill if 
# there's a process running but the pid is not the right one in the pidfile
get_state() {
    local mystatus="not-running"
    if [[ -f "${pidfile_path}" ]]; then
        # make sure the pid read corresponds to the running script
        local pid=$(< "${pidfile_path}")
        local cmdline="/proc/${pid}/cmdline"

        # make sure this is our script that is running there
        if [[ -f "${cmdline}" ]] \
        && grep -q "${script_full_path}" "${cmdline}"; then # Might need to adjust the regexp in the grep command
            mystatus="running ${pid}"
        else
            # we found a pid file that didn't get cleaned properly
            mystatus="force-kill"
        fi
    fi
    echo "${mystatus}"
}

activate_venv() {
    # search and activate a virtual env if there is one found (assuming we used virtualenv)
    # only print path without ./ in front
    find_path="$(find "${script_home}" -ipath "*env/bin/activate" -printf "%p\n" | head -n 1)"

    if [ ! -z "${find_path}" ]; then
        path=$(realpath "${find_path}")
        if [ -f "${path}" ]; then
            echo "Found venv in \"${path}\". Activating..."
            source "${path}"
        fi
    fi
}

start() {
    # echo "starting $script_full_path"
    if [ ! -z $WANT_VENV ]; then
        activate_venv
    fi
    # nohup "$script_full_path" "$args" >/dev/null 2>&1 &
    # nohup "$script_full_path" "$args" 2>&1 &

    # --daemon to launch clipster in daemon mode (required!)
    python3 "$script_full_path" "--daemon" "${PARAMS[@]}" &
    echo $! > "$pidfile_path"
}

toggle() {
    kill -0 "$1" && kill -USR1 "$1";
}

stop() {
    # `kill -0 pid` returns successfully if the pid is running, but does not actually kill it.
    kill -0 "$1" && kill "$1"
    rm "$pidfile_path"
}

get_remnant_process_pid() {
    echo $(ps -aux | grep -i ${script_name} | grep -v grep | awk '{print $2}')
}

read runningvar PID < <(get_state)
# echo "runningvar is \"${runningvar}\" pid \"${PID}\""
if [[ "${runningvar}" == "running" ]]; then
    # echo "$script_full_path was running with PID ${PID}"
    if [[ ! -z ${TOGGLE} ]]; then
        toggle "${PID}"
    else
        stop "${PID}"
    fi
elif [[ ${runningvar} == "force-kill" ]]; then
    read remnant_pid< <(get_remnant_process_pid)
    if [[ "x${remnant_pid}" != "x" ]]; then
        echo "Killing a remnant process of pid: ${remnant_pid}"
        stop "${remnant_pid}";
    fi
    start "$*"
else  # $runningvar == "not-running"
    start "$*"
fi
