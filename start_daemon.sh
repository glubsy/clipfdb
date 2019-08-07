#!/bin/bash
# Wrapper script to toggle daemon on and off

# ./clipster.py -d -l DEBUG

script_base_dir=$(realpath "$0")
script_home=$(dirname "$(realpath "$0")")
script_name="fdb_query.py"
script_full_path="$script_home/$script_name"
# args="-d" # not used anymore since trimming down of clipster.py
args="" #can be --clipster_debug
pid_file="/tmp/clipfdb.pid"
#echo "script full path: ${script_full_path}"

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
    find_path="$(find "${script_home}" -ipath "*/bin/activate" -printf "%p\n" | grep -i "/bin/activate")"

    if [ ! -z "${find_path}" ]; then
        path=$(realpath "${find_path}")
        if [ -f "${path}" ]; then 
            source "${path}"
            echo "Found venv in \"${path}\". Activating."
        fi
    fi;
}

start() {
    # echo "starting $script_full_path"
    # if argument is venv
    if [ "$1" == "venv" ]; then
        activate_venv
    fi
    # nohup "$script_full_path" "$args" >/dev/null 2>&1 &
    # nohup "$script_full_path" "$args" 2>&1 &
    "$script_full_path" "$args" &
    echo $! > "$pid_file"
}

get_remnant() {
	echo $(ps -aux | grep -i ${script_name} | grep -v grep | awk '{print $2}')
}

stop() {
    # `kill -0 pid` returns successfully if the pid is running, but does not actually kill it.
    kill -0 "$1" && kill -SIGUSR1 "$1" # to emit sound on termination
    rm "$pid_file"
    # echo "stopped"
}

read runningvar pid < <(running)
if [[ "${runningvar}" == "true" ]]; then
    # echo "$script_full_path was running with PID ${pid}"
    stop "${pid}"
elif [[ ${runningvar} == "force_kill" ]]; then
	read remnant_pid< <(get_remnant)
	if [[ "x${remnant_pid}" != "x" ]]; then
		echo "Killing a remnant process of pid: ${remnant_pid}"
		stop "${remnant_pid}";
	fi
	start "$*"
else
    start "$*"
fi
