#!/usr/bin/python3
from argparse import ArgumentParser
import os
from pathlib import Path
import subprocess
import sys
from time import sleep
from typing import List

parser = ArgumentParser(prog="CPN slurm big job starter")
parser.add_argument('-m', '--models', help="Path to directory containing the mcc models", default='/nfs/petrinet/mcc/2024/colour/')
parser.add_argument('-s', '--sbatch-script', help="Path to the sbatch script that is started", default='./big_job_script.sh')
parser.add_argument('-S', '--strategy')
parser.add_argument('--colored-successor-generator', help="The argument supplied to --colored-successor-generator")
parser.add_argument('-g', '--go', help="Schedule the jobs instead of just printing them", action='store_true')
parser.add_argument('-o', '--out-name', help="Name of the folder where output should be stored", required=True)
parser.add_argument('-w', '--wait-time', help="The wait time between starting jobs", default=0.2, type=float)
parser.add_argument('-b', '--use-baseline', help="Disable the colored engine", action='store_true')
parser.add_argument('--base-output-dir', help='Base path for output', default="/nfs/home/student.aau.dk/jhajri20/slurm-output/")
parser.add_argument('-d', '--deadlock-query', help='path to the global deadlock query', default='/nfs/home/student.aau.dk/jhajri20/ReachabilityDeadlock.xml')
parser.add_argument('-v', '--verifypn-path', help='path to the verifypn binary', default='/nfs/home/student.aau.dk/jhajri20/verifypn-linux64')
parser.add_argument('-t', '--timeout', help="The timeout for each query", type=int, default=5)
parser.add_argument("-c", "--categories", help="comma seperated list of jobs", default="ReachabilityCardinality,ReachabilityFireability,ReachabilityDeadlock")
only_args = sys.argv[1:]
EXTRA_ARGS = []
try:
    index = only_args.index("--")
    EXTRA_ARGS = only_args[index:][1:]
    only_args = only_args[:index]
except ValueError:
    pass
args = parser.parse_args(only_args)

MODELS_PATH = args.models
SBATCH_SCRIPT = args.sbatch_script
STRATEGY = args.strategy
GO = args.go
COLORED_SUCCESSOR_GENERATOR = args.colored_successor_generator
OUT_NAME = args.out_name
WAIT_TIME = args.wait_time
USE_BASELINE = args.use_baseline
BASE_OUTPUT_DIR = args.base_output_dir
slurm_output_path = Path(BASE_OUTPUT_DIR)
OUTPUT_PATH = slurm_output_path / OUT_NAME
DEADLOCK_QUERY = args.deadlock_query
VERIFYPN_PATH = args.verifypn_path
TIMEOUT = args.timeout
CATEGORIES = set(args.categories.split(","))
print(CATEGORIES)

def validate_scg(scg: str):
    if scg == "fixed":
        return
    elif scg == "even":
        return
    elif scg is None:
        return
    else:
        raise Exception(f"Unknown successor generator {scg}")

def validate_strategy(strategy: str, is_baseline: bool):
    if strategy == "DFS":
        return
    elif strategy == "BFS":
        return
    elif strategy == "RDFS":
        return
    elif strategy == "BestFS":
        return
    elif strategy == "RPFS" and is_baseline:
        return
    elif strategy is None:
        return
    else:
        raise Exception(f"Unknown search strategy {strategy}")

def validate_out_name(slurm_output_path: Path, output_path: Path):
    if (output_path.is_relative_to(slurm_output_path)):
        return
    else:
        raise Exception(f"Output path is not relative to slurm-output")

class QueryFile:
    def __init__(self, categoryName: str, queryPath: str, queryCount: int, isLTL: bool):
        self.categoryName = categoryName
        self.queryPath = queryPath
        self.queryCount = queryCount
        self.isLTL = isLTL
    def name(self):
        return self.queryPath.name

class Model:
    def __init__(self, modelRoot: Path, modelPath: Path, queryFiles: List[QueryFile], timeout: int):
        self.modelPath = modelPath
        self.queryFiles = queryFiles
        self.modelRoot = modelRoot
        self.timeout = timeout
    def __repr__(self):
        return self.name()
    def name(self):
        return self.modelRoot.name

