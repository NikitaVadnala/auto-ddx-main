import typing as ty
from dataclasses import dataclass

@dataclass
class Row:
    id: str
    name: str
    sym: list[str]
    drugs: list[str]


class Sym:
    def __init__(self) -> None:
        self.path = "DK-1-searchable.tsv"
        # self.path = "../DK-1-searchable.tsv"
        self.mem: ty.List[Row] = list()
        self.__load()
        self.__sym = self.syms()
        
    
    def __load(self) -> None:
        with open(self.path) as f:
            for row in f.readlines():
                r = row.split("\t")
                self.mem.append(Row(id=r[0].strip(), name=r[1].strip(), 
                    sym=[sy.strip() for sy in r[2].split(",")],
                    drugs=[sy.strip() for sy in r[3].split(",")]))

    def add(self, sym: str):
        if sym not in self.__sym:
            raise ValueError("E: New Sym")
        self.mem = [
            row for row in self.mem
            if sym in row.sym or sym in row.name
        ]

    def match_dis(self) -> list[Row]:
        return self.mem
    
    def syms(self) -> set[str]:
        ret = set()
        for row in self.mem:
            ret = ret.union(set(row.sym))
            ret.add(row.name)
        return ret

if __name__ == "__main__":
    sym = Sym()
    # print(sym.mem)
    try:
        sym.add("fever")
        sym.add("mayank")
    except ValueError:
        pass
    # sym.add("cough")
    print([(row.name, row.drugs) for row in sym.match_dis()])