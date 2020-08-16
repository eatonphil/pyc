import ast
import os
import copy
import re
import subprocess
import shutil
import sys

BUILTINS = {
    "print": "PYC_Print",
}

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


def initialize_variable(ctx: Context, name: str, val: str):
    if ctx.at_toplevel():
        decl = f"PyObject* {name}"
        ctx.declarations_write_statement(decl, 0)

        init = f"{name} = {val}"
        ctx.initializations_write_statement(init)
    else:
        ctx.body_write_statement(f"PyObject* {name} = {val}")


def compile_bin_op(ctx: Context, binop: ast.BinOp) -> str:
    result = ctx.register_local("binop")
    ctx.body_write_statement(f"PyObject* {result}")

    l = compile_expression(ctx, binop.left)
    r = compile_expression(ctx, binop.right)

    if isinstance(binop.op, ast.Add):
        ctx.body_write_statement(f"{result} = PYC_Add({l}, {r})")
    elif isinstance(binop.op, ast.Sub):
        ctx.body_write_statement(f"{result} = PYC_Sub({l}, {r})")
    else:
        raise Exception(f"Unsupported binary operator: {type(binop.op)}")

    return result


def compile_bool_op(ctx: Context, boolop: ast.BoolOp) -> str:
    result = ctx.register_local("boolop")
    ctx.body_write_statement(f"PyObject* {result}")

    if isinstance(boolop.op, ast.Or):
        done_or = ctx.register_local("done_or")

        for exp in boolop.values:
            v = compile_expression(ctx, exp)
            ctx.body_write_statement(f"{result} = {v}")
            ctx.body_writeln(f"if (PyObject_IsTrue({v})) {{")
            ctx.body_write_statement(f"goto {done_or}", ctx.indentation+1)
            ctx.body_writeln("}")

        ctx.body_writeln(f"{done_or}:\n", 0)

    return result


def compile_compare(ctx: Context, exp: ast.Compare) -> str:
    result = ctx.register_local("compare")
    left = compile_expression(ctx, exp.left)
    ctx.body_write_statement(f"PyObject* {result} = {left}")

    for i, op in enumerate(exp.ops):
        v = compile_expression(ctx, exp.comparators[i])

        if isinstance(op, ast.Eq):
            ctx.body_write_statement(f"{result} = PyObject_RichCompare({result}, {v}, Py_EQ)")
        elif isinstance(op, ast.NotEq):
            ctx.body_write_statement(f"{result} = PyObject_RichCompare({result}, {v}, Py_NE)")
        else:
            raise Exception(f"Unsupported comparison: {type(op)}")

    return result


def compile_call(ctx: Context, exp: ast.Call) -> str:
    args = ', '.join([compile_expression(ctx, a) for a in exp.args])
    fun = compile_expression(ctx, exp.func)
    res = ctx.register_local("call_result")

    # TODO: lambdas and closures need additional work
    ctx.body_write_statement(
        f"PyObject* {res} = {fun}({args})")
    return res


def compile_expression(ctx: Context, exp) -> str:
    if isinstance(exp, ast.Num):
        # TODO: deal with non-integers
        tmp = ctx.register_local("num")
        initialize_variable(ctx, tmp, f"PyLong_FromLong({exp.n})")
        return tmp
    elif isinstance(exp, ast.BinOp):
        return compile_bin_op(ctx, exp)
    elif isinstance(exp, ast.BoolOp):
        return compile_bool_op(ctx, exp)
    elif isinstance(exp, ast.Name):
        return ctx.get_local(exp.id)["name"]
    elif isinstance(exp, ast.Compare):
        return compile_compare(ctx, exp)
    elif isinstance(exp, ast.Call):
        return compile_call(ctx, exp)

    raise Exception(f"Unsupported expression: {type(exp)}")


def compile_assign(ctx: Context, stmt: ast.Assign):
    # TODO: support assigning to a tuple
    local = ctx.register_local(stmt.targets[0].id)
    val = compile_expression(ctx, stmt.value)
    initialize_variable(ctx, local, val)


def compile_function_def(ctx: Context, fd: ast.FunctionDef):
    name = ctx.register_local(fd.name)

    childCtx = ctx.copy()
    args = ", ".join([f"PyObject* {childCtx.register_local(a.arg)}" for a in fd.args.args])
    ctx.body_writeln(f"static PyObject* {name}({args}) {{", 0)

    childCtx.scope += 1
    childCtx.indentation += 1
    compile(childCtx, fd)

    if not childCtx.ret:
        childCtx.body_write_statement("return Py_None")

    ctx.body_writeln("}\n", 0)


def compile_return(ctx: Context, r: ast.Return):
    ctx.ret = compile_expression(ctx, r.value)
    ctx.body_writeln("")
    ctx.body_write_statement(f"return {ctx.ret}")


def compile_if(ctx: Context, exp: ast.If):
    test = compile_expression(ctx, exp.test)
    ctx.body_writeln(f"if (PyObject_IsTrue({test})) {{")
    ctx.indentation += 1
    compile(ctx, exp)
    # TODO: handle exp.orelse
    ctx.indentation -= 1
    ctx.body_writeln("}\n")


def compile(ctx: Context, module):
    for stmt in module.body:
        if isinstance(stmt, ast.Assign):
            compile_assign(ctx, stmt)
        elif isinstance(stmt, ast.FunctionDef):
            compile_function_def(ctx, stmt)
        elif isinstance(stmt, ast.Return):
            compile_return(ctx, stmt)
        elif isinstance(stmt, ast.If):
            compile_if(ctx, stmt)
        elif isinstance(stmt, ast.Expr):
            r = compile_expression(ctx, stmt.value)
            ctx.body_writeln("// noop to hide unused warning")
            ctx.body_write_statement(f"{r} += 0")
        else:
            raise Exception(f"Unsupported statement type: {type(stmt)}")


def main():
    target = sys.argv[1]
    with open(target) as f:
        source = f.read()
    tree = ast.parse(source, target)

    ctx = Context()
    with open("libpyc.c") as f:
        ctx.declarations_write(f.read() + "\n")

    for builtin, fn in BUILTINS.items():
        ctx.register_global(builtin, fn)
    
    compile(ctx, tree)

    # Create and move to working directory
    outdir = "bin"
    shutil.rmtree(outdir, ignore_errors=True)
    os.mkdir(outdir)
    os.chdir(outdir)

    with open("main.c", "w") as f:
        f.write(ctx.declarations.content)
        f.write(ctx.body.content)

        main = ctx.namings.get("main")["name"]
        f.write(f"""int main(int argc, char *argv[]) {{
  Py_Initialize();

  // Initialize globals, if any.
{ctx.initializations.content}
  PyObject* r = {main}();
  return PyLong_AsLong(r);
}}""")

    cflags_raw = subprocess.check_output(["python3-config", "--cflags"])
    cflags = [f.strip() for f in cflags_raw.decode().split(" ") if f.strip()]
    cmd = ["gcc", "-c", "-o", "main.o"] + cflags + ["main.c"]
    subprocess.run(cmd)

    ldflags_raw = subprocess.check_output(["python3-config", "--ldflags"])
    ldflags = [f.strip() for f in ldflags_raw.decode().split(" ") if f.strip()]
    cmd = ["gcc"] + ldflags + ["main.o"]
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
