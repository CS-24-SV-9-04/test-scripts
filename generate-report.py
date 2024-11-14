from pathlib import Path
import re


QUERY_SATISFIED = "Query is satisfied"
QUERY_UNSATISFIED = "Query is NOT satisfied"
QUERY_TIMEOUT = "TIMEOUT"

outputFiles = list(filter(lambda path : path.suffix == ".out", Path("./out/").iterdir()))
outputFiles.sort()
resultFile = open("results.csv", "w")
resultFile.write("Net,Category,Index,Result,Time\n")
for outputPath in outputFiles:
    content = outputPath.read_text()
    matches = re.finditer("#{6}\\s+RUNNING\\s+([^_]+)_([^\\.]+)\\.xml\\s+X\\s+([0-9]+)\\s+#{6}([^#]+)", content)
    for match in matches:
        name = match.group(1)
        category = match.group(2)
        query_index = match.group(3)
        outContent = match.group(4)
        time = "unknown"
        timeMatch = re.search("real\\s*([0-9]+m[0-9]+\\.[0-9]+s)", outContent)
        if (timeMatch != None):
            time = timeMatch.group(1)
        status = ""
        if (QUERY_SATISFIED in outContent):
            status = "satisfied"
        elif (QUERY_UNSATISFIED in outContent):
            status = "unsatisfied"
        elif (QUERY_TIMEOUT in outContent):
            status = "timeout"
            time = "n/a"
        else:
            status = "error"
        resultFile.write(f"{name},{category},{query_index},{status},{time}\n")
        
        
resultFile.close()
