#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>

#define RQM_ADAPTER_NATIVE_API 1

typedef struct {
    PyObject_HEAD
    PyObject *records;
    int supported;
} OperationCollector;

static PyTypeObject OperationCollectorType;
static PyObject *QuantumCircuitClass = NULL;
static PyObject *QuantumRegisterClass = NULL;
static PyObject *CircuitInstructionClass = NULL;
static PyObject *CircuitDataClass = NULL;

static int
unicode_equals(PyObject *value, const char *text)
{
    int comparison;
    if (!PyUnicode_Check(value)) {
        return 0;
    }
    comparison = PyUnicode_CompareWithASCIIString(value, text);
    if (comparison < 0 && PyErr_Occurred()) {
        return -1;
    }
    return comparison == 0;
}

static int
optional_attr_is_none(PyObject *value, const char *name)
{
    PyObject *attribute = PyObject_GetAttrString(value, name);
    int is_none;
    if (attribute == NULL) {
        if (PyErr_ExceptionMatches(PyExc_AttributeError)) {
            PyErr_Clear();
            return 1;
        }
        return -1;
    }
    is_none = attribute == Py_None;
    Py_DECREF(attribute);
    return is_none;
}

static PyObject *
collector_call(PyObject *self_object, PyObject *args, PyObject *kwargs)
{
    OperationCollector *self = (OperationCollector *)self_object;
    PyObject *operation = NULL;
    PyObject *name = NULL;
    PyObject *params = NULL;
    PyObject *angle_object = NULL;
    PyObject *canonical_name = NULL;
    PyObject *record = NULL;
    PyObject *num_qubits_object = NULL;
    PyObject *num_clbits_object = NULL;
    Py_ssize_t parameter_count;
    long num_qubits;
    long num_clbits;
    int is_angle = 0;
    int match;
    const char *canonical_text = NULL;

    if (kwargs != NULL && PyDict_Size(kwargs) != 0) {
        PyErr_SetString(PyExc_TypeError, "operation callback accepts no keywords");
        return NULL;
    }
    if (!PyArg_UnpackTuple(args, "operation", 1, 1, &operation)) {
        return NULL;
    }
    if (!self->supported) {
        Py_RETURN_NONE;
    }

    name = PyObject_GetAttrString(operation, "name");
    num_qubits_object = PyObject_GetAttrString(operation, "num_qubits");
    num_clbits_object = PyObject_GetAttrString(operation, "num_clbits");
    if (name == NULL || num_qubits_object == NULL || num_clbits_object == NULL) {
        goto error;
    }
    num_qubits = PyLong_AsLong(num_qubits_object);
    num_clbits = PyLong_AsLong(num_clbits_object);
    if ((num_qubits == -1 || num_clbits == -1) && PyErr_Occurred()) {
        goto error;
    }
    match = optional_attr_is_none(operation, "condition");
    if (match < 0) {
        goto error;
    }
    if (num_qubits != 1 || num_clbits != 0 || !match) {
        self->supported = 0;
        goto unsupported;
    }

#define MATCH_GATE(qiskit_name, canonical_gate, angle_gate)                     \
    match = unicode_equals(name, qiskit_name);                                  \
    if (match < 0) {                                                            \
        goto error;                                                             \
    }                                                                           \
    if (match) {                                                                \
        canonical_text = canonical_gate;                                        \
        is_angle = angle_gate;                                                   \
        goto gate_matched;                                                      \
    }

    MATCH_GATE("id", "i", 0)
    MATCH_GATE("x", "x", 0)
    MATCH_GATE("y", "y", 0)
    MATCH_GATE("z", "z", 0)
    MATCH_GATE("h", "h", 0)
    MATCH_GATE("s", "s", 0)
    MATCH_GATE("t", "t", 0)
    MATCH_GATE("rx", "rx", 1)
    MATCH_GATE("ry", "ry", 1)
    MATCH_GATE("rz", "rz", 1)
    MATCH_GATE("p", "phaseshift", 1)

    self->supported = 0;
    goto unsupported;

gate_matched:
    params = PyObject_GetAttrString(operation, "params");
    if (params == NULL) {
        goto error;
    }
    parameter_count = PySequence_Size(params);
    if (parameter_count < 0) {
        goto error;
    }
    if ((!is_angle && parameter_count != 0) || (is_angle && parameter_count != 1)) {
        self->supported = 0;
        goto unsupported;
    }

    if (is_angle) {
        PyObject *parameter = PySequence_GetItem(params, 0);
        double angle;
        if (parameter == NULL) {
            goto error;
        }
        angle = PyFloat_AsDouble(parameter);
        Py_DECREF(parameter);
        if (angle == -1.0 && PyErr_Occurred()) {
            if (PyErr_ExceptionMatches(PyExc_TypeError) ||
                PyErr_ExceptionMatches(PyExc_ValueError)) {
                PyErr_Clear();
                self->supported = 0;
                goto unsupported;
            }
            goto error;
        }
        if (!isfinite(angle)) {
            self->supported = 0;
            goto unsupported;
        }
        angle_object = PyFloat_FromDouble(angle);
        if (angle_object == NULL) {
            goto error;
        }
    } else {
        angle_object = Py_NewRef(Py_None);
    }

    canonical_name = PyUnicode_FromString(canonical_text);
    if (canonical_name == NULL) {
        goto error;
    }
    record = PyTuple_Pack(2, canonical_name, angle_object);
    if (record == NULL || PyList_Append(self->records, record) < 0) {
        goto error;
    }

unsupported:
    Py_XDECREF(record);
    Py_XDECREF(canonical_name);
    Py_XDECREF(angle_object);
    Py_XDECREF(params);
    Py_XDECREF(num_clbits_object);
    Py_XDECREF(num_qubits_object);
    Py_XDECREF(name);
    Py_RETURN_NONE;

error:
    Py_XDECREF(record);
    Py_XDECREF(canonical_name);
    Py_XDECREF(angle_object);
    Py_XDECREF(params);
    Py_XDECREF(num_clbits_object);
    Py_XDECREF(num_qubits_object);
    Py_XDECREF(name);
    return NULL;
}

