import ast
import os
import subprocess
import shutil
import sys

from context import Context
from codegen import generate

BUILTINS = {
    "print": "PYC_Print",
}


def main():
    target = sys.argv[1]
    with open(target) as f:
        source = f.read()
    tree = ast.parse(source, target)

    ctx = Context()
    with open("libpyc.c") as f:
        ctx.body_write(f.read() + "\n")

    for builtin, fn in BUILTINS.items():
        ctx.register_global(builtin, fn)
    
    generate(ctx, tree)

    # Create and move to working directory
    outdir = "bin"
    shutil.rmtree(outdir, ignore_errors=True)
    os.mkdir(outdir)
    os.chdir(outdir)

    with open("main.c", "w") as f:
        f.write(ctx.body.content)

        main = ctx.namings.get("main")["name"]
        f.write(f"""int main(int argc, char *argv[]) {{
  Py_Initialize();

  // Initialize globals, if any.
{ctx.initializations.content}
  PyObject* r = {main}();
  return PyLong_AsLong(r);
}}""")

    subprocess.run(["clang-format", "-i", "main.c"])

    cflags_raw = subprocess.check_output(["python3-config", "--cflags"])
    cflags = [f.strip() for f in cflags_raw.decode().split(" ") if f.strip()]
    cmd = ["gcc", "-c", "-o", "main.o"] + cflags + ["main.c"]
    subprocess.run(cmd)

    ldflags_raw = subprocess.check_output(["python3-config", "--ldflags"])
    ldflags = [f.strip() for f in ldflags_raw.decode().split(" ") if f.strip()]
    cmd = ["gcc"] + ldflags + ["main.o"]
    subprocess.run(cmd)


main()
