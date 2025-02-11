#!/usr/bin/python3
from contextlib import closing
from io import TextIOWrapper
from os import remove
from pathlib import Path
import tarfile
from typing import Dict, List, Optional, Tuple
import sqlite3
from result_parser import QueryInstance, Result, Status
import xml.etree.ElementTree as ET
import re

def create_tables(con: sqlite3.Connection):
    con.execute("""
    CREATE TABLE experiment (id INTEGER PRIMARY KEY, name, search_strategy);
    """)

    con.execute("""
    CREATE TABLE query_instance (id INTEGER PRIMARY KEY, model_name, query_name, query_index, query_type)
    """)

    con.execute("""
    CREATE TABLE query_result (
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
    CREATE TABLE extended_result (
        id INTEGER PRIMARY KEY,
        query_result_id,
        stdout,
        stderr,
        FOREIGN KEY(query_result_id) REFERENCES query_result(id)
    );
    """)

def parse_query_and_type(property: ET.ElementTree) -> Tuple[str, int, str]:
    name = property.find("./{http://mcc.lip6.fr/}id").text
    m = re.match(r".+\-([^-]+)\-[0-9]+\-([0-9]+)$", name)
    query_name = m.group(1)
    index = int(m.group(2)) + 1

    if property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}all-paths/{http://mcc.lip6.fr/}globally") is not None:
        return query_name, index, "ag"
    elif property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}exists-path/{http://mcc.lip6.fr/}finally") is not None:
        return query_name, index, "ef"
    else:
        raise Exception("error")

def create_query_instances(con: sqlite3.Connection, path: str):
    for modelDirectoryPath in Path(path).glob("*"):
        for queryFile in [modelDirectoryPath / "ReachabilityCardinality.xml", modelDirectoryPath / "ReachabilityFireability.xml"]:
            parsed = ET.parse(str(queryFile))
            for queryElement in parsed.iterfind(".//{http://mcc.lip6.fr/}property"):
                query_name, index, query_type = parse_query_and_type(queryElement)
                con.execute("""
                    INSERT INTO query_instance (model_name, query_name, query_index, query_type) VALUES (?, ?, ?, ?)
                """, (modelDirectoryPath.name, query_name, index, query_type))

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
            for memberInfo in resultTar.getmembers():
                if (memberInfo.path.endswith(".out")):
                    try:
                        errInfo = resultTar.getmember(memberInfo.path.removesuffix(".out") + ".err")
                        with resultTar.extractfile(memberInfo) as outFile:
                            with resultTar.extractfile(errInfo) as errFile:
                                outContent = outFile.read().decode()
                                errContent = errFile.read().decode()
                                results = Result.fromOutErr(outContent, errContent)
                                for result in results:
                                    name = createName(resultFilePath, result.strategy)
                                    if name not in resultDict:
                                        resultDict[name] = StrategyResults(resultFilePath.name.split(".")[0], result.strategy, dict())
                                    resultDict[name].results[result.query_instance.get_key()] = (result)
                    except KeyError:
                        print("missing err file for " + memberInfo.path)
    return resultDict


def getQueryInstance(con: sqlite3.Connection, queryInstance: QueryInstance) -> int:
    res = con.execute("SELECT id FROM query_instance WHERE model_name=? AND query_name=? AND query_index=?",
        (queryInstance.model_name, queryInstance.query_name, int(queryInstance.query_index)))
    id = res.fetchone()
    return id[0]

def insertResults(con: sqlite3.Connection, resultsDict: Dict[str, StrategyResults]):
    for strategy in resultsDict.values():
        experimentId: Optional[int] = None
        cur = con.cursor()
        res = cur.execute("INSERT INTO experiment (name, search_strategy) VALUES (?, ?) RETURNING id", (strategy.name, strategy.strategy))
        experimentId = res.fetchone()[0]
        print(f"adding {strategy.name}-{strategy.strategy}")
        for result in strategy.results.values():
            queryInstanceId = getQueryInstance(con, result.query_instance)
            res = cur.execute("INSERT INTO query_result (experiment_id, query_instance_id, time, status, result, max_memory, states, color_reduction_time, verification_time) VALUES (?,?,?,?,?,?,?,?,?) RETURNING id",
                (experimentId, queryInstanceId, result.time, result.status.name, result.result.name if result.result != None else None, result.maxMemory, result.states, result.colorReductionTime, result.verificationTime))
            cur.execute("INSERT INTO extended_result (query_result_id, stdout, stderr) VALUES (?, ?, ?)",
                (res.fetchone()[0], result.fullOut, result.fullErr)
            )

def generate_data(con: sqlite3.Connection, resultsFilePath: str):
    create_tables(con)
    create_query_instances(con, "/usr/local/share/mcc/")
    results = process_results(resultsFilePath)
    insertResults(con, results)

if __name__ == '__main__':
    try:
        remove("data.db")
    except FileNotFoundError:
        pass
    db = sqlite3.connect("data.db")
    generate_data(db, "many_results")
    db.commit()
    db.close()