static void
collector_dealloc(PyObject *self_object)
{
    OperationCollector *self = (OperationCollector *)self_object;
    Py_XDECREF(self->records);
    Py_TYPE(self_object)->tp_free(self_object);
}

#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wmissing-field-initializers"
#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"
#endif
static PyTypeObject OperationCollectorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
};
#if defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#endif

static PyObject *
extract_1q_operations(PyObject *module, PyObject *circuit)
{
    PyObject *data = NULL;
    PyObject *foreach_op = NULL;
    PyObject *callback_result = NULL;
    OperationCollector *collector = NULL;
    PyObject *records = NULL;
    (void)module;

    data = PyObject_GetAttrString(circuit, "_data");
    if (data == NULL) {
        goto error;
    }
    foreach_op = PyObject_GetAttrString(data, "foreach_op");
    if (foreach_op == NULL || !PyCallable_Check(foreach_op)) {
        if (foreach_op != NULL) {
            PyErr_SetString(PyExc_TypeError, "CircuitData.foreach_op is not callable");
        }
        goto error;
    }

    collector = PyObject_New(OperationCollector, &OperationCollectorType);
    if (collector == NULL) {
        goto error;
    }
    collector->records = PyList_New(0);
    collector->supported = 1;
    if (collector->records == NULL) {
        goto error;
    }

    callback_result = PyObject_CallOneArg(foreach_op, (PyObject *)collector);
    if (callback_result == NULL) {
        goto error;
    }
    if (!collector->supported) {
        Py_DECREF(callback_result);
        Py_DECREF((PyObject *)collector);
        Py_DECREF(foreach_op);
        Py_DECREF(data);
        Py_RETURN_NONE;
    }

    records = Py_NewRef(collector->records);
    Py_DECREF(callback_result);
    Py_DECREF((PyObject *)collector);
    Py_DECREF(foreach_op);
    Py_DECREF(data);
    return records;

error:
    Py_XDECREF(callback_result);
    Py_XDECREF((PyObject *)collector);
    Py_XDECREF(foreach_op);
    Py_XDECREF(data);
    return NULL;
}

static PyObject *
build_1q_circuit(PyObject *module, PyObject *unitary_gate)
{
    PyObject *register_args = NULL;
    PyObject *quantum_register = NULL;
    PyObject *index = NULL;
    PyObject *qubit = NULL;
    PyObject *qubits = NULL;
    PyObject *empty = NULL;
    PyObject *instruction_args = NULL;
    PyObject *instruction = NULL;
    PyObject *reserve = NULL;
    PyObject *data_args = NULL;
    PyObject *data = NULL;
    PyObject *call_result = NULL;
    PyObject *constructor = NULL;
    PyObject *circuit = NULL;
    (void)module;

    register_args = Py_BuildValue("(is)", 1, "q");
    if (register_args == NULL) {
        goto error;
    }
    quantum_register = PyObject_CallObject(QuantumRegisterClass, register_args);
    if (quantum_register == NULL) {
        goto error;
    }
    index = PyLong_FromLong(0);
    if (index == NULL) {
        goto error;
    }
    qubit = PyObject_GetItem(quantum_register, index);
    if (qubit == NULL) {
        goto error;
    }
    qubits = PyTuple_Pack(1, qubit);
    empty = PyTuple_New(0);
    if (qubits == NULL || empty == NULL) {
        goto error;
    }
    instruction_args = PyTuple_Pack(3, unitary_gate, qubits, empty);
    if (instruction_args == NULL) {
        goto error;
    }
    instruction = PyObject_CallObject(CircuitInstructionClass, instruction_args);
    if (instruction == NULL) {
        goto error;
    }
    reserve = PyLong_FromLong(1);
    if (reserve == NULL) {
        goto error;
    }
    data_args = PyTuple_Pack(4, quantum_register, empty, Py_None, reserve);
    if (data_args == NULL) {
        goto error;
    }
    data = PyObject_CallObject(CircuitDataClass, data_args);
    if (data == NULL) {
        goto error;
    }
    call_result = PyObject_CallMethod(data, "add_qreg", "O", quantum_register);
    if (call_result == NULL) {
        goto error;
    }
    Py_CLEAR(call_result);
    call_result = PyObject_CallMethod(data, "append", "O", instruction);
    if (call_result == NULL) {
        goto error;
    }
    Py_CLEAR(call_result);
    constructor = PyObject_GetAttrString(QuantumCircuitClass, "_from_circuit_data");
    if (constructor == NULL) {
        goto error;
    }
    circuit = PyObject_CallOneArg(constructor, data);

error:
    Py_XDECREF(constructor);
    Py_XDECREF(call_result);
    Py_XDECREF(data);
    Py_XDECREF(data_args);
    Py_XDECREF(reserve);
    Py_XDECREF(instruction);
    Py_XDECREF(instruction_args);
    Py_XDECREF(empty);
    Py_XDECREF(qubits);
    Py_XDECREF(qubit);
    Py_XDECREF(index);
    Py_XDECREF(quantum_register);
    Py_XDECREF(register_args);
    return circuit;
}

