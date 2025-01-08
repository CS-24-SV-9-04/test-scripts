#!/usr/bin/python3
from argparse import ArgumentParser
from io import TextIOWrapper
from itertools import chain
from os import mkdir
import sqlite3
import sys
from typing import List

from analysis_helper import Experiment, getExperimentId


parser = ArgumentParser(prog="Generates cactus graphs for all given experiments")
parser.add_argument("time_lower_threshold", type=float)
parser.add_argument("experiments", nargs='+', help="all experiments included in the matrix in <name>-<strategy> format")
args = parser.parse_args()

con = sqlite3.connect("data.db")

allExperimentIds = [getExperimentId(con, Experiment.fromFormat(experimentFormat)) for experimentFormat in args.experiments]
allExperiments: List[Experiment] = [Experiment.fromFormat(experimentFormat) for experimentFormat in args.experiments]

def getSkipCount(con: sqlite3.Connection, all_experiments: List[int], time_lower_threshold: float):
    cur = con.execute(f"""
        SELECT COUNT(*) FROM (
        SELECT 
            iqi.id
        FROM query_result iqr
            LEFT JOIN query_instance iqi ON iqi.id = iqr.query_instance_id
        WHERE iqr.experiment_id IN ({("?," * len(all_experiments))[:-1]})
        GROUP BY iqr.query_instance_id
        HAVING MAX(iqr.time) < ? AND COUNT(iqr.time) = COUNT(*))
    """, (*all_experiments, time_lower_threshold))
    return cur.fetchone()[0]

skipCount = getSkipCount(con, allExperimentIds, args.time_lower_threshold)

def getTimes(con: sqlite3.Connection, experiment: int, all_experiments: List[int], time_lower_threshold: float):
    cur = con.execute(f"""
        SELECT qr.time FROM query_result qr
        WHERE qr.experiment_id = ? AND qr.status = "Answered" 
            AND qr.query_instance_id NOT IN (
            SELECT 
                iqi.id
                FROM query_result iqr
                LEFT JOIN query_instance iqi ON iqi.id = iqr.query_instance_id
                WHERE iqr.experiment_id IN ({("?," * len(all_experiments))[:-1]})
                GROUP BY iqr.query_instance_id
                HAVING MAX(iqr.time) < ? AND COUNT(iqr.time) = COUNT(*)
            )
            ORDER BY qr.time
    """, (experiment, *all_experiments, time_lower_threshold))
    return [(skipCount + i, time[0]) for i, time in enumerate(cur.fetchall())]

def createTab(out: TextIOWrapper, data: List[tuple[int, float]]):
    out.write("counter\ttime\n")
    for dataPoint in data:
        i, time = dataPoint
        out.write(f"{i}\t{time}\n")
try:
    mkdir("tables")
except FileExistsError:
    pass

for experiment in allExperiments:
    id = getExperimentId(con, experiment)
    with open(f"tables/{experiment.getFullStrategyName()}.tab", "w") as f:
        createTab(f, getTimes(con, id, allExperimentIds, args.time_lower_threshold))
