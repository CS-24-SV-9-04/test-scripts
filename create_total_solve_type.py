#!/usr/bin/python3
from argparse import ArgumentParser
from io import TextIOWrapper
from itertools import chain
import sqlite3
import sys
from typing import List

from analysis_helper import Experiment, getExperimentId


parser = ArgumentParser(prog="Generates comparison between all experiments based on data.db")
parser.add_argument("baseline", help="The baseline result to compare with uniques")
parser.add_argument("experiments", nargs='+', help="all experiments included in the matrix in <name>-<strategy> format")
args = parser.parse_args()

baseline = Experiment.fromFormat(args.baseline)
experiments: List[Experiment] = [Experiment.fromFormat(x) for x in args.experiments]

con = sqlite3.connect("data.db")

class SolveStats:
    def __init__(self, total: int, unique: int):
        self.total = total
        self.unique = unique

def getSolveStats(con: sqlite3.Connection, baselineId: int, experimentId: int) -> SolveStats:
    cur = con.execute("""
    SELECT 
        COUNT(*) FILTER (WHERE (qi.query_type = 'ef' AND qr1.result = 'Satisfied') OR (qi.query_type = 'ag' AND qr1.result = 'Unsatisfied')) AS counter_total, 
        COUNT(*) FILTER (WHERE (qi.query_type = 'ag' AND qr1.result = 'Satisfied') OR (qi.query_type = 'ef' AND qr1.result = 'Unsatisfied')) AS full_total,
        COUNT(*) FILTER (WHERE ((qi.query_type = 'ef' AND qr1.result = 'Satisfied') OR (qi.query_type = 'ag' AND qr1.result = 'Unsatisfied')) AND baseline.status != 'Answered') AS counter_total_unique,
        COUNT(*) FILTER (WHERE ((qi.query_type = 'ag' AND qr1.result = 'Satisfied') OR (qi.query_type = 'ef' AND qr1.result = 'Unsatisfied')) AND baseline.status != 'Answered') AS full_total_unique
    FROM query_instance qi
        LEFT JOIN query_result qr1 ON qr1.query_instance_id = qi.id AND qr1.experiment_id = ?
        LEFT JOIN query_result baseline on baseline.query_instance_id = qi.id AND baseline.experiment_id = ?
    """, (experimentId, baselineId))
    counter, full, counter_unique, full_unique = cur.fetchone()
    return SolveStats(counter, counter_unique), SolveStats(full, full_unique)

def writeTable(out: TextIOWrapper, solveStats: List[tuple[str, SolveStats, SolveStats]]):
    out.write(r"\begin{tabularx}{\textwidth}{X c c c c c}")
    out.write("\n\\toprule\n")
    out.write(r"\multirow{3}{*}{Strategy} & \multicolumn{5}{c}{Solve count} \\")
    out.write("\n\\cline{2-6}\n")
    out.write(r"& \multicolumn{2}{c}{Counter example} && \multicolumn{2}{c}{Full state space exploration}\\")
    out.write("\n\\cline{2-3}\\cline{5-6}\n")
    out.write(r"& Total & Unique && Total & Unique\\")
    out.write("\n\\midrule\n")
    for solveStat in solveStats:
        name, counterExampleSolves, fullStateSpaceSolve = solveStat
        out.write(f"{name}&{counterExampleSolves.total}&{counterExampleSolves.unique}&&{fullStateSpaceSolve.total}&{fullStateSpaceSolve.unique}\\\\\n")
    out.write("\\bottomrule\n")
    out.write("\\end{tabularx}")

solveStats = []

baselineId = getExperimentId(con, baseline)

for e in experiments:
    solveStats.append((e.getFullStrategyName(), *getSolveStats(con, baselineId, getExperimentId(con, e))))

writeTable(sys.stdout, solveStats)