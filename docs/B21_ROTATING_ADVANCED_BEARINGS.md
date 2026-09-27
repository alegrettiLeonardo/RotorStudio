# B21 — Rotating/Asymmetric Advanced Bearings

BASE_B20 = 086f7d0e64eebac4df0e8b32b099bfebe7472fbc
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

B21 qualifies the exact time-invariant subset of fixed-frame advanced bearings
for the rotating/asymmetric solver. Each evaluated 2x2 K/C/M must commute with
the planar rotation generator J. A general matrix that does not commute with J
becomes 2*Omega-periodic in rotating coordinates and is rejected with an
explicit Floquet/time-periodic diagnostic rather than averaged.

For q_s=R q_r the qualified bearing contributes M_b, C_b, 2 M_b J to the
Omega damping coefficient, K_b, C_b J to the Omega stiffness coefficient and
-M_b to the Omega^2 stiffness coefficient.

Additive bearing type 10 carries evaluated K/C/M. Historical rotating bearing
types 1-4 retain their V2 behavior, including the documented type-4 index defect
and nargout-dependent legacy K1b semantics. The B21 advanced K1 term is kept
separate so modal-with-vectors does not re-enable the legacy K1b branch.

Initial coefficient policy is synchronous: omega=Omega. Speed-dependent
advanced bearings are re-evaluated at each modal/FRF operating point.

B21_ROTATING_INVARIANT_ADVANCED_BEARINGS = PASS only after same-head
Linux/Windows qualification.
