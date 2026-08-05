from setuptools import Extension, setup


setup(
    ext_modules=[
        Extension(
            "rqm_qiskit._rqm_adapter_native",
            sources=["src/rqm_qiskit/_rqm_adapter_native.c"],
            optional=True,
        )
    ]
)
