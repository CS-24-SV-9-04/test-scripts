#!/usr/bin/python3
from argparse import ArgumentParser
from io import TextIOWrapper
from itertools import chain
from pathlib import Path
import re
from typing import Iterable, List, Optional

from result_parser import QueryResult, Result, Status

parser = ArgumentParser(prog="Generates CSV report from the output of model checking jobs")
parser.add_argument("strategy")
args = parser.parse_args()

STRATEGY = args.strategy

resultsIter: Iterable[Result] = iter([])

outputFiles = list(Path("./out/").glob(f"*_{STRATEGY}*.out"))
outputFiles.sort(key = lambda a : str(a).lower())
resultFile = open("results.csv", "w")
resultFile.write("Net,Category,Index,Result,Time,Memory\n")

def writeToCSV(file: TextIOWrapper, *args):
    resultFile.write(",".join(map(lambda x: str(x), args)) + "\n")

def toOldStatus(status: Status, query_result: Optional[QueryResult]):
    if (status == Status.Answered):
        return "satisfied" if query_result == QueryResult.Satisfied else "unsatisfied"
    elif (status == Status.OutOfMemory):
        return "out of memory"
    elif (status == Status.Error):
        return "error"
    elif (status == Status.Timeout):
        return "timeout"
    elif (status == Status.TooManyBindings):
        return "too many bindings"
    else:
        return "unknown"

for outputPath in outputFiles:
    outContent = outputPath.read_text()
    errContent = (outputPath.parent / (outputPath.stem + ".err")).read_text()
    resultsIter = chain(resultsIter, Result.fromOutErr(outContent, errContent))

results = list(resultsIter)

for result in results:
    writeToCSV(
        resultFile,
        result.query_instance.model_name,
        result.query_instance.query_name,
        result.query_instance.query_index,
        toOldStatus(result.status, result.result),
        result.time if result.time != None else "n/a",
        result.maxMemory if result.time != None else "unknown"
    )

resultFile.close()

cactusData = sorted(filter(lambda k: k.status == Status.Answered and k.time != None, results), key = lambda m: m.time)

# Create cactus plot
cactusPlotOut = open("cactus.plot", "w")
cactusPlotOut.write("counter\ttime\n")
counter = 0
for point in cactusData:
    cactusPlotOut.write(f"{counter}\t{point.time}\n")
    counter += 1
cactusPlotOut.close()