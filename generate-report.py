from pathlib import Path
import re


QUERY_SATISFIED = "Query is satisfied"
QUERY_UNSATISIFED = "Query is NOT satisfied"
QUERY_TIMEOUT = "TIMEOUT"

outputFiles = list(filter(lambda path : path.suffix == ".out", Path("./out/").iterdir()))
outputFiles.sort()
resultFile = open("results.csv", "w")
resultFile.write("Net,Category,Index,Result\n")
for outputPath in outputFiles:
    content = outputPath.read_text()
    matches = re.finditer("#{6}\\s+RUNNING\\s+([^_]+)_([^#\\.]+)\\.xml\\s+#{6}([^#]+)", content)
    for match in matches:
        name = match.group(1)
        category = match.group(2)
        outContent = match.group(3)
        status = ""
        if (QUERY_SATISFIED in outContent):
            status = "satisfied"
        elif (QUERY_UNSATISIFED in outContent):
            status = "unsatisfied"
        elif (QUERY_TIMEOUT in outContent):
            status = "timeout"
        else:
            status = "error"
        query_index = re.search("-x ([0-9]+)", outContent)
        resultFile.write(f"{name},{category},{query_index.group(1)},{status}\n")
        
        
resultFile.close()
