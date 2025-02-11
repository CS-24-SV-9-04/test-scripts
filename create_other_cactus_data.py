#!/usr/bin/python3
from argparse import ArgumentParser
from io import TextIOWrapper
from os import mkdir
import sqlite3
from typing import List
from analysis_helper import Experiment, getExperimentId


parser = ArgumentParser(prog="Generates cactus graphs for all given experiments")
parser.add_argument("experiments", nargs='+', help="all experiments included in the matrix in <name>-<strategy> format")
args = parser.parse_args()

con = sqlite3.connect("data.db")

allExperimentIds = [getExperimentId(con, Experiment.fromFormat(experimentFormat)) for experimentFormat in args.experiments]
allExperiments: List[Experiment] = [Experiment.fromFormat(experimentFormat) for experimentFormat in args.experiments]

def getSkipCount(con: sqlite3.Connection, experiment: int):
    cur = con.execute(f"""
        SELECT COUNT(*) FROM query_result qr
	        WHERE qr.experiment_id = ? 
	        AND qr.status = "Answered"
	        AND (
                STATES <= 2
                OR qr.verification_time IS NULL
                OR qr.states IS NULL
                OR throughput > 1
            )
    """, (experiment,))
    return cur.fetchone()[0]

def getThroughputs(con: sqlite3.Connection, experiment: int):
    cur = con.execute(f"""
        SELECT qr.states/qr.verification_time as throughput FROM query_result qr
	        WHERE qr.experiment_id = ? 
            AND qr.verification_time IS NOT NULL
	        AND qr.states IS NOT NULL
	        AND qr.status = "Answered"
	        AND STATES > 2
            AND throughput > 1
	        ORDER BY throughput ASC
    """, (experiment,))
    skipCount = 0#getSkipCount(con, experiment)
    return [(i, time[0]) for i, time in enumerate(cur.fetchall())]

def createTab(out: TextIOWrapper, data: List[tuple[int, float]]):
    out.write("counter\tthroughput\n")
    for dataPoint in data:
        i, throughput = dataPoint
        out.write(f"{i}\t{throughput}\n")
try:
    mkdir("tables")
except FileExistsError:
    pass

for experiment in allExperiments:
    id = getExperimentId(con, experiment)
    with open(f"tables/throughput-{experiment.getFullStrategyName()}.tab", "w") as f:
        createTab(f, getThroughputs(con, id))

