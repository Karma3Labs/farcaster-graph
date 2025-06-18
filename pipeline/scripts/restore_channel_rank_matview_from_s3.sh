#!/bin/sh
set -e
unset -v progname
progname="${0##*/}"
msg() { case $# in [1-9]*) echo "${_func:-"${progname}"}: $*" >&2;; esac; }
err_exit() { c="${1:-1}"; shift 2> /dev/null; msg "$@"; exit "${c}"; }
ex_usage() { err_exit 64 "$@"; }
print_usage() {
  :
}
usage() { print_usage >&2; ex_usage "$@"; }
now=$(date +%s)
dryrun=false
while getopts :s:n opt
do
  case "${opt}" in
    s) now=$(date --date="${OPTARG}" +%s);;
    n) dryrun=true;;
    '?') usage "unrecognized option -${OPTARG}";;
    ':') usage "missing argument for -${OPTARG}";;
  esac
done
shift $((OPTIND - 1))
while :
do
  date=$(date --utc --date="@${now}" "+%Y-%m-%d")
  output=$(aws s3 ls "s3://k3l-farcaster-backups/historical/${date}/")
  backups=$(echo "${output}" | grep -o 'k3l_channel_rankings_all_[0-9]*\.csv\.gz') && break
  now=$((now - 86400))
done
backup="s3://k3l-farcaster-backups/historical/${date}/$(echo "${backups}" | head -1)"
msg "restoring from ${backup}"
aws s3 cp "${backup}" - | gunzip | sed 's/^[^,]*,//' > cfids-from-s3.csv
"${dryrun}" && finalize=ROLLBACK || finalize=COMMIT
psql -h eigen8.k3l.io -p 9541 -U k3l_user postgres << ENDEND
BEGIN;
\COPY k3l_channel_fids (channel_id, fid, score, rank, compute_ts, strategy_name) TO 'cfids-backup.csv' (FORMAT csv, HEADER TRUE);
TRUNCATE k3l_channel_fids;
\COPY k3l_channel_fids (channel_id, fid, score, rank, compute_ts, strategy_name) FROM 'cfids-from-s3.csv' (FORMAT csv, HEADER MATCH);
REFRESH MATERIALIZED VIEW k3l_channel_rank;
TRUNCATE k3l_channel_fids;
\COPY k3l_channel_fids (channel_id, fid, score, rank, compute_ts, strategy_name) FROM 'cfids-backup.csv' (FORMAT csv, HEADER MATCH);
${finalize};
ENDEND
