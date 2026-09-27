# ROSS analysis reference attribution

ROSS — Rotordynamic Open Source Software, developed by ROSS developers.
Source: https://github.com/petrobras/ross
Frozen commit: 6320eab9f890f1b3cc1710d508b446fe063ca68d
License: Apache License, Version 2.0; full text in ROSS_LICENSE.txt.

PR-A0 invokes frozen ROSS public methods to generate validation references.
It does not contain a port of ROSS numerical solver equations. Fixture
rotor_example is supplied by ROSS; additional fixtures change input entities
and call the same authority. Generated references identify source and methods.

For later Fortran ports, add method-level provenance and modified-file notices.
Do not imply endorsement by Petrobras or the ROSS developers.
