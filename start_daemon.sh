#!/bin/bash
# Wrapper script to toggle daemon on and off
# Call this script as e.g. "$0 --venv --no-terminal-output"
# --venv is only used by this shell script to activate a venv if found
# other arguments are passed to clipster first, then passed to clipfdb
# You can then start the clipster client independently like 
# "/path/to/clipfdb/clipster/clipster -sc"

script_base_dir=$(realpath "$0")
script_home=$(dirname "$(realpath "$0")")
script_name="fdb_query.py"
script_full_path="$script_home/$script_name"
#echo "script full path: ${script_full_path}"
USERID=$(id -u)
pid_file="/run/user/${USERID}/clipfdb.pid"

# Find params for us, but keep other params intact to pass them to child proc
declare -a PARAMS
PARAM_COUNT=0
while (( "$#" )); do
  case "$1" in
    --venv) # shuffle path passed
      WANT_VENV=1
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

# returns a boolean and optionally the pid, otherwise force_kill if there's a process running but the pid is not the right one in the pidfile
running() {
    local mystatus="false"
    if [[ -f "${pid_file}" ]]; then
        # check to see it corresponds to the running script
        local pid=$(< "${pid_file}")
        local cmdline="/proc/${pid}/cmdline"
	# make sure this is out script that is running there
        # you may need to adjust the regexp in the grep command
        if [[ -f "${cmdline}" ]] && grep -q "${script_full_path}" "${cmdline}"; then
            mystatus="true ${pid}"
        else
		# we found a pid in /tmp that didn't get cleaned properly!
		mystatus="force_kill"
	fi
    fi
    echo "${mystatus}"
}

activate_venv(){
    # search and activate a virtual env if there is one found (assuming we used virtualenv)
    # only print path without ./ in front
    find_path="$(find "${script_home}" -ipath "*env/bin/activate" -printf "%p\n" | head -n 1)"

    if [ ! -z "${find_path}" ]; then
        path=$(realpath "${find_path}")
        if [ -f "${path}" ]; then
            echo "Found venv in \"${path}\". Activating..."
            source "${path}"
        fi
    fi;
}

start() {
    # echo "starting $script_full_path"
    # if argument is venv
    if [ ! -z $WANT_VENV ]; then
        activate_venv
    fi
    # nohup "$script_full_path" "$args" >/dev/null 2>&1 &
    # nohup "$script_full_path" "$args" 2>&1 &

    # --daemon to launch clipster in daemon mode (required!)
    "$script_full_path" "--daemon" "${PARAMS[@]}" &
    echo $! > "$pid_file"
}

get_remnant_process_pid() {
	echo $(ps -aux | grep -i ${script_name} | grep -v grep | awk '{print $2}')
}

stop() {
    # `kill -0 pid` returns successfully if the pid is running, but does not actually kill it.
    kill -0 "$1" && kill "$1"
    rm "$pid_file"
}

read runningvar PID < <(running)
if [[ "${runningvar}" == "true" ]]; then
    # echo "$script_full_path was running with PID ${PID}"
    stop "${PID}"
elif [[ ${runningvar} == "force_kill" ]]; then
	read remnant_pid< <(get_remnant_process_pid)
	if [[ "x${remnant_pid}" != "x" ]]; then
		echo "Killing a remnant process of pid: ${remnant_pid}"
		stop "${remnant_pid}";
	fi
	start "$*"
else
    start "$*"
fi
