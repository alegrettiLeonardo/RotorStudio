# I7 — native mass materialization

I7 converts only I1/I2-qualified, UMP-disabled iRdin mass spans into the
existing inertial-disk representation already consumed by the native Fortran
rotor assembly.

ST41 contains eight materialized slices: six package slices plus two single
mass records. Every slice center is inserted as an exact FE station before
`Disk.inertial` creation. Nearest-node projection is forbidden.

The frozen I2 inertia convention is preserved:
- `Ip = m/8 * (OD^2 + ID^2)`
- `Id = 0.5*Ip + m*L^2/12`

The distributed-mass blocker is removed only after all slices materialize.
ST41 remains globally blocked because I4 currently qualifies only the local
bearing/support matrix element; global rotor/support coupling is a later gate.
UMP-enabled legacy cases remain fail-closed.
