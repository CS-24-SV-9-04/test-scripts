import sqlite3
from typing import Self

class Experiment:
    def __init__(self, name: str, strategy: str):
        self.name = name
        self.strategy = strategy
        if self.strategy.lower() == "default":
            self.type = "baseline"
        elif "e" in self.strategy.lower():
            self.type = "even"
        else:
            self.type = "fixed"
    def __repr__(self):
        return f"<Experiment {self.name} {self.strategy}>"
    
    @staticmethod
    def fromFormat(format: str) -> Self:
        name, strategy = format.split("-")
        return Experiment(name, strategy)
    
    def getFullStrategyName(self) -> str:
        if (self.type == "even"):
            return f"EVEN-{self.strategy}"
        elif (self.type == "fixed"):
            return f"FIX-{self.strategy}"
        else:
            return "baseline"

def getExperimentId(con: sqlite3.Connection, experiment: Experiment):
    res = con.execute("SELECT id FROM experiment WHERE name=? AND search_strategy=?", (experiment.name, experiment.strategy))
    return res.fetchone()[0]