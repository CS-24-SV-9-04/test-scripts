import fcntl
import subprocess
import os
import sys
from enum import Enum

QUERY_FILE_PATH = os.environ["QUERY_FILE_PATH"]
MODEL_FILE_PATH = os.environ["MODEL_FILE_PATH"]
QUERY_COUNT = os.environ["QUERY_COUNT"]
VERIFYPN_PATH = os.environ["VERIFYPN_PATH"]
RESULT_PATH = os.environ["RESULT_PATH"]

QUERY_IS_SATISFIED = "Query is satisfied"
QUERY_IS_NOT_SATISFIED = "Query is NOT satisfied"

class Status(Enum):
    Timeout = "timeout",
    Error = "error",
    Satisfied = "satisfied",
    Unsatisfied = "unsatisfied"


for queryIndex in range(1, int(QUERY_COUNT) + 1):
    print(f"\n###### RUNNING {MODEL_FILE_PATH}:{QUERY_FILE_PATH}#{queryIndex} ######\n")
    print(f"\n###### RUNNING {MODEL_FILE_PATH}:{QUERY_FILE_PATH}#{queryIndex} ######\n", file=sys.stderr)
    status = Status.Error
    try:
        proc = subprocess.run([
                VERIFYPN_PATH,
                "-C", 
                "-x",
                str(queryIndex),
                MODEL_FILE_PATH,
                QUERY_FILE_PATH
            ], 
            capture_output=True,
            timeout=60
        )
        decoded = proc.stdout.decode("utf-8")
        print(decoded)
        print(proc.stderr.decode("utf-8"), file=sys.stderr)
        if (proc.returncode == 0):
            if (QUERY_IS_SATISFIED in decoded):
                status = Status.Satisfied
            elif (QUERY_IS_NOT_SATISFIED in decoded):
                status = Status.Unsatisfied
    except TimeoutError:
        status = Status.TIMEOUT
    
    
    with open(RESULT_PATH, "a") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)

        file.write(f"{MODEL_FILE_PATH},{QUERY_FILE_PATH},{queryIndex},{status.value}\n")

        fcntl.flock(file.fileno(), fcntl.LOCK_UN)