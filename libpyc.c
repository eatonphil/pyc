#define PY_SSIZE_T_CLEAN
#include <Python.h>

inline PyObject* PYC_Print(PyObject* o) {
  PyObject_Print(o, stdout, Py_PRINT_RAW);
  printf("\n");
  Py_INCREF(Py_None);
  return Py_None;
}
