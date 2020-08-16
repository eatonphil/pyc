import copy


class Writer():
    content = ""

    def write(self, exp: str, indent: int = 0):
        self.content += ("  " * indent) + exp

    def writeln(self, stmt: str, indent: int = 0):
        self.write(stmt + "\n", indent)

    def write_statement(self, stmt: str, indent: int = 0):
        self.writeln(stmt + ";", indent)


class Context():
    declarations = Writer()
    initializations = Writer()
    body = Writer()
    indentation = 0

    scope = 0
    ret = None
    namings = {}
    counter = -1

    def __getattr__(self, name: str) -> object:
        # Helpers to avoid passing in self.indentation every time
        outputs = ["declarations", "initializations", "body"]
        for output in outputs:
            if name.startswith(output):
                return lambda s, i=None: getattr(getattr(self, output), name[len(output)+1:])(s, i if i is not None else self.indentation)

        return object.__getattr__(self, name)

    def get_local(self, source_name: str) -> dict:
        return self.namings[source_name]

    def register_global(self, name: str, loc: str):
        self.namings[name] = {
            "name": loc,
            "scope": 0,
        }

    def register_local(self, local: str = "tmp") -> str:
        self.counter += 1
        self.namings[local] = {
            "name": f"{local}_{self.counter}",
            # naming dictionary is copied, so we need to capture scope
            # at declaration
            "scope": self.scope,
        }
        return self.namings[local]["name"]

    def copy(self):
        new = copy.copy(self)
        # For some reason copy.deepcopy doesn't do this
        new.namings = dict(new.namings)
        return new

    def at_toplevel(self):
        return self.scope == 0
