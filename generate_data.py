#!/usr/bin/python3
from argparse import ArgumentParser
from contextlib import closing
from io import TextIOWrapper
from itertools import islice
from os import remove
from pathlib import Path
import tarfile
from typing import Dict, Iterator, List, Optional, Tuple
import sqlite3
from result_parser import QueryInstance, QueryResult, Result, Status
import xml.etree.ElementTree as ET
import re
import json
import typing
import csv

parser = ArgumentParser(prog="Generates a database with the data from many_results")
parser.add_argument("timeout", help="Sets a virtual timeout cut", default=100000, type=float)
parsed = parser.parse_args()
TIMEOUT = parsed.timeout


expected_answers = json.load(open("expected_answers.json", "r"))

def create_tables(con: sqlite3.Connection):
    
    con.execute("""
    CREATE TABLE IF NOT EXISTS experiment (id INTEGER PRIMARY KEY, name, search_strategy);
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS query_instance (id INTEGER PRIMARY KEY, model_name, query_name, query_index, query_type, expected_answer)
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS query_result (
        id INTEGER PRIMARY KEY,
        experiment_id,
        query_instance_id,
        time,
        status,
        result,
        max_memory,
        states,
        color_reduction_time,
        verification_time,
        FOREIGN KEY(experiment_id) REFERENCES experiment(id),
        FOREIGN KEY(query_instance_id) REFERENCES query_instance(id)
    );
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS extended_result (
        id INTEGER PRIMARY KEY,
        query_result_id,
        stdout,
        stderr,
        FOREIGN KEY(query_result_id) REFERENCES query_result(id)
    );
    """)

