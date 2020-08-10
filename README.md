# pyc

A simple Python to C compiler written in Python making use of
libpython.

### Requirements

* GCC
* Python3
* libpython (python3-devel on Fedora)

### Example

Take a simple Python program:

```python
$ cat tests/fun_no_args.py
b = 4

def main():
    return 2 + b
```

And compile it:

```c
$ python3 pyc.py tests/fun_no_args.py
$ cat bin/main.c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

PyObject *b_0;
static PyObject* main_1(PyObject *self, PyObject *args) {
  PyObject* bo_2;;
  if (PyLong_Check(PyLong_FromLong(2)) && PyLong_Check(b_0)) {
    bo_2 = PyLong_FromLong(PyLong_AsLong(PyLong_FromLong(2)) + PyLong_AsLong(b_0));
  } else { bo_2 = PyLong_FromLong(0); }
  return bo_2;
}
int main(int argc, char *argv[]) {
  Py_Initialize();

  // Initialize globals, if any.
  b_0 = PyLong_FromLong(4);

  PyObject* py_result = main_1(0, 0);
  long result = PyLong_AsLong(py_result);
  Py_DECREF(py_result);
  return result;
}
```

And run the program built by pyc:

```bash
$ ./bin/a.out && echo $?
6
```
