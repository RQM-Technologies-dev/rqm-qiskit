OPENQASM 3.0;
include "stdgates.inc";
bit[1] result;
qubit[1] q;
rz(0.37) q[0];
ry(-0.81) q[0];
rz(1.13) q[0];
result[0] = measure q[0];

