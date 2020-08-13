import ast
import copy
import os
import subprocess
import shutil
import sys


class Writer():
    content = ""

    def write(self, exp: str, indent: int = 0):
        self.content += ("  " * indent) + exp

    def write_statement(self, stmt: str, indent: int = 0):
        self.write(stmt + ";\n", indent)


class Namings():
    namings = {}
    counter = -1

    def get(self, source_name: str) -> str:
        return self.namings[source_name]

    def register(self, local: str) -> str:
        self.counter += 1
        self.namings[local] = f"{local}_{self.counter}"
        return self.namings[local]

    def tmp(self, prefix: str = "tmp") -> str:
        self.counter += 1
        tmp = f"{prefix}_{self.counter}"
        self.namings[tmp] = tmp
        return tmp


class Context():
    declarations = Writer()
    initializations = Writer()
    body = Writer()
    namings = Namings() 
    indentation = 0

    def copy(self) -> "Context":
        return copy.deepcopy(self)

    def at_toplevel(self):
        return self.indentation == 0

    def initialize_variable(self, name, val):
        if self.at_toplevel():
            decl = f"PyObject *{name}"
            self.declarations.write_statement(decl, 0)

            init = f"{name} = {val}"
            self.initializations.write_statement(init, 1)
        else:
            self.body.write_statement(f"PyObject *{name} = {val}", self.indentation)


def compile_bin_op(ctx: Context, bo: ast.BinOp) -> str:
    result = ctx.namings.tmp("bo")
    ctx.body.write_statement(f"PyObject* {result}", ctx.indentation)

    if isinstance(bo.op, ast.Add):
        l = compile_expression(ctx, bo.left)
        r = compile_expression(ctx, bo.right)
        # TODO: handle non-longs
        ctx.body.write(f"if (PyLong_Check({l}) && PyLong_Check({r})) {{\n", ctx.indentation)
        ctx.body.write_statement(f"{result} = PyLong_FromLong(PyLong_AsLong({l}) + PyLong_AsLong({r}))", ctx.indentation + 1)
        ctx.body.write(f"}} else {{ {result} = PyLong_FromLong(0); }}\n", ctx.indentation)

    return result


def compile_expression(ctx: Context, exp) -> str:
    if isinstance(exp, ast.Num):
        # TODO: deal with non-integers
        tmp = ctx.namings.tmp()
        ctx.initialize_variable(tmp, f"PyLong_FromLong({exp.n})")
        return tmp
    elif isinstance(exp, ast.BinOp):
        return compile_bin_op(ctx, exp)
    elif isinstance(exp, ast.Name):
        return ctx.namings.get(exp.id)

    raise Exception(f"Unsupported type: {type(exp)}")


def compile_assign(ctx: Context, stmt: ast.Assign):
    # TODO: support assigning to a tuple
    local = ctx.namings.register(stmt.targets[0].id)
    val = compile_expression(ctx, stmt.value)
    ctx.initialize_variable(local, val)


def compile_function_def(ctx: Context, fd: ast.FunctionDef):
    name = ctx.namings.register(fd.name)
    ctx.body.write(f"static PyObject* {name}(PyObject *self, PyObject *args) {{\n", 0)
    childCtx = ctx.copy()
    childCtx.indentation += 1

    compile(childCtx, fd)
    ctx.body.write("}\n", 0)


def compile_return(ctx: Context, r: ast.Return):
    exp = compile_expression(ctx, r.value)
    ctx.body.write_statement(f"return {exp}", ctx.indentation)


def compile(ctx: Context, module):
    for stmt in module.body:
        if isinstance(stmt, ast.Assign):
            compile_assign(ctx, stmt)
        elif isinstance(stmt, ast.FunctionDef):
            compile_function_def(ctx, stmt)
        elif isinstance(stmt, ast.Return):
            compile_return(ctx, stmt)
        else:
            raise Exception(f"Unsupported statement type: {type(stmt)}")


def main():
    target = sys.argv[1]
    with open(target) as f:
        source = f.read()
    tree = ast.parse(source, target)

    ctx = Context()
    ctx.declarations.write("""#define PY_SSIZE_T_CLEAN
#include <Python.h>

""")
    
    compile(ctx, tree)

    # Create and move to working directory
    outdir = "bin"
    shutil.rmtree(outdir, ignore_errors=True)
    os.mkdir(outdir)
    os.chdir(outdir)

    with open("main.c", "w") as f:
        f.write(ctx.declarations.content)
        f.write(ctx.body.content)

        main = ctx.namings.get("main")
        f.write(f"""int main(int argc, char *argv[]) {{
  Py_Initialize();

  // Initialize globals, if any.
{ctx.initializations.content}
  PyObject* py_result = {main}(0, 0);
  long result = PyLong_AsLong(py_result);
  Py_DECREF(py_result);
  return result;
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
