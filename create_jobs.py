#!/usr/bin/python3
from pathlib import Path
from typing import List
from argparse import ArgumentParser
from pathlib import Path
import subprocess
import os
import time

parser = ArgumentParser(prog="colored petri net slurm job starter")
parser.add_argument('-m', '--models', help="Path to directory containing the mcc models", default='/usr/local/share/mcc/')
parser.add_argument('-s', '--sbatch-script', help="Path to the sbatch script that is started", default='./sbatch_script.sh')
parser.add_argument('-S', '--strategy', help="The search strategy to be used")
parser.add_argument('--colored-successor-generator', help="The argument supplied to --colored-successor-generator")
parser.add_argument('-g', '--go', help="Schedule the jobs instead of just printing them", action='store_true')
parser.add_argument('-o', '--out-name', help="Name of the folder where output should be stored", required=True)
parser.add_argument('-w', '--wait-time', help="The wait time between starting jobs", default=0.2, type=float)
parser.add_argument('-b', '--use-baseline', help="Disable the colored engine", action='store_true')
parser.add_argument('--base-output-dir', help='Base path for output', default="/nfs/home/student.aau.dk/jhajri20/slurm-output/")
args = parser.parse_args()

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

def validate_scg(scg: str):
    if scg == "fixed":
        return
    elif scg == "even":
        return
    elif scg is None:
        return
    else:
        raise Exception(f"Unknown successor generator {scg}")

def validate_strategy(strategy: str):
    if strategy == "DFS":
        return
    elif strategy == "BFS":
        return
    elif strategy == "RDFS":
        return
    elif strategy == "BestFS":
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

def fake_process_invocation(args: List[str], env: dict[str,str]):
    print(' '.join(args))
    if ('VERIFYPN_OPTIONS' in env):
        print(env['VERIFYPN_OPTIONS'])

def real_process_invocation(args: List[str], env: dict[str,str]):
    subprocess.call(args, env=env)

process_invocation = real_process_invocation if GO else fake_process_invocation

def create_out_path(output_path: Path):
    output_path.mkdir(parents=True, exist_ok=True)

validate_scg(COLORED_SUCCESSOR_GENERATOR)
validate_strategy(STRATEGY)
validate_out_name(slurm_output_path, OUTPUT_PATH)

class QueryFile:
    def __init__(self, queryPath):
        self.queryPath = queryPath
        self.queryCount = 16
    def name(self):
        return self.queryPath.name

class Model:
    def __init__(self, modelRoot, modelPath, queryFiles):
        self.modelPath = modelPath
        self.queryFiles = queryFiles
        self.modelRoot = modelRoot
    def __repr__(self):
        return self.name()
    def name(self):
        return self.modelRoot.name

models: List[Model] = []

print("finding models")
for modelRoot in Path(MODELS_PATH).iterdir():
    modelPnml = modelRoot / "model.pnml"
    queryFiles = [QueryFile(modelRoot / 'ReachabilityCardinality.xml'), QueryFile(modelRoot / "ReachabilityFireability.xml")]
    models.append(Model(modelRoot, modelPnml, queryFiles))

print(f"Found {models.__len__()} models")

class ModelCheckingJob:
    def __init__(self, model: Model, queryFile: QueryFile):
        self.model = model
        self.queryFile = queryFile

    def __repr__(self):
        return f"{self.model.name()} {self.queryFile.name()}"

def startSbatchJob(env: dict[str,str], script_path: str, job_name: str, output_path: Path):
    process_invocation([
        "./fake_sbatch.sh",
        "--job-name",
        job_name,
        "--output",
        str(output_path / f"{job_name}-%j.out"),
        "--error",
        str(output_path / f"{job_name}-%j.err"),
        script_path
    ], env=env)

def scheduleJob(job: ModelCheckingJob):
    my_env = os.environ.copy()
    my_env["MODEL_FILE_PATH"] = os.path.abspath(job.model.modelPath)
    my_env["QUERY_FILE_PATH"] = os.path.abspath(job.queryFile.queryPath)
    my_env["QUERY_COUNT"] = str(job.queryFile.queryCount)
    verifypn_options = []
    if not USE_BASELINE:
        verifypn_options.append("-C")
    else:
        verifypn_options.append("-n 1")
    if not USE_BASELINE and COLORED_SUCCESSOR_GENERATOR is not None:
        verifypn_options.append("--colored-successor-generator")
        verifypn_options.append(COLORED_SUCCESSOR_GENERATOR)
    if STRATEGY is not None:
        verifypn_options.append("-s")
        verifypn_options.append(STRATEGY)
    my_env["VERIFYPN_OPTIONS"] = ' '.join(verifypn_options)
    job_name =  f"{job.model.name()}_{job.queryFile.name()}_{"default" if STRATEGY is None else STRATEGY}"
    startSbatchJob(my_env, SBATCH_SCRIPT, job_name, OUTPUT_PATH)

modelCheckingJobs: List[ModelCheckingJob] = []
print("creating jobs list")
for model in models:
    for queryFile in model.queryFiles:
        modelCheckingJobs.append(ModelCheckingJob(model, queryFile))

print(f"found {len(modelCheckingJobs)} jobs")
totalQueries = 0
for modelCheckingJob in modelCheckingJobs:
    totalQueries += modelCheckingJob.queryFile.queryCount

if (GO):
    create_out_path(OUTPUT_PATH)

print(f"requires an estimated {totalQueries} minutes of cpu time")
print("Scheduling jobs, press enter to start")
input()
for modelCheckingJob in modelCheckingJobs:
    time.sleep(WAIT_TIME)
    scheduleJob(modelCheckingJob)

print("\a")