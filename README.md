# pyc

A simple Python to C compiler written in Python making use of
libpython.

### Requirements

* GCC
* Python3
* libpython (python3-devel on Fedora)
* clang-format

### Example

Take a simple Python program:

```python
$ cat tests/recursive_fib.py
def fib(n):
    if n == 0 or n == 1:
        return n

    return fib(n - 1) + fib(n - 2)


def main():
    print(fib(40))
```

Compile and run it:

```bash
$ python3 pyc tests/recursive_fib.py
$ ./bin/a.out
102334155
```

### Generated code

After compiling, the C program is stored in `bin/main.c`:

```c
$ cat bin/main.c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *PYC_Add(PyObject *l, PyObject *r) {
  // TODO: allow __add__ override

  // Includes ints and bools
  if (PyLong_Check(l) && PyLong_Check(r)) {
    return PyNumber_Add(l, r);
  }

  // TODO: handle str, etc.

  // TODO: throw exception
  return NULL;
}

static PyObject *PYC_Sub(PyObject *l, PyObject *r) {
  // TODO: allow __add__ override

  // Includes ints and bools
  if (PyLong_Check(l) && PyLong_Check(r)) {
    return PyNumber_Subtract(l, r);
  }

  // TODO: handle str, etc.

  // TODO: throw exception
  return NULL;
}

static PyObject *PYC_Print(PyObject *o) {
  PyObject_Print(o, stdout, Py_PRINT_RAW);
  printf("\n");
  return Py_None;
}

static PyObject *fib_0(PyObject *n_1) {
  PyObject *boolop_2;
  PyObject *compare_4 = n_1;
  PyObject *num_5 = PyLong_FromLong(0);
  compare_4 = PyObject_RichCompare(compare_4, num_5, Py_EQ);
  boolop_2 = compare_4;
  if (PyObject_IsTrue(compare_4)) {
    goto done_or_3;
  }
  PyObject *compare_6 = n_1;
  PyObject *num_7 = PyLong_FromLong(1);
  compare_6 = PyObject_RichCompare(compare_6, num_7, Py_EQ);
  boolop_2 = compare_6;
  if (PyObject_IsTrue(compare_6)) {
    goto done_or_3;
  }
done_or_3:

  if (PyObject_IsTrue(boolop_2)) {

    return n_1;
  }

  PyObject *binop_8;
  PyObject *binop_9;
  PyObject *num_10 = PyLong_FromLong(1);
  binop_9 = PYC_Sub(n_1, num_10);
  PyObject *call_result_11 = fib_0(binop_9);
  PyObject *binop_12;
  PyObject *num_13 = PyLong_FromLong(2);
  binop_12 = PYC_Sub(n_1, num_13);
  PyObject *call_result_14 = fib_0(binop_12);
  binop_8 = PYC_Add(call_result_11, call_result_14);

  return binop_8;
}

static PyObject *main_1() {
  PyObject *num_2 = PyLong_FromLong(40);
  PyObject *call_result_3 = fib_0(num_2);
  PyObject *call_result_4 = PYC_Print(call_result_3);
  // noop to hide unused warning
  call_result_4 += 0;
  return Py_None;
}

int main(int argc, char *argv[]) {
  Py_Initialize();

  // Initialize globals, if any.

  PyObject *r = main_1();
  return PyLong_AsLong(r);
}
```
