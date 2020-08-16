#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject* PYC_Add(PyObject* l, PyObject* r) {
  // TODO: allow __add__ override

  // Includes ints and bools
  if (PyLong_Check(l) && PyLong_Check(r)) {
    return PyNumber_Add(l, r);
  }

  // TODO: handle str, etc.

  // TODO: throw exception
  return NULL;
}

static PyObject* PYC_Sub(PyObject* l, PyObject* r) {
  // TODO: allow __add__ override

  // Includes ints and bools
  if (PyLong_Check(l) && PyLong_Check(r)) {
    return PyNumber_Subtract(l, r);
  }

  // TODO: handle str, etc.

  // TODO: throw exception
  return NULL;
}

static PyObject* PYC_Print(PyObject* o) {
  PyObject_Print(o, stdout, Py_PRINT_RAW);
  printf("\n");
  return Py_None;
}
