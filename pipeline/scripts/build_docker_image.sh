#!/bin/sh
unset -v progname progdir
progname="${0##*/}"
case "${0}" in
*/*) progdir="${0%/*}";;
*) progdir=.;;
esac
msg() { case $# in [1-9]*) echo "${_func:-"${progname}"}: $*" >&2;; esac; }
err() { c="${1:-1}"; shift 2> /dev/null || :; msg "$@"; exit "${c}" || exit; }
usage() { msg "$@"; print_usage >&2; exit 64; }
ex_unavailable() { err 69 "$@"; }
ex_software() { err 70 "$@"; }
print_usage() {
  cat <<- ENDEND
usage: ${progname} [options] [-- extra-docker-build-options]
options:
-d              dev mode - include modified/untracked files (default)
-p              production mode - use only the files in the HEAD commit
-t TAG          [repo][:tag] (default: ${default_tag})
ENDEND
}
unset -v default_repo default_tag
default_repo="karma3labs/fcgraph-pipeline"
default_tag="${default_repo}:latest"
unset -v dev repo tag opt
dev=true
tag="${default_tag}"
OPTIND=1
while getopts :dpt: opt
do
  case "${opt}" in
  d) dev=true;;
  p) dev=false;;
  t) tag="${OPTARG}";;
  \?) usage "unrecognized option -${OPTARG}";;
  :) usage "missing argument for -${OPTARG}";;
  *) ex_software "unhandled option -${opt}";;
  esac
done
shift $((OPTIND - 1))
case "${tag}" in
:*) tag="${default_repo}${tag}"
esac
cd "${progdir}/.." || exit
{ [ -f Dockerfile ] && [ -f pyproject.toml ]; } || ex_unavailable "cannot locate repo root"
if ${dev}
then
  git ls-files --cached --others --exclude-standard -z | tar --null -T- -cvf-
else
  git archive --format=tar HEAD
fi | docker build -t "${tag}" "$@" -