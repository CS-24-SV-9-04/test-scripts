from argparse import ArgumentParser
from io import TextIOWrapper
import sqlite3
from typing import List


parser = ArgumentParser(prog="Generates comparison between two experiments based on data.db")
parser.add_argument("experiment_a", help="Name of experiment in the format <name>-<strategy>")
parser.add_argument("experiment_b", help="Name of experiment in the format <name>-<strategy>")
args = parser.parse_args()
EXPERIMENT_A = args.experiment_a
EXPERIMENT_B = args.experiment_b

def getExperimentId(con: sqlite3.Connection, nameAndStrategy: str):
    name, strategy = nameAndStrategy.split("-")
    res = con.execute("SELECT id FROM experiment WHERE name=? AND search_strategy=?", (name, strategy))
    return res.fetchone()[0]

con = sqlite3.connect("data.db")

aId = getExperimentId(con, EXPERIMENT_A)
bId = getExperimentId(con, EXPERIMENT_B)


def writeToCSV(file: TextIOWrapper, *args):
    file.write(",".join(map(lambda x: str(x), args)) + "\n")

def createFileFromQuery(con: sqlite3.Connection, filename: str, headers: List[str], query: str, data: tuple):
    res = con.execute(query, data)
    inconsistenciesFile = open(filename, "w")
    writeToCSV(inconsistenciesFile, *headers)
    for inconsistency in res.fetchall():
        writeToCSV(inconsistenciesFile, *inconsistency)
    inconsistenciesFile.close()


createFileFromQuery(con, "compared/inconsistencies.csv",
    ["model name", "query name", "query index", f"{EXPERIMENT_A} result", f"{EXPERIMENT_B} result"], """
    SELECT qi.model_name, qi.query_name, qi.query_index, l.result, r.result as b_result FROM query_result l
        LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
        LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
        WHERE l.experiment_id = ? and r.experiment_id = ? and l.result IS NOT NULL AND r.result IS NOT NULL AND l.result != r.result 
""", (aId, bId))

for experimentId, name in [(aId, "a"), (bId, "b")]:
    createFileFromQuery(con, f"compared/errors_{name}.csv", 
        ["Model name, Query name, Query index, Status, Max memory"],
        """
        SELECT qi.model_name, qi.query_name, qi.query_index, l.status, l.max_memory
        FROM query_result l
        LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
        WHERE l.experiment_id = ? AND lower(l.status) = "error"
    """, (experimentId,))

for leftId, rightId, name in [(aId, bId, "a"), (bId, aId, "b")]:
    createFileFromQuery(con, f"compared/uniques_{name}.csv",
        ["model name", "query name", "query index"], """
        SELECT 
            qi.model_name, qi.query_name, qi.query_index
        FROM query_result l
        LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
        LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
        WHERE l.experiment_id = ? and r.experiment_id = ? AND (
            (l.status = "Answered" AND r.status != "Answered")
        )
    """, (leftId, rightId))

unique_cur = con.execute(
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

unique_a, unique_b = unique_cur.fetchone()

error_cur = con.execute(
        """
        SELECT 
            COUNT(*) FILTER (WHERE lower(l.status) == "error"),
            COUNT(*) FILTER (WHERE lower(r.status) == "error")
        FROM query_result l
        LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
        LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
        WHERE l.experiment_id = ? and r.experiment_id = ?
    """, (aId, bId))

error_a, error_b = error_cur.fetchone()

resultsFile = open("compared/results.txt", "w")

resultsFile.write(f"unique for {EXPERIMENT_A}: {unique_a}\n")
resultsFile.write(f"error for {EXPERIMENT_A}: {error_a}\n")
resultsFile.write(f"\n")
resultsFile.write(f"unique for {EXPERIMENT_B}: {unique_b}\n")
resultsFile.write(f"error for {EXPERIMENT_B}: {error_b}\n")

resultsFile.close()