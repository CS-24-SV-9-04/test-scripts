#!/usr/bin/python3
from argparse import ArgumentParser
from itertools import islice
import os
from pathlib import Path
import sys

parsedArgs = {}
positionalArgs = []
argIter = iter(range(1, len(sys.argv)))

for i in argIter:
    if sys.argv[i].startswith("--"):
        if (i + 1 < len(sys.argv)):
            parsedArgs[sys.argv[i]] = sys.argv[i + 1]
            next(argIter)
        else:
            raise Exception("parse error")
    else:
        positionalArgs.append(sys.argv[i])

JOB_NAME: str = parsedArgs["--job-name"]
OUTPUT = parsedArgs["--output"]
ERROR = parsedArgs["--error"]
TIME = parsedArgs["--time"]
COMMAND = positionalArgs

OUTPUT_FOLDER = Path("fake_sbatch_jobs")
OUTPUT_FOLDER.mkdir(exist_ok=True)

with (OUTPUT_FOLDER / (JOB_NAME + ".sh")).open("w") as f:
    f.write("#!/bin/bash\n")
    f.write(f"# {JOB_NAME}\n")
    env = os.environ.copy()
    for (key, val) in env.items():
        f.write(f"declare -x {key}=\"{val}\"\n")
    f.write(f"{" ".join(COMMAND)} 2>\"{ERROR.replace("%j", "JOB_NUMBER")}\" 1>\"{OUTPUT.replace("%j", "JOB_NUMBER")}\"\n")
    print(f"created job {JOB_NAME}")

(OUTPUT_FOLDER / (JOB_NAME + ".sh")).chmod(0o775)