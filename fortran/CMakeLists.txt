cmake_minimum_required(VERSION 3.20)
project(drmrotor LANGUAGES Fortran)
set(CMAKE_Fortran_STANDARD 2018)
set(CMAKE_Fortran_STANDARD_REQUIRED ON)
find_package(BLAS REQUIRED)
find_package(LAPACK REQUIRED)

# ROSS-derived bearing library.  It remains a separate shared library from
# drmrotor and is consumed through its stable C ABI by the Python Core.
# The qualified legacy drmrotor bearing path is therefore left untouched.
add_library(drmbearings SHARED
 bearings/src/rb_kinds.f90
 bearings/src/rb_status.f90
 bearings/src/rb_interpolation.f90
 bearings/src/rb_rolling.f90
 bearings/src/rb_cylindrical.f90
 bearings/src/rb_squeeze_film_damper.f90
 bearings/src/rb_fixed_geometry.f90
 bearings/src/rb_tilting_pad_config.f90
 bearings/src/rb_reynolds_element.f90
 bearings/src/rb_reynolds_banded.f90
 bearings/src/rb_c_api.f90)
set_target_properties(drmbearings PROPERTIES OUTPUT_NAME drmbearings)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(drmbearings PRIVATE
  $<$<CONFIG:Debug>:-Wall -Wextra -Wimplicit-interface -ffree-line-length-none -fcheck=all -fbacktrace -ffpe-trap=invalid,zero,overflow>
  $<$<CONFIG:Release>:-O2 -ffree-line-length-none>)
endif()
add_library(drmrotor SHARED
 src/rd_kinds.f90 src/rd_status.f90 src/rd_lapack.f90
 src/rd_shaft_circular.f90 src/rd_shaft_tapered.f90 src/rd_shaft_asymmetric.f90
 src/rd_assembly_stationary.f90 src/rd_assembly_rotating.f90 src/rd_eigensystem.f90
 src/rd_frequency_response.f90 src/rd_external_response.f90 src/rd_critical_speed.f90
 src/rd_reduction.f90 src/rd_dp45.f90 src/rd_transient.f90
 src/rd_coaxial_solver.f90 src/rd_rotating_solver.f90 src/rd_c_api.f90)
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

add_executable(test_transient tests/test_transient.f90)
target_link_libraries(test_transient PRIVATE drmrotor)
add_test(NAME transient_dp45_reduction COMMAND test_transient)

add_executable(test_ross_bearings_native bearings/tests/test_rb_native.f90)
target_link_libraries(test_ross_bearings_native PRIVATE drmbearings)
add_test(NAME ross_bearings_native_bf1_bf2_bf3_bf4_bf5a_bf5band_bf5cfg_bf7 COMMAND test_ross_bearings_native)
