import asyncio
from enum import Enum
from html.parser import HTMLParser
from io import TextIOWrapper
from re import match, search
from time import sleep
from typing import Iterable
import urllib.request

class ParserState(Enum):
    INIT = 0
    READING_CATEGORY = 1,
    LOOK_FOR_TABLE = 2,
    READ_TABLE = 3,
    FOUND_MODEL_TITLE = 4,
    READ_RESULT = 5,
    READ_VARIATION = 6,
    FIND_RESULT_STRING = 7,
    READ_RESULT_STRING = 8


def getClasses(attrs: list[tuple[str, str | None]]) -> Iterable[str]:
    classAttr = next((x for x in attrs if x[0] == 'class'), None)
    if (classAttr is not None and classAttr[1] is not None):
        return classAttr[1].split(' ')
    return []
class MCCResultParser(HTMLParser):
    def __init__(self, output: TextIOWrapper, *args):
        super().__init__(*args)
        self.state = ParserState.INIT
        self.category = None
        self.currentModel = None
        self.currentVariation = None
        self.output = output
        self.resultCount = 0

    def handle_starttag(self, tag, attrs):
        if self.state == ParserState.INIT:
            if any(map(lambda x: x == 'secondarytitle', getClasses(attrs))):
                self.state = ParserState.READING_CATEGORY
        elif self.state == ParserState.LOOK_FOR_TABLE:
            if tag == "table":
                classAttr = next((x for x in attrs if x[0] == 'class'), None)
                if any(map(lambda x: x == 'results', classAttr[1].split(' '))):
                    self.state = ParserState.READ_TABLE
        elif self.state == ParserState.READ_TABLE or self.state == ParserState.READ_RESULT:
            if tag == "td" and any(map(lambda x: x == 'modelname', getClasses(attrs))):
                self.state = ParserState.FOUND_MODEL_TITLE
            elif (self.state == ParserState.READ_RESULT):
                if tag == "a" and any(map(lambda x: x == 'expectedresult', getClasses(attrs))):
                    self.state = ParserState.READ_VARIATION
        elif self.state == ParserState.FIND_RESULT_STRING:
            if tag == "b":
                self.state = ParserState.READ_RESULT_STRING
    
    def handle_endtag(self, tag):
        if self.state == ParserState.READING_CATEGORY:
            self.state = ParserState.LOOK_FOR_TABLE
        if self.state == ParserState.FOUND_MODEL_TITLE:
            self.state = ParserState.READ_RESULT

    def handle_data(self, data):
        if self.state == ParserState.READING_CATEGORY:
            m = search(r"Results for (.+)", data, )
            if (m is None):
                raise RuntimeError("Could not determine category")
            self.category = m.group(1)
            print(f"found category {self.category}")
        elif self.state == ParserState.FOUND_MODEL_TITLE:
            m = search(r"(.+) — (Colored|P/T)", data)
            if (m is None):
                print("found non matching model title")
                print(data)
                self.state = ParserState.READ_TABLE
                return
            modelType = 'COL' if m.group(2) == "Colored" else "PT"
            name = m[1]
            self.currentModel = f"{name}-{modelType}"
        elif self.state == ParserState.READ_VARIATION:
            self.currentVariation = data
            self.state = ParserState.FIND_RESULT_STRING
        elif self.state == ParserState.READ_RESULT_STRING:
            self.addAnswers(self.category, self.currentModel, self.currentVariation, data)
            self.state = ParserState.READ_RESULT

    def addAnswers(self, category: str, modelName: str, variation: str, answerString: str):
        queryIndex = 0
        for answer in answerString.replace(" ", "").replace(")", "").replace("(", ""):
            self.output.write(f"{modelName}-{variation},{category},{queryIndex},{answer}\n")
            queryIndex += 1
            self.resultCount += 1

links = [
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/ReachabilityCardinality.html&TITLE=Results%20for%20ReachabilityCardinality",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/ReachabilityFireability.html&TITLE=Results%20for%20ReachabilityFireability",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/LTLCardinality.html&TITLE=Results%20for%20LTLCardinality",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/LTLFireability.html&TITLE=Results%20for%20LTLFireability",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/CTLCardinality.html&TITLE=Results%20for%20CTLCardinality",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/CTLFireability.html&TITLE=Results%20for%20CTLFireability",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/OneSafe.html&TITLE=Results%20for%20OneSafe",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/Liveness.html&TITLE=Results%20for%20Liveness",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/StableMarking.html&TITLE=Results%20for%20StableMarking",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/QuasiLiveness.html&TITLE=Results%20for%20QuasiLiveness",
    "https://mcc.lip6.fr/2024/index.php?CONTENT=results/ReachabilityDeadlock.html&TITLE=Results%20for%20ReachabilityDeadlock"
]

def retrieveAndWriteAnswers(url: str, outf: TextIOWrapper):
    contents = urllib.request.urlopen(url).read().decode('utf-8')
    parser = MCCResultParser(outf)
    parser.feed(contents)
    print(f"got {parser.resultCount} total results")

with open("all_answers.csv", "w") as f:
    for link in links:
        print(f"Doing {link}")
        retrieveAndWriteAnswers(link, f)