def parse_query_and_type(property: ET.ElementTree) -> Tuple[str, int, Optional[str]]:
    name = property.find("./{http://mcc.lip6.fr/}id").text
    m = re.match(r".+\-([^-0-9]+)\-([0-9]+\-)?([0-9]+)$", name)
    query_name = m.group(1)
    index = int(m.group(3)) + 1

    if property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}all-paths") is not None:
        return query_name, index, "ag"
    elif property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}exists-path") is not None:
        return query_name, index, "ef"
    elif property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}negation/{http://mcc.lip6.fr/}all-paths") is not None:
        return query_name, index, "ef"
    elif property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}negation/{http://mcc.lip6.fr/}exists-path") is not None:
        return query_name, index, "ag"
    else:
        return query_name, index, None

class ConsensusAnswer:
    def __init__(self, model_name: str, category: str, index: int, consensus: Optional[QueryResult]):
        self.model_name = model_name
        self.category = category
        self.index = index + 1
        self.consensus = consensus

def read_consensus_answers(answerPath: str) -> Iterator[ConsensusAnswer]:
    with open(answerPath, newline='') as csvFile:
        csvReader = csv.reader(csvFile)
        for row in csvReader:
            yield ConsensusAnswer(row[0], row[1], int(row[2]),
                QueryResult.Satisfied if row[3] == "T"
                    else (QueryResult.Unsatisfied if row[3] == "F" else None))

NON_DYNAMIC_QUERY_CATEGORIES = ["ReachabilityDeadlock", "OneSafe", "Liveness", "StableMarking", "QuasiLiveness"]
DYNAMIC_QUERY_CATEGORIES = ["ReachabilityCardinality", "ReachabilityFireability", "LTLCardinality", "LTLFireability", "CTLCardinality", "CTLFireability"]
def create_query_instances(con: sqlite3.Connection, path: str):
    known_models: set[str] = set()
    consensus_answers = read_consensus_answers('all_answers.csv')
    for consensus_answer in filter(lambda x : 'COL' in x.model_name, consensus_answers):
        known_models.add(consensus_answer.model_name)
        expected_answer = None
        if consensus_answer.consensus != None:
            expected_answer = consensus_answer.consensus.name
        if consensus_answer.category == "ReachabilityDeadlock":
            con.execute("""
                    INSERT INTO query_instance (model_name, query_name, query_index, query_type, expected_answer) VALUES (?, ?, ?, ?, ?)
                """, (consensus_answer.model_name, consensus_answer.category, consensus_answer.index, "ef", expected_answer))
            continue
        if consensus_answer.category in NON_DYNAMIC_QUERY_CATEGORIES:
            con.execute("""
                    INSERT INTO query_instance (model_name, query_name, query_index, query_type, expected_answer) VALUES (?, ?, ?, ?, ?)
                """, (consensus_answer.model_name, consensus_answer.category, consensus_answer.index, None, expected_answer))
            continue
        parsed = ET.parse(str(Path(path) / consensus_answer.model_name / (consensus_answer.category + ".xml")))
        #fix
        query_type = None
        for queryElement in islice(parsed.iterfind(".//{http://mcc.lip6.fr/}property"), consensus_answer.index - 1, consensus_answer.index):
            _, _, query_type = parse_query_and_type(queryElement)
        
        con.execute("""
                INSERT INTO query_instance (model_name, query_name, query_index, query_type, expected_answer) VALUES (?, ?, ?, ?, ?)
            """, (consensus_answer.model_name, consensus_answer.category, consensus_answer.index, query_type, expected_answer))
    for modelDirectoryPath in Path(path).glob("*"):
        model_name = modelDirectoryPath.name 
        if (modelDirectoryPath.name not in known_models):
            for queryCategory in DYNAMIC_QUERY_CATEGORIES:
                parsed = ET.parse(str(modelDirectoryPath / (queryCategory + ".xml")))
                for queryElement in parsed.iterfind(".//{http://mcc.lip6.fr/}property"):
                    query_name, index, query_type = parse_query_and_type(queryElement)
                    con.execute("""
                        INSERT INTO query_instance (model_name, query_name, query_index, query_type, expected_answer) VALUES (?, ?, ?, ?, ?)
                    """, (model_name, queryCategory, index, query_type, None))
            for queryCategory in NON_DYNAMIC_QUERY_CATEGORIES:
                if queryCategory == "ReachabilityDeadlock":
                    con.execute("""
                        INSERT INTO query_instance (model_name, query_name, query_index, query_type, expected_answer) VALUES (?, ?, ?, ?, ?)
                    """, (model_name, queryCategory, 1, "ef", None))
                    continue
                con.execute("""
                    INSERT INTO query_instance (model_name, query_name, query_index, query_type, expected_answer) VALUES (?, ?, ?, ?, ?)
                """, (model_name, queryCategory, 1, None, None))

class StrategyResults:
    def __init__(self, name: str, strategy: str, results: dict[str, Result]):
        self.name = name
        self.strategy = strategy
        self.results = results

def createName(filePath, strategy):
    return str(filePath.name) + ":" + strategy

def process_results(resultFilesPath: str) -> Dict[str, StrategyResults]:
    resultDict: Dict[str, StrategyResults] = dict()
    resultFilePaths = list(Path(resultFilesPath).glob(f"*.tar"))
    for resultFilePath in resultFilePaths:
        with tarfile.open(str(resultFilePath), "r") as resultTar:
            is_large_job = True
            try:
                resultTar.getmember("large")
            except KeyError:
                is_large_job = False
            for memberInfo in resultTar.getmembers():
                if (memberInfo.path.endswith(".out")):
                    try:
                        errInfo = resultTar.getmember(memberInfo.path.removesuffix(".out") + ".err")
                        with resultTar.extractfile(memberInfo) as outFile:
                            with resultTar.extractfile(errInfo) as errFile:
                                outContent = outFile.read().decode()
                                errContent = errFile.read().decode()
                                results = Result.fromOutErr(outContent, errContent, is_large_job)
                                for result in results:
                                    name = createName(resultFilePath, result.strategy)
                                    if name not in resultDict:
                                        resultDict[name] = StrategyResults(resultFilePath.name.split(".")[0], result.strategy, dict())
                                    resultDict[name].results[result.query_instance.get_key()] = (result)
                    except KeyError:
                        print("missing err file for " + memberInfo.path)
    return resultDict

def processResult(result: Result):
    if (result.time > TIMEOUT):
        result.time = None
        result.states = None
        result.result = None
        result.verificationTime = None
        result.colorReductionTime = None
        result.status = Status.Timeout


def getQueryInstance(con: sqlite3.Connection, queryInstance: QueryInstance) -> int:
    res = con.execute("SELECT id FROM query_instance WHERE model_name=? AND query_name=? AND query_index=?",
        (queryInstance.model_name, queryInstance.query_name, int(queryInstance.query_index)))
    id = res.fetchone()
    return id[0]

def insertResults(con: sqlite3.Connection, resultsDict: Dict[str, StrategyResults]):
    for strategy in resultsDict.values():
        experimentId: Optional[int] = None
        exists_cur = con.execute("SELECT * FROM experiment WHERE name = ? AND search_strategy = ?", (strategy.name, strategy.strategy))
        if (len(exists_cur.fetchall()) > 0):
            continue
        exists_cur.close()
        cur = con.cursor()
        res = cur.execute("INSERT INTO experiment (name, search_strategy) VALUES (?, ?) RETURNING id", (strategy.name, strategy.strategy))
        experimentId = res.fetchone()[0]
        print(f"adding {strategy.name}-{strategy.strategy}")
        for result in strategy.results.values():
            processResult(result)
            try:
                queryInstanceId = getQueryInstance(con, result.query_instance)
            except:
                print(result.query_instance.model_name, result.query_instance.query_index, result.query_instance.query_name)
                raise
            res = cur.execute("INSERT INTO query_result (experiment_id, query_instance_id, time, status, result, max_memory, states, color_reduction_time, verification_time) VALUES (?,?,?,?,?,?,?,?,?) RETURNING id",
                (experimentId, queryInstanceId, result.time, result.status.name, result.result.name if result.result != None else None, result.maxMemory, result.states, result.colorReductionTime, result.verificationTime))
            cur.execute("INSERT INTO extended_result (query_result_id, stdout, stderr) VALUES (?, ?, ?)",
                (res.fetchone()[0], result.fullOut, result.fullErr)
            )
        cur.close()
        con.commit()

def generate_data(con: sqlite3.Connection, resultsFilePath: str):
    create_tables(con)
    cur = con.execute("SELECT COUNT(*) FROM query_instance")
    if (cur.fetchone()[0] == 0):
        print("Creating query instances")
        create_query_instances(con, "/usr/local/share/mcc/")
        con.commit()
    print("Processing results")
    results = process_results(resultsFilePath)
    print("Inserting results")
    insertResults(con, results)

if __name__ == '__main__':
    db = sqlite3.connect("data.db")
    generate_data(db, "many_results")
    db.commit()
    db.close()