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
@click.option(
    "--this", type=str, required=True, help="Path to result set for this location"
)
@click.option(
    "--other", type=str, required=True, help="Path to result set for other location"
)
@click.option(
    "--dump-models",
    type=bool,
    default=False,
    help="Dump models in jsonl format for missing targets",
)
@click.option("-v", "--verbose", count=True, callback=configure_logging)
def compare(this, other, dump_models, verbose):
    """Main compare function."""

    tic = time.time()

    #
    # loading result set for this location
    #
    this_path = Path(this)
    if not this_path.exists():
        logger.error(
            f"Path to result set for this location does not exist. Check path. Exiting!"
        )
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
    if not other_path.exists():
        logger.error(
            f"Path to result set for other location does not exist. Check path. Exiting!"
        )
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
    differing_this_is_newer_model = {}
    differing_other_is_newer_model = {}
    differing_both_same_age_model = {}

    # Note: this_path and other_path are now used in a different context

    for other_path, other_record in other_model.items():
        if not other_path in this_model.keys():
            logger.debug(f"{other_path} is missing in this location.")
            missing_model[other_path] = other_record
        else:
            this_record = this_model[other_path]
            this_path = this_record["path"]

            # print(f"{other_record=}")
            # print(f"{this_record=}")
            if other_record["checksum"] != this_record["checksum"]:
                logger.debug(
                    f"{other_path} exists in this location, but has differing content."
                )
                differing_model[other_path] = other_record

                # We can distinguish this a bit more looking at the last_modified timestamp
                other_last_modified = other_record["last_modified"]
                this_last_modified = this_record["last_modified"]
                if other_record["last_modified"] > this_record["last_modified"]:
                    logger.debug(f"{other_path} is newer.")
                    differing_other_is_newer_model[other_path] = other_record
                elif other_record["last_modified"] < this_record["last_modified"]:
                    logger.debug(f"{this_path} is newer")
                    differing_this_is_newer_model[this_path] = this_record
                else:
                    logger.debug(
                        "Hit the rare case where content differs, whilst last_modified is equal"
                    )
                    differing_both_same_age_model[this_path] = this_record
            else:
                logger.debug(f"{other_path} exists in this location and is equal.")
                equal_model[other_path] = other_record

    toc = time.time()

    logger.info(f"Comparison took {toc-tic:.1f} s.")
    logger.info(
        f"We have {len(equal_model)} equal entries in this and the other location."
    )
    logger.info(
        f"There are {len(differing_model)} entries available on both sides but with differing content, "
    )
    logger.info(
        f"of which {len(differing_this_is_newer_model)} entries are newer on this side, "
    )
    logger.info(
        f"and {len(differing_other_is_newer_model)} entries are newer on the other side."
    )
    logger.info(
        f"Most weirdly {len(differing_both_same_age_model)} entries have different checksums, but the same age."
    )
    logger.info(f"{len(missing_model)} entries are missing on this side.")

    # Some assertions to check correctness of the strategy
    assert len(missing_model) + len(equal_model) + len(differing_model) == len(
        other_model
    )

    assert len(missing_model) + len(equal_model) + len(
        differing_this_is_newer_model
    ) + len(differing_other_is_newer_model) + len(differing_both_same_age_model) == len(
        other_model
    )

    missing_paths = []
    if dump_models:
        # write the missing list
        with Path("missing_entries.jsonl").open("w") as fd:
            for path, record in missing_model.items():
                missing_paths.append(path)
                fd.write(json.dumps(record) + "\n")

        # write the differing, newer in other side list
        with Path("differing_entries.json").open("w") as fd:
            for path, record in differing_other_is_newer_model.items():
                missing_paths.append(path)
                fd.write(json.dumps(record) + "\n")

        with Path("missing_paths.txt").open("w") as fd:
            for path in sorted(missing_paths):
                fd.write(path + "\n")


if __name__ == "__main__":
    sys.exit(compare())  # pragma: no cover
