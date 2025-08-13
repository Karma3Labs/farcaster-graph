#!/bin/sh
unset -v tooldir verbose opt
verbose=false
OPTIND=1
while getopts :b:v opt
do
	case "${opt}" in
		'?') echo "unrecognized option -${OPTARG}" >&2; exit 64;;
		':') echo "missing argument for -${OPTARG}" >&2; exit 64;;
		b) tooldir="${OPTARG}";;
		v) verbose=true;;
		*) echo "unhandled option -${opt}" >&2; exit 70;;
	esac
done
shift $((OPTIND - 1))
case "${tooldir+set}" in
	set) PATH="${tooldir}${PATH+":${PATH}"}"; export PATH;;
esac
case $# in
        0)
                set -- .
                ;;
esac
unset -v isort_v black_v
if ${verbose}
then
	isort_v=--verbose
	black_v=--verbose
	set -x
else
	isort_v=
	black_v=--quiet
fi
isort --profile=black ${isort_v} "$@" || exit
black ${black_v} "$@" || exit
#autopep8 --in-place --aggressive --aggressive --recursive "$@" || exit
