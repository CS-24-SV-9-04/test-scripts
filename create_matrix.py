#!/usr/bin/python3
from argparse import ArgumentParser
from io import TextIOWrapper
from itertools import chain
import sqlite3
import sys
from typing import List

from analysis_helper import Experiment, getExperimentId


parser = ArgumentParser(prog="Generates comparison between two experiments based on data.db")
parser.add_argument("experiments", nargs='+', help="all experiments included in the matrix in <name>-<strategy> format")
args = parser.parse_args()

experiments = [Experiment.fromFormat(x) for x in args.experiments]
print(experiments)

con = sqlite3.connect("data.db")

matrix = [[0] * len(experiments) for _ in experiments]

def getUniques(a: Experiment, b: Experiment) -> tuple[int, int]:
    aId = getExperimentId(con, a)
    bId = getExperimentId(con, b)
    cur = con.execute(
        """
        SELECT 
            COUNT(*) FILTER (WHERE l.status == "Answered"),
            COUNT(*) FILTER (WHERE r.status == "Answered")
        FROM query_result l
        LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
        LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
        WHERE l.experiment_id = ? and r.experiment_id = ? AND (
            (l.status = "Answered" AND r.status != "Answered") 
            OR 
            (l.status != "Answered" AND r.status = "Answered")
        )
    """, (aId, bId))
    return cur.fetchone()

for aIndex in range(len(experiments)):
    for bIndex in range(len(experiments)):
        if (aIndex == bIndex):
            matrix[aIndex][bIndex] = 0
        a, b = getUniques(experiments[aIndex], experiments[bIndex])
        matrix[aIndex][bIndex] = b
        matrix[bIndex][aIndex] = a

def print_matrix(out: TextIOWrapper, matrix: List[List[int]]):
    evens = list(filter(lambda x: experiments[x].type == "even", range(len(experiments))))
    fixeds = list(filter(lambda x: experiments[x].type == "fixed", range(len(experiments))))
    baseline = next(filter(lambda x: experiments[x].type == "baseline", range(len(experiments))))
    sortedIndices = list(chain(chain(evens, fixeds), [baseline]))
    print(evens)
    print(fixeds)
    print(baseline)
    out.write(r"\begin{tabular}{|w{c}{0.1cm}|w{c}{0.7cm}|")
    out.write("c|" * len(experiments))
    out.write("}\n")
    out.write("\\hline\n")
    out.write(r"\multicolumn{2}{|c|}{} & ")
    if (len(fixeds) > 0):
        out.write(r"\multicolumn{")
        out.write(str(len(fixeds)))
        out.write(r"}{c|}{FIX} & ")
    if (len(evens) > 0):
        out.write(r"\multicolumn{")
        out.write(str(len(evens)))
        out.write(r"}{c|}{EVEN} & ")
    if (baseline is not None):
        out.write(r"\multirow{2}{*}{Baseline}")
    out.write(r"\\")
    out.write("\n")

    if (len(fixeds) > 0):
        out.write(f"\\cline{{3-{2 + len(fixeds)}}}")
    if (len(evens) > 0):
        out.write(f"\\cline{{{3 + len(fixeds)}-{2 + len(fixeds) + len(evens)}}}")
    out.write("\n")
    out.write(r"\multicolumn{2}{|c|}{}")
    for index in sortedIndices:
        if (experiments[index].type != "baseline"):
            out.write(f" & {experiments[index].strategy}")
        else:
            out.write(" & ")
    out.write(r"\\")
    out.write("\n")
    out.write("\\hline\n")

    if (len(fixeds) > 0):
        out.write(r"\multirow{")
        out.write(str(len(fixeds)))
        out.write(r"}{*}{\rotatebox[origin=c]{90}{FIX}}")
    for aIndex in fixeds:
        out.write(f"& {experiments[aIndex].strategy} ")
        for bIndex in sortedIndices:
            out.write(f"& {matrix[aIndex][bIndex]}")
        out.write(r"\\")
        out.write("\n")
        out.write(f"\\cline{{3-{2 + len(sortedIndices)}}}\n")
    if (len(fixeds) > 0):
        out.write("\\hline\n")
    for aIndex in evens:
        out.write(f"& {experiments[aIndex].strategy} ")
        for bIndex in sortedIndices:
            out.write(f"& {matrix[aIndex][bIndex]}")
        out.write(r"\\")
        out.write("\n")
        out.write(f"\\cline{{3-{2 + len(sortedIndices)}}}\n")
    if (len(evens) > 0):
        out.write("\\hline\n")
    if baseline is not None:
        out.write(r"\multicolumn{2}{|c|}{Baseline}")
        for bIndex in sortedIndices:
            out.write(f"& {matrix[baseline][bIndex]}")
        out.write(r"\\")
        out.write("\n")
        out.write(f"\\cline{{3-{2 + len(sortedIndices)}}}\n")
        out.write("\\hline\n")
    out.write("\\end{tabular}\n")

print_matrix(sys.stdout, matrix)