#!/usr/bin/python3
from itertools import islice
import sqlite3
from analysis_helper import Experiment, getExperimentId

con = sqlite3.connect("data.db")

prettyNames = {
    "bCFP": "CFP ",
    "bColReduc": "SCR",
    "bLPQueryReduc": "LP + QS",
    "bNatty": "None",
    "bNoLP": "Default - LP",
    "bNoQuerySimplification": "Default - LP - QS",
    "bPartition": "CP",
    "bPor": "POR",
    "bQueryReduc": "QS",
    "bReduc": "SR",
    "bVarSym": "VS",
    "final_baseline": "Default",
    "main": "EC stable",
    "newSuccGenBugfix": "EC experimental",
    "final": "EC P9",
    "queryReduc8": "EC experimental + QS + LP"
}

baselineTargets = ["bCFP", "bColReduc", "bLPQueryReduc", "bNatty", "bNoLP", "bNoQuerySimplification", "bPartition", "bPor", "bQueryReduc", "bReduc", "bVarSym"]
other_targets = ["main-RDFS", "newSuccGenBugfix-RDFS", "queryReduc8-RDFS"]
experimentIds = [getExperimentId(con, Experiment.fromFormat(experimentFormat + "-default")) for experimentFormat in baselineTargets] + [getExperimentId(con, Experiment.fromFormat(experimentFormat)) for experimentFormat in other_targets]

nattyId = getExperimentId(con, Experiment.fromFormat("bNatty" + "-default")) 
mainId = getExperimentId(con, Experiment.fromFormat("main" + "-RDFS")) 

def main():
    cur = con.execute(f"""
        SELECT
            e.name,
            COUNT(*) FILTER (WHERE qr.status = "Answered") AS total_answered,
            COUNT(*) FILTER (WHERE (qi.query_type = "ef" AND qr.result = "Satisfied") OR (qi.query_type = "ag" AND qr.result = "Unsatisfied")) AS positive_answers,
            COUNT(*) FILTER (WHERE (qi.query_type = "ag" AND qr.result = "Satisfied") OR (qi.query_type = "ef" AND qr.result = "Unsatisfied")) AS negative_answers,
            COUNT(*) FILTER (WHERE qr.status = "Answered" AND nattyQr.status != "Answered") AS natty_unique_answers,
            COUNT(*) FILTER (WHERE qr.status = "Answered" AND mainQr.status != "Answered") AS main_unique_answers
        FROM query_result qr
            LEFT JOIN query_result nattyQr ON nattyQr.query_instance_id = qr.query_instance_id AND nattyQr.experiment_id = {nattyId}
            LEFT JOIN query_result mainQr ON mainQr.query_instance_id = qr.query_instance_id AND mainQr.experiment_id = {mainId}
            LEFT JOIN query_instance qi ON qi.id = qr.query_instance_id
            LEFT JOIN experiment e ON e.id = qr.experiment_id
        WHERE e.id IN ({",".join(map(lambda x: str(x), experimentIds))})
        GROUP BY qr.experiment_id
        ORDER BY total_answered DESC
    """)
    print("Name&Answers&Positive&Negative&Default unique&EC stable unique\\\\\\hline")
    for data in cur.fetchall():
        print(f"{prettyNames[data[0]]}&{"&".join(islice(map(lambda x: str(x), data), 1, None))}\\\\")

main()