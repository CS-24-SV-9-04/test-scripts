#!/usr/bin/python3
from os import mkdir
from argparse import ArgumentParser
import sqlite3
from typing import List

from analysis_helper import Experiment, getExperimentId


parser = ArgumentParser(prog="Gathers all stderr and stdout for errors in given strategy")
parser.add_argument("experiment", help="Name of experiment in the format <name>-<strategy>")
args = parser.parse_args()
EXPERIMENT = Experiment.fromFormat(args.experiment)
try:
    mkdir("errors")
except FileExistsError:
    pass

con = sqlite3.connect("data.db")

experimentId = getExperimentId(con, EXPERIMENT)

res = con.execute("""
SELECT qi.model_name, qi.query_name, qi.query_index, er.stdout, er.stderr
    FROM query_result qr
    LEFT JOIN query_instance qi
        ON qi.id = qr.query_instance_id
    LEFT JOIN extended_result er
        ON qr.id = er.query_result_id
    WHERE
        lower(qr.status) = "error" AND qr.experiment_id = ?
""", (experimentId,))

for model_name, query_name, query_index, stdout, stderr in res.fetchall():
    with open(f"errors/{model_name}-{query_name}-{query_index}", "w") as f:
        f.write("STDOUT\n\n")
        f.write(stdout)
        f.write("\n\nSTDERR\n\n")
        f.write(stderr)