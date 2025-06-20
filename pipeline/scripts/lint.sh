#!/bin/sh
unset -v tooldir opt
OPTIND=1
while getopts :b: opt
do
	case "${opt}" in
		'?') echo "unrecognized option -${OPTARG}" >&2; exit 64;;
		':') echo "missing argument for -${OPTARG}" >&2; exit 64;;
		b) tooldir="${OPTARG}";;
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
isort --profile=black "$@" || exit
black --quiet "$@" || exit
#autopep8 --in-place --aggressive --aggressive --recursive "$@" || exit