def createEnv(model: Model):
    my_env = os.environ.copy()
    categoriesList: List[str] = []
    for queryFile in model.queryFiles:
        categoriesList.append(f'{queryFile.queryCount}:{queryFile.categoryName}:{1 if queryFile.isLTL else 0}:{queryFile.queryPath}')
    my_env["CATEGORIES"] = " ".join(categoriesList)
    my_env["MODEL_NAME"] = model.modelRoot.name
    my_env["MODEL_FILE_PATH"] = model.modelPath
    my_env["VERIFYPN_PATH"] = VERIFYPN_PATH
    my_env["SEARCH_STRATEGY"] = STRATEGY or "default"
    my_env["SUCCESSOR_GENERATOR"] = COLORED_SUCCESSOR_GENERATOR or "default"
    reachabilityOptions = []
    reachabilityOptions.append("-n")
    reachabilityOptions.append("1")
    if not USE_BASELINE:
        reachabilityOptions.append("-C")
    if not USE_BASELINE and COLORED_SUCCESSOR_GENERATOR is not None:
        reachabilityOptions.append("--colored-successor-generator")
        reachabilityOptions.append(COLORED_SUCCESSOR_GENERATOR)
    if STRATEGY is not None:
        reachabilityOptions.append("-s")
        reachabilityOptions.append(STRATEGY)
    reachabilityOptions = reachabilityOptions + EXTRA_ARGS
    ltlOptions = reachabilityOptions + ["-R", "0", "-ltl"]
    
    my_env["REACHABILITY_OPTIONS"] = " ".join(reachabilityOptions)
    my_env["LTL_OPTIONS"] = " ".join(ltlOptions)
    return my_env

def scheduleJob(model: Model):
    env = createEnv(model)
    args = [
        "sbatch",
        "--job-name",
        f'{model.modelRoot.name}_{OUT_NAME}',
        "--output",
        str(OUTPUT_PATH / f"{model.modelRoot.name}_{OUT_NAME}-%j.out"),
        "--error",
        str(OUTPUT_PATH / f"{model.modelRoot.name}_{OUT_NAME}-%j.err"),
        "--time",
        str(model.timeout + 10),
        SBATCH_SCRIPT
    ]

    if (GO):
        subprocess.call(args, env=env)
    else:
        print(args)


def main():
    validate_scg(COLORED_SUCCESSOR_GENERATOR)
    validate_strategy(STRATEGY, USE_BASELINE)
    validate_out_name(slurm_output_path, OUTPUT_PATH)

    models: List[Model] = []

    print("finding models")
    totalQueries = 0
    for modelRoot in Path(MODELS_PATH).iterdir():
        modelPnml = modelRoot / "model.pnml"
        localQueries = 0
        queryFiles = list(filter(lambda x: x.categoryName in CATEGORIES, [
            QueryFile("ReachabilityCardinality", modelRoot / 'ReachabilityCardinality.xml', 16, False),
            QueryFile("ReachabilityFireability", modelRoot / "ReachabilityFireability.xml", 16, False),
            QueryFile("LTLCardinality", modelRoot / "LTLCardinality.xml", 16, True),
            QueryFile("LTLFireability", modelRoot / "LTLFireability.xml", 16, True),
            QueryFile("ReachabilityDeadlock", Path(DEADLOCK_QUERY), 1, False)
        ]))
        for query in queryFiles:
            totalQueries += query.queryCount
            localQueries += query.queryCount
        models.append(Model(modelRoot, modelPnml, queryFiles, localQueries * TIMEOUT))
    
    print(f"Found {models.__len__()} models")
    print(f"Total number of queries: {totalQueries} needs maximum {totalQueries * TIMEOUT} CPU minutes")

    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_PATH / "large").open("w") as f:
        pass

    print("press enter to start")
    input()

    for model in models:
        scheduleJob(model)
        sleep(WAIT_TIME)

main()