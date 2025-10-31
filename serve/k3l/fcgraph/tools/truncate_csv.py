import argparse
import csv
import logging
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

_logger = logging.getLogger(__name__)


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()
    input_filename = None if str(args.input_filename) == "-" else args.input_filename
    if args.output_filename is None and args.in_place is not None:
        output_filename = input_filename
    else:
        output_filename = args.output_filename
    # noinspection PyAbstractClass
    # (ExitStack is not abstract)
    with ExitStack() as stack:
        if input_filename is None:
            input_file = sys.stdin
        else:
            input_file = stack.enter_context(input_filename.open("r", newline=""))
        if output_filename is None:
            output_file = sys.stdout
        else:
            output_fd, output_tmp_name = tempfile.mkstemp(
                dir=output_filename.parent,
                prefix=output_filename.stem + ".",
            )
            output_file = stack.enter_context(open(output_fd, "w", newline=""))
        input_csv = csv.reader(input_file)
        output_csv = csv.writer(output_file)
        for _, row in zip(range(args.lines), input_csv):
            output_csv.writerow(row)
    if args.in_place is not None:
        new_suffix = input_filename.suffix + args.in_place
        backup_filename = input_filename.with_suffix(new_suffix)
        _rename(input_filename, backup_filename)
    if output_filename is not None:
        _rename(output_tmp_name, output_filename)


def _rename(src, dst):
    _logger.debug(f"renaming {src} -> {dst}")
    os.rename(src, dst)


# noinspection DuplicatedCode
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Truncate a CSV file.")
    parser.add_argument(
        "lines",
        type=int,
        metavar="LINES",
        help="""Number of lines to keep.""",
    )
    parser.add_argument(
        "input_filename",
        type=Path,
        nargs="?",
        metavar="INPUT-FILE",
        help="""Input CSV file.""",
    )
    output = parser.add_mutually_exclusive_group(required=False)
    output.add_argument(
        "--in-place",
        "-i",
        metavar="EXT",
        help="""Modify the input file in-place, renaming the original file
                by adding the given extension, e.g. -i .bak""",
    )
    output.add_argument(
        "output_filename",
        type=Path,
        nargs="?",
        metavar="OUTPUT-FILE",
        help="""Output CSV file.""",
    )
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())
