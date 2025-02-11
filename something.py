#!/usr/bin/python3
from argparse import ArgumentParser
from io import TextIOWrapper
from os import mkdir
import sqlite3
from typing import List
from analysis_helper import Experiment, getExperimentId


parser = ArgumentParser(prog="Generates cactus graphs for all given experiments")
parser.add_argument("baseline")
parser.add_argument("experiment")
args = parser.parse_args()

con = sqlite3.connect("data.db")

baseline = Experiment.fromFormat(args.baseline)
experiment = Experiment.fromFormat(args.experiment)

baselineId = getExperimentId(con, baseline)
experimentId = getExperimentId(con, experiment)

def getData(con: sqlite3.Connection):
    cur = con.execute(f"""
        SELECT rqr.states, lqr.states FROM query_result lqr
            LEFT JOIN query_result rqr ON rqr.query_instance_id = lqr.query_instance_id AND rqr.experiment_id = ?
	        LEFT JOIN query_instance qi ON lqr.query_instance_id = qi.id
            WHERE lqr.experiment_id = ? 
            AND lqr.states IS NOT NULL
            AND rqr.states IS NOT NULL
            AND lqr.status = 'Answered'
            AND rqr.status = 'Answered'
            AND (qi.query_type = 'ef' AND lqr.result = 'Unsatisfied'
            OR qi.query_type = 'ag' AND lqr.result = 'Satisfied')
	        ORDER BY rqr.states ASC
    """, (baselineId, experimentId))
    return [(time[0], time[1]) for i, time in enumerate(cur.fetchall())]

def createTab(out: TextIOWrapper, data: List[tuple[int, float]]):
    out.write("baseline\tcomparison\n")
    for dataPoint in data:
        i, throughput = dataPoint
        out.write(f"{i}\t{throughput}\n")
try:
    mkdir("tables")
except FileExistsError:
    pass


with open(f"tables/statespace-{experiment.getFullStrategyName()}.tab", "w") as f:
    createTab(f, getData(con))

