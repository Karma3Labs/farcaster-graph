#!/bin/sh
unset -v tool_dir verbose opt
verbose=
OPTIND=1
while getopts :b:vqs opt
do
	case "${opt}" in
		'?') echo "unrecognized option -${OPTARG}" >&2; exit 64;;
		':') echo "missing argument for -${OPTARG}" >&2; exit 64;;
		b) tool_dir="${OPTARG}";;
		v) verbose=--verbose;;
		q) verbose=--quiet;;
		s) verbose=--silent;;
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
ruff ${verbose} check --fix "$@" || exit
ruff ${verbose} format "$@" || exit
