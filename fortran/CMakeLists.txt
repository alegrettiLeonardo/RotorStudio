cmake_minimum_required(VERSION 3.20)
project(drmrotor LANGUAGES Fortran)
set(CMAKE_Fortran_STANDARD 2018)
set(CMAKE_Fortran_STANDARD_REQUIRED ON)
find_package(BLAS REQUIRED)
find_package(LAPACK REQUIRED)
add_library(drmrotor SHARED
 src/rd_kinds.f90 src/rd_status.f90 src/rd_lapack.f90
 src/rd_shaft_circular.f90 src/rd_shaft_tapered.f90 src/rd_shaft_asymmetric.f90
 src/rd_assembly_stationary.f90 src/rd_assembly_rotating.f90 src/rd_eigensystem.f90
 src/rd_frequency_response.f90 src/rd_critical_speed.f90 src/rd_coaxial_solver.f90 src/rd_rotating_solver.f90 src/rd_c_api.f90)
target_link_libraries(drmrotor PRIVATE LAPACK::LAPACK BLAS::BLAS)
set_target_properties(drmrotor PROPERTIES OUTPUT_NAME drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(drmrotor PRIVATE $<$<CONFIG:Debug>:-Wall -Wextra -Wimplicit-interface -ffree-line-length-none -fcheck=all -fbacktrace -ffpe-trap=invalid,zero,overflow> $<$<CONFIG:Release>:-O2 -ffree-line-length-none>)
endif()
enable_testing()
add_executable(test_shaft tests/test_shaft.f90)
target_link_libraries(test_shaft PRIVATE drmrotor)
add_test(NAME shaft_invariants COMMAND test_shaft)

add_executable(test_extended tests/test_extended.f90)
target_link_libraries(test_extended PRIVATE drmrotor)
add_test(NAME extended_shaft_equivalence COMMAND test_extended)

add_executable(test_bearings tests/test_bearings.f90)
target_link_libraries(test_bearings PRIVATE drmrotor)
add_test(NAME bearing_source_formulas COMMAND test_bearings)

add_executable(test_rotating tests/test_rotating.f90)
target_link_libraries(test_rotating PRIVATE drmrotor)
add_test(NAME rotating_legacy_compatibility COMMAND test_rotating)
