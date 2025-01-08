#!/usr/bin/python3
from contextlib import closing
from io import TextIOWrapper
from os import remove
from pathlib import Path
import tarfile
from typing import Dict, List, Optional
import sqlite3
from result_parser import QueryInstance, Result, Status

def create_tables(con: sqlite3.Connection):
    con.execute("""
    CREATE TABLE experiment (id INTEGER PRIMARY KEY, name, search_strategy);
    """)

    con.execute("""
    CREATE TABLE query_instance (id INTEGER PRIMARY KEY, model_name, query_name, query_index)
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
        (queryInstance.model_name, queryInstance.query_name, queryInstance.query_index))
    id = res.fetchone()
    if (id is None):
        res = con.execute("INSERT INTO query_instance (model_name, query_name, query_index) VALUES (?, ?, ?) RETURNING id",
            (queryInstance.model_name, queryInstance.query_name, queryInstance.query_index))
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
            res = cur.execute("INSERT INTO query_result (experiment_id, query_instance_id, time, status, result, max_memory, states) VALUES (?,?,?,?,?,?,?) RETURNING id",
                (experimentId, queryInstanceId, result.time, result.status.name, result.result.name if result.result != None else None, result.maxMemory, result.states))
            cur.execute("INSERT INTO extended_result (query_result_id, stdout, stderr) VALUES (?, ?, ?)",
                (res.fetchone()[0], result.fullOut, result.fullErr)
            )

def generate_data(con: sqlite3.Connection, resultsFilePath: str):
    create_tables(con)
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