static PyObject *
build_info(PyObject *module, PyObject *Py_UNUSED(ignored))
{
    PyObject *info = PyDict_New();
    PyObject *api_version = PyLong_FromLong(RQM_ADAPTER_NATIVE_API);
    PyObject *compiler = PyUnicode_FromString(Py_GetCompiler());
    PyObject *python = PyUnicode_FromString(Py_GetVersion());
    (void)module;
    if (info == NULL || api_version == NULL || compiler == NULL || python == NULL) {
        Py_XDECREF(python);
        Py_XDECREF(compiler);
        Py_XDECREF(api_version);
        Py_XDECREF(info);
        return NULL;
    }
    if (PyDict_SetItemString(info, "api_version", api_version) < 0 ||
        PyDict_SetItemString(info, "compiler", compiler) < 0 ||
        PyDict_SetItemString(info, "python", python) < 0) {
        Py_DECREF(python);
        Py_DECREF(compiler);
        Py_DECREF(api_version);
        Py_DECREF(info);
        return NULL;
    }
    Py_DECREF(python);
    Py_DECREF(compiler);
    Py_DECREF(api_version);
    return info;
}

static PyMethodDef module_methods[] = {
    {"extract_1q_operations", (PyCFunction)extract_1q_operations, METH_O,
     PyDoc_STR("Extract supported one-qubit operation records.")},
    {"build_1q_circuit", (PyCFunction)build_1q_circuit, METH_O,
     PyDoc_STR("Pack one fresh Qiskit circuit around a unitary gate.")},
    {"build_info", (PyCFunction)build_info, METH_NOARGS,
     PyDoc_STR("Return native adapter build provenance.")},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef module_definition = {
    PyModuleDef_HEAD_INIT,
    "_rqm_adapter_native",
    "Guarded native helpers for the RQM-Qiskit one-qubit adapter.",
    -1,
    module_methods,
    NULL,
    NULL,
    NULL,
    NULL,
};

static int
load_class(const char *module_name, const char *class_name, PyObject **target)
{
    PyObject *module = PyImport_ImportModule(module_name);
    if (module == NULL) {
        return -1;
    }
    *target = PyObject_GetAttrString(module, class_name);
    Py_DECREF(module);
    return *target == NULL ? -1 : 0;
}

PyMODINIT_FUNC
PyInit__rqm_adapter_native(void)
{
    PyObject *module;
    OperationCollectorType.tp_name =
        "rqm_qiskit._rqm_adapter_native._OperationCollector";
    OperationCollectorType.tp_basicsize = sizeof(OperationCollector);
    OperationCollectorType.tp_flags = Py_TPFLAGS_DEFAULT;
    OperationCollectorType.tp_call = collector_call;
    OperationCollectorType.tp_dealloc = collector_dealloc;
    if (PyType_Ready(&OperationCollectorType) < 0) {
        return NULL;
    }
    if (load_class("qiskit", "QuantumCircuit", &QuantumCircuitClass) < 0 ||
        load_class("qiskit.circuit", "QuantumRegister", &QuantumRegisterClass) < 0 ||
        load_class("qiskit.circuit", "CircuitInstruction", &CircuitInstructionClass) < 0 ||
        load_class("qiskit._accelerate.circuit", "CircuitData", &CircuitDataClass) < 0) {
        return NULL;
    }
    module = PyModule_Create(&module_definition);
    if (module == NULL) {
        return NULL;
    }
    return module;
}
