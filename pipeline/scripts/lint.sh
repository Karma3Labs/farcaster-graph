#!/bin/sh
unset -v tool_dir opt
OPTIND=1
while getopts :b: opt
do
	case "${opt}" in
		'?') echo "unrecognized option -${OPTARG}" >&2; exit 64;;
		':') echo "missing argument for -${OPTARG}" >&2; exit 64;;
		b) tool_dir="${OPTARG}";;
		*) echo "unhandled option -${opt}" >&2; exit 70;;
	esac
done
shift $((OPTIND - 1))
case "${tool_dir+set}" in
	set) PATH="${tool_dir}${PATH+":${PATH}"}"; export PATH;;
esac
case $# in
	0)
		set -- .
		;;
esac
ruff check --fix "$@" || exit
ruff format "$@" || exit
