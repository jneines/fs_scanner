#!/usr/bin/env python3
"""Console script for fs_scanner."""
import sys
import time
from pathlib import Path
import json
import hashlib
import zlib

import click
from loguru import logger


#
# logging configuration
#
def configure_logging(ctx, param, value):
    logger.remove()

    if value == 0:
        # no logging
        pass
    elif value == 1:
        logger.add(sys.stderr, level="INFO")
    else:
        logger.add(sys.stderr, level="DEBUG")


#
# checksum handling
#
def no_checksum(path):
    """No checksum

    Do not calculate any checksum.
    Obviously the fastest approach, but in no way reliable.
    Use this for simple comparisons only.
    """
    return None


def size_checksum(path):
    """Size based checksum

    Use the files size as a checksum.
    Very weak, but fast.
    """
    return path.stat().st_size


def simple_checksum(path):
    """Simple checksum calculation

    Use a iterative adler32 based approach to calculate the files checksum.
    Still quite fast. Not perfectly reliable though.
    """
    chunk_size = 1024
    checksum = zlib.adler32(b"")
    with path.open("rb") as fd:
        while chunk := fd.read(chunk_size):
            checksum = zlib.adler32(chunk, checksum)

    return checksum


def strong_checksum(path):
    """Strong checksum calculation

    Use a standard md5 based approach to calculate the files checksum.
    This should considered to be reliable enough, but will take some more time.
    """
    with path.open("rb") as fd:
        digest = hashlib.file_digest(fd, "md5")
        return digest.hexdigest()


checksum_mapper = {
    "none": no_checksum,
    "size": size_checksum,
    "simple": simple_checksum,
    "strong": strong_checksum,
}

#
# fs scanner
#


@click.command()
@click.option(
    "-d",
    "--entry-dir",
    type=str,
    required=True,
    help="Entry directory to start the scan",
)
@click.option(
    "-o",
    "--output",
    type=str,
    default="-",
    show_default=True,
    help="Path for output in jsonl format",
)
@click.option(
    "-c",
    "--checksum",
    type=click.Choice(["none", "time", "simple", "strong"]),
    default="none",
    show_default=True,
    help=(
        "Type of checksum to use. "
        "'none' will not calculate any checksum, "
        "'size' will use the files size, "
        "'simple' will use an incremental adler32 checksum, "
        "whereas 'strong' will use std md5 based checksum approach"
    ),
)
@click.option("-v", "--verbose", count=True, callback=configure_logging)
def scan(entry_dir, output, checksum, verbose):
    """Main scan function."""

    entry_dir = Path(entry_dir)
    if not entry_dir.exists():
        logger.error(f"{entry_dir=} does not exist. Exiting!")
        sys.exit(-1)

    logger.info(f"Starting recursive scan at {entry_dir=}")

    # open the output stream.
    if output == "-":
        output_stream = sys.stdout
    else:
        output_file = Path(output)
        output_stream = output_file.open("w")

    tic = time.time()
    file_count = 0
    error_count = 0
    content_size = 0
    for root, dirs, files in entry_dir.walk():
        for _file in files:
            file_count += 1

            file_path = root / _file
            check_state = "OK"
            try:
                s = file_path.stat()
                if not file_path.is_file():
                    logger.warning(f"{file_path.as_posix()} is not a regular file. Skipping ...")
                    continue
                file_size = s.st_size
                last_modified = s.st_mtime
                content_size += file_size

                file_checksum = checksum_mapper[checksum](file_path)
            except OSError as e:
                logger.error(f"Unable to process file. Error was {e}")
                check_state = str(e)
                error_count += 1

            record = {
                "path": file_path.relative_to(entry_dir.parent).as_posix(),
                "size": file_size,
                "last_modified": last_modified,
                "checksum": file_checksum,
                "check_state": check_state,
            }

            output_stream.write(json.dumps(record) + "\n")

    # close the output stream. Closing stdout will not be a problem here
    output_stream.close()

    toc = time.time()

    logger.info(f"Scan took {toc-tic:.1f} s.")
    logger.info(f"Scanned {file_count} files.")
    logger.info(f"{error_count} errors occured while scanning.")
    logger.info(f"Overall content size is {content_size:_d} Bytes")



if __name__ == "__main__":
    sys.exit(scan())  # pragma: no cover

