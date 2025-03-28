#!/usr/bin/python3
from argparse import ArgumentParser
from io import TextIOWrapper
import sqlite3
from typing import List


parser = ArgumentParser(prog="Gets inconsistencies between the expected results from MCC and the experiment's result")
parser.add_argument("experiment", help="Name of experiment in the format <name>-<strategy>")
args = parser.parse_args()
EXPERIMENT = args.experiment

def getExperimentId(con: sqlite3.Connection, nameAndStrategy: str):
    name, strategy = nameAndStrategy.split("-")
    res = con.execute("SELECT id FROM experiment WHERE name=? AND search_strategy=?", (name, strategy))
    return res.fetchone()[0]

con = sqlite3.connect("data.db")

experiment_id = getExperimentId(con, EXPERIMENT)

cur = con.execute("""
SELECT qi.model_name, qi.query_name, qi.query_index, qr.result, qi.expected_answer FROM query_result qr LEFT JOIN query_instance qi ON qr.query_instance_id = qi.id
	WHERE qr.result != qi.expected_answer
	AND qr.experiment_id = ?
""", (experiment_id,))

l = cur.fetchall()
print("model name, category, query index, result, expected result")
for bob in l:
    print(f"{bob[0]}, {bob[1]}, {bob[2]}, {bob[3]}, {bob[4]}")