
from enum import Enum
import re
from typing import Iterable, Optional, Self

QUERY_SATISFIED = "Query is satisfied"
QUERY_UNSATISFIED = "Query is NOT satisfied"
QUERY_TIMEOUT = "TIMEOUT"
OUT_OF_MEMORY = "std::bad_alloc"
TOO_MANY_BINDINGS = "TOO_MANY_BINDINGS"

class Status(Enum):
    Answered = 0,
    Timeout = 1,
    TooManyBindings = 2,
    OutOfMemory = 3,
    Error = 4
    def __str__(self):
        return self.name

class QueryResult(Enum):
    Satisfied = 0,
    Unsatisfied = 1
    def __str__(self):
        return self.name

class QueryInstance:
    def __init__(self,  model_name: str, query_name: str, query_index: str):
        self.model_name = model_name
        self.query_name = query_name
        self.query_index = query_index
    def get_key(self):
        return f"{self.model_name}:{self.query_name}:{self.query_index}"

pattern = r"#{6}\s+RUNNING\s+([^_]+)_([^\.]+)\.xml_([A-Za-z]+)\s+X\s+([0-9]+)\s+#{6}([^#]+)"

class Result:
    def __init__(self, query_instance: QueryInstance, time: Optional[float], status: Status, result: Optional[QueryResult], maxMemory: Optional[float], states: Optional[int], strategy: str, fullOut: str, fullErr: str):
        self.query_instance = query_instance
        self.time = time
        self.status = status
        self.result = result
        self.maxMemory = maxMemory
        self.states = states
        self.strategy = strategy
        self.fullOut = fullOut
        self.fullErr = fullErr

    @staticmethod
    def fromOutErr(out: str, err: str) -> Iterable[Self]:
        outMatches = re.finditer(pattern, out)
        errMatches = re.finditer(pattern, err)
        return map(lambda t: Result.__fromOutErrSingle(*t), zip(outMatches, errMatches))

    @staticmethod
    def __fromOutErrSingle(outMatch: re.Match, errMatch: re.Match) -> Self:
        name = outMatch.group(1)
        category = outMatch.group(2)
        strategy = outMatch.group(3)
        query_index = outMatch.group(4)
        outResult = outMatch.group(5)
        errResult = errMatch.group(5)
        timeMatch = re.search(r"TOTAL_TIME: ([0-9]+(\.[0-9]+)?)s", errResult)
        memoryMatch = re.search("MAX_MEMORY: ([0-9]+)kB", errResult)
        time = None
        status = Status.Error
        maxMemory = None
        result = None
        if (timeMatch != None):
            time = float(timeMatch.group(1))
        if (memoryMatch != None):
            maxMemory = float(memoryMatch.group(1))
        if (QUERY_SATISFIED in outResult):
            status = Status.Answered
            result = QueryResult.Satisfied
        elif (QUERY_UNSATISFIED in outResult):
            status = Status.Answered
            result = QueryResult.Unsatisfied
        elif (QUERY_TIMEOUT in outResult):
            status = Status.Timeout
            time = None
        elif (TOO_MANY_BINDINGS in outResult):
            status = Status.TooManyBindings
            time = None
        elif (OUT_OF_MEMORY in errResult):
            status = Status.OutOfMemory
            time = None
        else:
            status = Status.Error
        
        return Result(QueryInstance(name, category, query_index), time, status, result, maxMemory, None, strategy, outMatch.group(5), errMatch.group(5))
        

