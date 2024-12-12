from argparse import ArgumentParser
from pathlib import Path
import re
from typing import List, Optional

parser = ArgumentParser(prog="Generates CSV report from the output of model checking jobs")
parser.add_argument("strategy")
args = parser.parse_args()

STRATEGY = args.strategy

QUERY_SATISFIED = "Query is satisfied"
QUERY_UNSATISFIED = "Query is NOT satisfied"
QUERY_TIMEOUT = "TIMEOUT"
OUT_OF_MEMORY = "std::bad_alloc"
TOO_MANY_BINDINGS = "TOO_MANY_BINDINGS"

class Metric:
    def __init__(self, name: str, time: Optional[float]):
        self.name = name
        self.time = time
metrics: List[Metric] = []

outputFiles = list(Path("./out/").glob(f"*_{STRATEGY}*.out"))
outputFiles.sort(key = lambda a : str(a).lower())
resultFile = open("results.csv", "w")
resultFile.write("Net,Category,Index,Result,Time,Memory\n")
pattern = r"#{6}\s+RUNNING\s+([^_]+)_([^\.]+)\.xml_([A-Za-z]+)\s+X\s+([0-9]+)\s+#{6}([^#]+)"
for outputPath in outputFiles:
    outContent = outputPath.read_text()
    errContent = (outputPath.parent / (outputPath.stem + ".err")).read_text()
    outMatches = re.finditer(pattern, outContent)
    errMatches = re.finditer(pattern, errContent)

    for outMatch, errMatch in zip(outMatches, errMatches):
        name = outMatch.group(1)
        category = outMatch.group(2)
        query_index = outMatch.group(4)
        outResult = outMatch.group(5)
        errResult = errMatch.group(5)
        timeMatch = re.search("TOTAL_TIME: ([0-9]+(\\.[0-9]+)?)", errResult)
        memoryMatch = re.search("MAX_MEMORY: ([0-9]+)kB", errResult)
        time = "unknown"
        status = ""
        maxMemory = "unknown"
        if (timeMatch != None):
            time = timeMatch.group(1)
        if (memoryMatch != None):
            maxMemory = memoryMatch.group(1)
        if (QUERY_SATISFIED in outResult):
            status = "satisfied"
        elif (QUERY_UNSATISFIED in outResult):
            status = "unsatisfied"
        elif (QUERY_TIMEOUT in outResult):
            status = "timeout"
            time = "n/a"
        elif (TOO_MANY_BINDINGS in outResult):
            status = "too many bindings"
            time = "n/a"
        elif (OUT_OF_MEMORY in errResult):
            status = "out of memory"
            time = "n/a"
        else:
            status = "error"
        resultFile.write(f"{name},{category},{query_index},{status},{time},{maxMemory}\n")
        if (time != "unknown" and time != "n/a"):
            metrics.append(Metric(name, float(time)))
        else:
            metrics.append(Metric(name, None))

resultFile.close()

cactusData = sorted(filter(lambda k: k.time != None, metrics), key = lambda m: m.time)

# Create cactus plot
cactusPlotOut = open("cactus.plot", "w")
cactusPlotOut.write("counter\ttime\n")
counter = 0
for point in cactusData:
    cactusPlotOut.write(f"{counter}\t{point.time}\n")
    counter += 1
cactusPlotOut.close()