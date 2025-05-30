import re
import random
import sys
import os

def getInhibitor(match, content, chance):
    expr = match.group('arcExpr')
    if random.randrange(chance) != 0:
        return expr
    source = match.group('source')
    target = match.group('target')
    cardinality = match.group('cardinality')
    if re.search(rf'<place id=\"{source}\">', content) == None:
        return expr
    return rf'''<arc id="{source}_to_{target}" source="{source}" target="{target}" type="inhibitor">
                <structure>
                    <numberof>
                        <subterm>
                            <numberconstant value="{cardinality}">
                                <positive/>
                            </numberconstant>
                        </subterm>
                    </numberof>
                </structure>
            </arc>'''

def addInhibitors(filePath, newFilePath, chance):
    file = open(filePath, 'r')
    content = file.read()
    file.close()
    (content, nArcs) = re.subn(r'(?P<arcExpr><arc.*?source=\"(?P<source>.*?)\"\s*?target=\"(?P<target>.*?)\"(?:.|\n)*?(?P<cardinality>\d*)\'(?:.|\n)*?</arc>)', lambda x: getInhibitor(x, content, chance), content)
    file = open(newFilePath, 'w')
    file.write(content)
    file.close()

def main():
    args = sys.argv[1:]
    print(args)
    chance = 5
    if len(args) < 1:
        path = "/"
    else:
        path = args[0]
        if len(args) >= 2:
            chance = int(args[1])
        if len(args) >= 3:
            random.seed(args[2])
    print("Using " + path + " as base directory")
    elements = os.scandir(path)
    changedModels = 0
    for element in elements:
        if element.is_dir():
            try:
                modelPath = os.path.join(element.path, "model.pnml")
                newModelPath = os.path.join(element.path, "inhibModel.pnml")
                addInhibitors(modelPath, newModelPath, chance)
                changedModels += 1
            except:
                continue
    print("Added " + str(changedModels) + " new models with inhibitor arcs")

if __name__ == "__main__":
    main()