#!/usr/bin/python3
from pathlib import Path
from typing import List
from argparse import ArgumentParser
import subprocess
import os

parser = ArgumentParser(prog="colored petri net slurm job starter")
parser.add_argument('-m', '--models', help="Path to directory containing the mcc models", default='/usr/local/share/mcc/')
parser.add_argument('-s', '--sbatch-script', help="Path to the sbatch script that is started", default='./sbatch_script.sh')
args = parser.parse_args()

MODELS_PATH = args.models
SBATCH_SCRIPT = args.sbatch_script

class QueryFile:
    def __init__(self, queryPath):
        self.queryPath = queryPath
        with open(queryPath, 'r') as content_file:
            self.queryCount = content_file.read().count("<property>")
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
    queryFiles = [QueryFile(x) for x in modelRoot.glob('ReachabilityCardinality.xml')]
    models.append(Model(modelRoot, modelPnml, queryFiles))

print(f"Found {models.__len__()} models")

class ModelCheckingJob:
    def __init__(self, model: Model, queryFile: QueryFile):
        self.model = model
        self.queryFile = queryFile

    def __repr__(self):
        return f"{self.model.name()} {self.queryFile.name()}"

def scheduleJob(job: ModelCheckingJob):
    my_env = os.environ.copy()
    my_env["MODEL_FILE_PATH"] = os.path.abspath(job.model.modelPath)
    my_env["QUERY_FILE_PATH"] = os.path.abspath(job.queryFile.queryPath)
    my_env["QUERY_COUNT"] = str(job.queryFile.queryCount)
    subprocess.call(["./fake_sbatch.sh", "--job-name", f"{job.model.name()}_{job.queryFile.name()}", SBATCH_SCRIPT], env=my_env)

modelCheckingJobs: List[ModelCheckingJob] = []
print("creating jobs list")
for model in models:
    for queryFile in model.queryFiles:
        modelCheckingJobs.append(ModelCheckingJob(model, queryFile))

print(f"found {len(modelCheckingJobs)} jobs")
totalQueries = 0
for modelCheckingJob in modelCheckingJobs:
    for queryFile in model.queryFiles:
        totalQueries += modelCheckingJob.queryFile.queryCount
print(f"requires an estimated {totalQueries} minutes of cpu time")

i = 0
for modelCheckingJob in modelCheckingJobs:
    scheduleJob(modelCheckingJob)