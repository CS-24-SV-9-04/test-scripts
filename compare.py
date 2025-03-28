#!/usr/bin/python3
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

createFileFromQuery(con, f"compared/memory_comparison.csv",
    ["model name", "query name", "query index", "memory usage a", "memory usage b", "factor"], """
    SELECT 
        qi.model_name, qi.query_name, qi.query_index, l.max_memory, r.max_memory, round(l.max_memory / r.max_memory, 2)
    FROM query_result l
    LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
    LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
    WHERE l.experiment_id = ? and r.experiment_id = ? AND (
        (l.status = "Answered" AND r.status = "Answered")
    )
    ORDER BY abs(l.max_memory / r.max_memory) DESC
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

total_cur = con.execute(
        """
        SELECT 
            COUNT(*) FILTER (WHERE lower(l.status) == "answered"),
            COUNT(*) FILTER (WHERE lower(r.status) == "answered")
        FROM query_result l
        LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
        LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
        WHERE l.experiment_id = ? and r.experiment_id = ?
    """, (aId, bId))

total_a, total_b = total_cur.fetchone()

cardinality_cur = con.execute(
        """
        SELECT 
            COUNT(*) FILTER (WHERE lower(l.status) = "answered"),
            COUNT(*) FILTER (WHERE lower(r.status) = "answered")
        FROM query_result l
        LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
        LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
        WHERE l.experiment_id = ? and r.experiment_id = ? AND qi.query_name = "ReachabilityCardinality"
    """, (aId, bId))

total_cardinality_a, total_cardinality_b = cardinality_cur.fetchone()

fireability_cur = con.execute(
        """
        SELECT 
            COUNT(*) FILTER (WHERE lower(l.status) = "answered"),
            COUNT(*) FILTER (WHERE lower(r.status) = "answered")
        FROM query_result l
        LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
        LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
        WHERE l.experiment_id = ? and r.experiment_id = ? AND qi.query_name = "ReachabilityFireability"
    """, (aId, bId))

total_fireability_a, total_fireability_b = fireability_cur.fetchone()

throughput_cur = con.execute(
        """
        SELECT 
            AVG(l.states/l.verification_time) FILTER (WHERE lower(l.status) == "answered" AND l.states > 4 and l.verification_time > 0),
            AVG(r.states/r.verification_time) FILTER (WHERE lower(r.status) == "answered" AND r.states > 4 and r.verification_time > 0)
        FROM query_result l
        LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
        LEFT JOIN query_instance qi ON qi.id == l.query_instance_id
        WHERE l.experiment_id = ? and r.experiment_id = ?
    """, (aId, bId))

throughput_a, throughput_b = throughput_cur.fetchone()

memory_usage_cur = con.execute(
        """
        SELECT 
            SUM(l.max_memory)/SUM(r.max_memory)
        FROM query_result l
        LEFT JOIN query_result r On r.query_instance_id = l.query_instance_id
        WHERE l.experiment_id = ? and r.experiment_id = ? and lower(l.status) == "answered" AND lower(r.status) == 'answered'
    """, (aId, bId))

memory_usage_ratio, = memory_usage_cur.fetchone()

resultsFile = open("compared/results.txt", "w")

resultsFile.write(f"total for {EXPERIMENT_A}: {total_a}\n")
resultsFile.write(f"cardinality for {EXPERIMENT_A}: {total_cardinality_a}\n")
resultsFile.write(f"fireablity for {EXPERIMENT_A}: {total_fireability_a}\n")
resultsFile.write(f"unique for {EXPERIMENT_A}: {unique_a}\n")
resultsFile.write(f"error for {EXPERIMENT_A}: {error_a}\n")
resultsFile.write(f"throughput for {EXPERIMENT_A}: {throughput_a}\n")
resultsFile.write(f"\n")
resultsFile.write(f"memory usage ratio ({EXPERIMENT_A}/{EXPERIMENT_B}): {round(memory_usage_ratio * 100, 2)}%\n")
resultsFile.write(f"\n")
resultsFile.write(f"total for {EXPERIMENT_B}: {total_b}\n")
resultsFile.write(f"cardinality for {EXPERIMENT_B}: {total_cardinality_b}\n")
resultsFile.write(f"fireablity for {EXPERIMENT_B}: {total_fireability_b}\n")
resultsFile.write(f"unique for {EXPERIMENT_B}: {unique_b}\n")
resultsFile.write(f"error for {EXPERIMENT_B}: {error_b}\n")
resultsFile.write(f"throughput for {EXPERIMENT_B}: {throughput_b}\n")
resultsFile.close()