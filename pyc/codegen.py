import ast

from context import Context


def initialize_variable(ctx: Context, name: str, val: str):
    if ctx.at_toplevel():
        decl = f"PyObject* {name}"
        ctx.body_write_statement(decl, 0)

        init = f"{name} = {val}"
        ctx.initializations_write_statement(init)
    else:
        ctx.body_write_statement(f"PyObject* {name} = {val}")


def generate_bin_op(ctx: Context, binop: ast.BinOp) -> str:
    result = ctx.register_local("binop")
    ctx.body_write_statement(f"PyObject* {result}")

    l = generate_expression(ctx, binop.left)
    r = generate_expression(ctx, binop.right)

    if isinstance(binop.op, ast.Add):
        ctx.body_write_statement(f"{result} = PyNumber_Add({l}, {r})")
    elif isinstance(binop.op, ast.Sub):
        ctx.body_write_statement(f"{result} = PyNumber_Subtract({l}, {r})")
    else:
        raise Exception(f"Unsupported binary operator: {type(binop.op)}")

    return result


def generate_bool_op(ctx: Context, boolop: ast.BoolOp) -> str:
    result = ctx.register_local("boolop")
    ctx.body_write_statement(f"PyObject* {result}")

    if isinstance(boolop.op, ast.Or):
        done_or = ctx.register_local("done_or")

        for exp in boolop.values:
            v = generate_expression(ctx, exp)
            ctx.body_write_statement(f"{result} = {v}")
            ctx.body_writeln(f"if (PyObject_IsTrue({v})) {{")
            ctx.body_write_statement(f"goto {done_or}", ctx.indentation+1)
            ctx.body_writeln("}")

        ctx.body_writeln(f"{done_or}:\n", 0)

    return result


def generate_compare(ctx: Context, exp: ast.Compare) -> str:
    result = ctx.register_local("compare")
    left = generate_expression(ctx, exp.left)
    ctx.body_write_statement(f"PyObject* {result} = {left}")

    for i, op in enumerate(exp.ops):
        v = generate_expression(ctx, exp.comparators[i])

        if isinstance(op, ast.Eq):
            ctx.body_write_statement(f"{result} = PyObject_RichCompare({result}, {v}, Py_EQ)")
        elif isinstance(op, ast.NotEq):
            ctx.body_write_statement(f"{result} = PyObject_RichCompare({result}, {v}, Py_NE)")
        else:
            raise Exception(f"Unsupported comparison: {type(op)}")

    return result


def generate_call(ctx: Context, exp: ast.Call) -> str:
    args = ', '.join([generate_expression(ctx, a) for a in exp.args])
    fun = generate_expression(ctx, exp.func)
    res = ctx.register_local("call_result")

    # TODO: lambdas and closures need additional work
    ctx.body_write_statement(
        f"PyObject* {res} = {fun}({args})")
    return res


def generate_expression(ctx: Context, exp) -> str:
    if isinstance(exp, ast.Num):
        # TODO: deal with non-integers
        tmp = ctx.register_local("num")
        initialize_variable(ctx, tmp, f"PyLong_FromLong({exp.n})")
        return tmp
    elif isinstance(exp, ast.BinOp):
        return generate_bin_op(ctx, exp)
    elif isinstance(exp, ast.BoolOp):
        return generate_bool_op(ctx, exp)
    elif isinstance(exp, ast.Name):
        return ctx.get_local(exp.id)["name"]
    elif isinstance(exp, ast.Compare):
        return generate_compare(ctx, exp)
    elif isinstance(exp, ast.Call):
        return generate_call(ctx, exp)

    raise Exception(f"Unsupported expression: {type(exp)}")


def generate_assign(ctx: Context, stmt: ast.Assign):
    # TODO: support assigning to a tuple
    local = ctx.register_local(stmt.targets[0].id)
    val = generate_expression(ctx, stmt.value)
    initialize_variable(ctx, local, val)


def generate_function_def(ctx: Context, fd: ast.FunctionDef):
    name = ctx.register_local(fd.name)

    childCtx = ctx.copy()
    args = ", ".join([f"PyObject* {childCtx.register_local(a.arg)}" for a in fd.args.args])
    ctx.body_writeln(f"PyObject* {name}({args}) {{", 0)

    childCtx.scope += 1
    childCtx.indentation += 1
    generate(childCtx, fd)

    if not childCtx.ret:
        childCtx.body_write_statement("return Py_None")

    ctx.body_writeln("}\n", 0)


def generate_return(ctx: Context, r: ast.Return):
    ctx.ret = generate_expression(ctx, r.value)
    ctx.body_writeln("")
    ctx.body_write_statement(f"return {ctx.ret}")


def generate_if(ctx: Context, exp: ast.If):
    test = generate_expression(ctx, exp.test)
    ctx.body_writeln(f"if (PyObject_IsTrue({test})) {{")
    ctx.indentation += 1
    generate(ctx, exp)
    # TODO: handle exp.orelse
    ctx.indentation -= 1
    ctx.body_writeln("}\n")


def generate(ctx: Context, module):
    for stmt in module.body:
        if isinstance(stmt, ast.Assign):
            generate_assign(ctx, stmt)
        elif isinstance(stmt, ast.FunctionDef):
            generate_function_def(ctx, stmt)
        elif isinstance(stmt, ast.Return):
            generate_return(ctx, stmt)
        elif isinstance(stmt, ast.If):
            generate_if(ctx, stmt)
        elif isinstance(stmt, ast.Expr):
            r = generate_expression(ctx, stmt.value)
            ctx.body_writeln("// noop to hide unused warning")
            ctx.body_write_statement(f"{r} += 0")
        else:
            raise Exception(f"Unsupported statement type: {type(stmt)}")
