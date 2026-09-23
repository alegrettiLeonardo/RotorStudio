# Commands executed — M6

- `command -v matlab` -> not found
- `command -v octave` -> not found
- `apt-get update -qq` -> timed out after 45 s
- Release CMake/build/CTest -> 5/5 PASS
- Debug CMake/build/CTest -> 5/5 PASS
- `pytest python/tests` -> 51/51 PASS
- 22-example campaign -> 33/33 PASS, 22 unique examples
- `run_authority.sh` -> BLOCKED (no MATLAB/Octave)
- formal comparator with missing authority -> BLOCKED, exit 2
- comparator self-check with synthetic current-solver baseline -> PASS, explicitly SELF_CHECK_NOT_AUTHORITY
- exact M6 ZIP clean test -> manifest PASS, rebuild PASS, 5/5 CTest, 51/51 pytest, 33/33 campaign, formal status BLOCKED as expected
