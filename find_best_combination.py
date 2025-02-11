#!/usr/bin/python3
from argparse import ArgumentParser
from itertools import combinations, permutations
import sqlite3
from typing import List

from analysis_helper import Experiment, getExperimentId

con = sqlite3.connect("data.db")

parser = ArgumentParser(prog="Generates comparison between two experiments based on data.db")
parser.add_argument("experiments", nargs='+', help="all experiments included in the matrix in <name>-<strategy> format")
args = parser.parse_args()

experiments: List[Experiment] = [(Experiment.fromFormat(x), getExperimentId(con, Experiment.fromFormat(x))) for x in args.experiments]
i = 0
for perm in combinations(experiments, 4):
    cur = con.execute("""
        SELECT COUNT(*) FROM query_instance qi
	        LEFT JOIN query_result qr1 ON qr1.query_instance_id = qi.id AND qr1.experiment_id = ?
	        LEFT JOIN query_result qr2 ON qr2.query_instance_id = qi.id AND qr2.experiment_id = ?
	        LEFT JOIN query_result qr3 ON qr3.query_instance_id = qi.id AND qr3.experiment_id = ?
	        LEFT JOIN query_result qr4 ON qr4.query_instance_id = qi.id AND qr4.experiment_id = ?   
            WHERE qr1.status = "Answered" OR qr2.status = "Answered" OR qr3.status = "Answered" OR qr4.status = "Answered
    """)
    