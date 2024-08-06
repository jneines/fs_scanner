#!/usr/bin/env python3
"""Compare two result sets."""
import sys
from pathlib import Path
import json
import time

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
# fs compare
#
@click.command()
@click.option("--this", type=str, required=True, help="Path to result set for this location")
@click.option("--other", type=str, required=True, help="Path to result set for other location")
@click.option("-v", "--verbose", count=True, callback=configure_logging)
def compare(this, other, verbose):
    """Main compare function."""

    tic = time.time()

    #
    # loading result set for this location
    #
    this_path = Path(this)
    if not this_path.exists():
        logger.error(f"Path to result set for this location does not exist. Check path. Exiting!")
        sys.exit(-1)

    logger.info(f"Reading result contents for this location")
    this_model = {}
    for line in this_path.open("r"):
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        this_model[record["path"]] = record
    logger.info(f"Result set for this location has {len(this_model)} entries.")

    #
    # loading result set for other location
    #
    other_path = Path(other)
    if not this_path.exists():
        logger.error(f"Path to result set for other location does not exist. Check path. Exiting!")
        sys.exit(-1)

    logger.info(f"Reading result contents for other location")
    other_model = {}
    for line in other_path.open("r"):
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        other_model[record["path"]] = record
    logger.info(f"Result set for other location has {len(other_model)} entries.")

    #
    # actual comparison step
    #
    missing_model = {}
    equal_model = {}
    differing_model = {}

    for other_path, other_record in other_model.items():
        if not other_path in this_model.keys():
            logger.debug(f"{other_path} is missing in this location.")
            missing_model[other_path] = other_record
        else:
            this_record = this_model[other_path]
            if other_record["checksum"] != this_record["checksum"]:
                logger.debug(f"{other_path} exists in this location, but has differing content.")
                differing_model[other_path] = other_record
            else:
                logger.debug(f"{other_path} exists in this location and is equal.")
                equal_model[other_path] = other_record



    toc = time.time()

    logger.info(f"Comparison took {toc-tic:.1f} s.")
    logger.info(f"We have {len(equal_model)} equal entries in this and the other location.") 
    logger.info(f"There are {len(differing_model)} entries available on both sides but with differing content.") 
    logger.info(f"{len(missing_model)} entries are missing on this side.") 

    assert len(missing_model) + len(equal_model) + len(differing_model) == len(other_model)



if __name__ == "__main__":
    sys.exit(compare())  # pragma: no cover
