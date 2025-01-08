#!/usr/bin/python3
from argparse import ArgumentParser
from io import TextIOWrapper
from itertools import chain
import sqlite3
import sys
from typing import List

from analysis_helper import Experiment, getExperimentId


parser = ArgumentParser(prog="Generates comparison between two experiments based on data.db")
parser.add_argument("-n", "--non-reduced", nargs='+', help="all experiments included in the matrix in <name>-<strategy> format")
parser.add_argument("-r", "--reduced", nargs='+', help="all experiments included in the matrix in <name>-<strategy> format")
args = parser.parse_args()


nonReduced: List[Experiment] = [Experiment.fromFormat(x) for x in args.non_reduced]
reduced: List[Experiment] = [Experiment.fromFormat(x) for x in args.reduced]

con = sqlite3.connect("data.db")

class SolveStats:
    def __init__(self, cardinality: int, fireability: int):
        self.cardinality = cardinality
        self.fireability = fireability

def getSolveStats(con: sqlite3.Connection, experimentId: int) -> SolveStats:
    print(experimentId)
    cur = con.execute(
        """
        SELECT 
            COUNT(*) FILTER (WHERE qi.query_name = "ReachabilityCardinality"),
            COUNT(*) FILTER (WHERE qi.query_name = "ReachabilityFireability")
        FROM query_result qr
            LEFT JOIN query_instance qi ON qi.id == qr.query_instance_id
        WHERE qr.experiment_id = ? AND qr.status == "Answered"
    """, (experimentId,))
    cardinality, fireability = cur.fetchone()
    return SolveStats(cardinality, fireability)

def writeTable(out: TextIOWrapper, solveStats: List[tuple[str, SolveStats, SolveStats]]):
    out.write(r"\begin{tabularx}{\textwidth}{X c c c c c}")
    out.write("\n\\toprule\n")
    out.write(r"\multirow{3}{*}{Strategy} & \multicolumn{5}{c}{Solve count} \\")
    out.write("\n\\cline{2-6}\n")
    out.write(r"& \multicolumn{2}{c}{Reduction} && \multicolumn{2}{c}{No reduction}\\")
    out.write("\n\\cline{2-3}\\cline{5-6}\n")
    out.write(r"& Cardinality & Fireability && Cardinality & Fireability\\")
    out.write("\n\\midrule\n")
    for solveStat in solveStats:
        name, reductionStat, noreductionStat = solveStat
        out.write(f"{name}&{reductionStat.cardinality}&{reductionStat.fireability}&&{noreductionStat.cardinality}&{noreductionStat.fireability}\\\\\n")
    out.write("\\bottomrule\n")
    out.write("\\end{tabularx}")

if (len(reduced) != len(nonReduced)):
    print("reduced and non reduced needs to be the same length")
    exit(1)


solveStats = []
for r, n in zip(reduced, nonReduced):
    if (r.strategy != n.strategy):
        print("mismatched strategy")
        print(f"reduced has {r.strategy}, non reduced has {n.strategy}")
        exit(1)
    solveStats.append((r.getFullStrategyName(), getSolveStats(con, getExperimentId(con, r)), getSolveStats(con, getExperimentId(con, n))))
print(solveStats)
writeTable(sys.stdout, solveStats)