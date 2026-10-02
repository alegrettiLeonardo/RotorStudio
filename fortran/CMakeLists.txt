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
 bearings/src/rb_job_control.f90
 bearings/src/rb_interpolation.f90
 bearings/src/rb_rolling.f90
 bearings/src/rb_cylindrical.f90
 bearings/src/rb_squeeze_film_damper.f90
 bearings/src/rb_fixed_geometry.f90
 bearings/src/rb_tilting_pad_config.f90
 bearings/src/rb_dynamic_reduction.f90
 bearings/src/rb_reynolds_element.f90
 bearings/src/rb_reynolds_banded.f90
 bearings/src/rb_reynolds_mesh.f90
 bearings/src/rb_film_thickness.f90
 bearings/src/rb_pressure_isoviscous.f90
 bearings/src/rb_thermal.f90
 bearings/src/rb_pad_deformation.f90
 bearings/src/rb_native_multiphysics.f90
 bearings/src/rb_plain_journal_physics.f90
 bearings/src/rb_tilting_pad_physics.f90
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
 src/rd_frequency_response.f90 src/rd_external_response.f90 src/rd_critical_speed.f90 src/rd_intersections.f90 src/rd_rouch.f90 src/rd_ucs.f90 src/rd_ucs_c_api.f90 src/rd_level1.f90 src/rd_level1_c_api.f90 src/rd_api617_unbalance.f90 src/rd_api617_unbalance_c_api.f90 src/rd_clearance.f90 src/rd_clearance_c_api.f90
 src/rd_reduction.f90 src/rd_dp45.f90 src/rd_transient.f90
 src/rd_coaxial_solver.f90 src/rd_rotating_solver.f90 src/rd_dynamic_stiffness.f90 src/rd_frf_general.f90 src/rd_newmark.f90 src/rd_transient_stiffness.f90 src/rd_time_response_general.f90 src/rd_time_response_c_api.f90 src/rd_forced_response.f90 src/rd_forced_response_c_api.f90 src/rd_static.f90 src/rd_c_api.f90)
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
add_test(NAME ross_bearings_native_bf1_bf2_bf3_bf4_bf5a_bf5band_bf5mesh_bf5film_bf5press_bf5cond_bf5cfg_bf5plain_bf7 COMMAND test_ross_bearings_native)

add_executable(test_static tests/test_static.f90)
target_link_libraries(test_static PRIVATE drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_static PRIVATE -ffree-line-length-none)
endif()
add_test(NAME static_gravity_equilibrium COMMAND test_static)
add_executable(test_frf_general tests/test_frf_general.f90)
target_link_libraries(test_frf_general PRIVATE drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
  target_compile_options(test_frf_general PRIVATE -ffree-line-length-none)
endif()
add_test(NAME general_frf_dynamic_stiffness COMMAND test_frf_general)

add_executable(test_forced_response tests/test_forced_response.f90)
target_link_libraries(test_forced_response PRIVATE drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_forced_response PRIVATE -ffree-line-length-none)
endif()
add_test(NAME arbitrary_forced_response COMMAND test_forced_response)

add_executable(test_newmark tests/test_newmark.f90)
target_link_libraries(test_newmark PRIVATE drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_newmark PRIVATE -ffree-line-length-none)
endif()
add_test(NAME simple_newmark_analytic COMMAND test_newmark)

add_executable(time_probe tests/time_probe.f90)
target_link_libraries(time_probe PRIVATE drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(time_probe PRIVATE -ffree-line-length-none)
endif()


add_executable(test_ucs tests/test_ucs.f90)
target_link_libraries(test_ucs PRIVATE drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_ucs PRIVATE -ffree-line-length-none)
endif()
add_test(NAME ucs_native_contract COMMAND test_ucs)

add_executable(test_level1 tests/test_level1.f90)
target_link_libraries(test_level1 PRIVATE drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_level1 PRIVATE -ffree-line-length-none)
endif()
add_test(NAME level1_native_contract COMMAND test_level1)


add_executable(test_api617_unbalance tests/test_api617_unbalance.f90)
target_link_libraries(test_api617_unbalance PRIVATE drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_api617_unbalance PRIVATE -ffree-line-length-none)
endif()
add_test(NAME api617_unbalance_native_contract COMMAND test_api617_unbalance)


add_executable(test_clearance tests/test_clearance.f90)
target_link_libraries(test_clearance PRIVATE drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_clearance PRIVATE -ffree-line-length-none)
endif()
add_test(NAME api617_clearance_native_contract COMMAND test_clearance)

# B1 isolated 6-DOF element kernels. Existing A1-A8 dispatch is unchanged.
target_sources(drmrotor PRIVATE
 src/rd_shaft_6dof.f90
 src/rd_disk_6dof.f90
 src/rd_6dof_element_c_api.f90)
add_executable(test_6dof_elements tests/test_6dof_elements.f90)
target_link_libraries(test_6dof_elements PRIVATE drmrotor)
target_include_directories(test_6dof_elements PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_6dof_elements PRIVATE -ffree-line-length-none)
endif()
add_test(NAME sixdof_element_native_contract COMMAND test_6dof_elements)

# B2 additive global 6-DOF assembly/modal/Campbell kernels.
target_sources(drmrotor PRIVATE
 src/rd_6dof_assembly.f90
 src/rd_6dof_modal.f90
 src/rd_6dof_campbell.f90
 src/rd_6dof_global_c_api.f90)
add_executable(test_6dof_global tests/test_6dof_global.f90)
target_link_libraries(test_6dof_global PRIVATE drmrotor)
target_include_directories(test_6dof_global PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_6dof_global PRIVATE -ffree-line-length-none)
endif()
add_test(NAME sixdof_global_modal_campbell_native_contract COMMAND test_6dof_global)

# I4 iRdin flexible bearing-support element kernel.
# Additive diagnostic/qualification kernel only; existing A0-A8/B1 dispatch is unchanged.
target_sources(drmrotor PRIVATE
 src/rd_irdin_support.f90
 src/rd_irdin_support_c_api.f90)
add_executable(test_irdin_support tests/test_irdin_support.f90)
target_link_libraries(test_irdin_support PRIVATE drmrotor)
target_include_directories(test_irdin_support PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_irdin_support PRIVATE -ffree-line-length-none)
endif()
add_test(NAME irdin_support_element_contract COMMAND test_irdin_support)

# I8 global iRdin rotor-bearing-support matrix composition.
target_sources(drmrotor PRIVATE
 src/rd_irdin_support_global.f90
 src/rd_irdin_support_global_c_api.f90)
add_executable(test_irdin_support_global tests/test_irdin_support_global.f90)
target_link_libraries(test_irdin_support_global PRIVATE drmrotor)
target_include_directories(test_irdin_support_global PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_irdin_support_global PRIVATE -ffree-line-length-none)
endif()
add_test(NAME irdin_support_global_matrix_contract COMMAND test_irdin_support_global)

# I9 expanded iRdin modal and synchronous response solvers.
target_sources(drmrotor PRIVATE
 src/rd_irdin_support_analysis.f90
 src/rd_irdin_support_analysis_c_api.f90)
add_executable(test_irdin_support_analysis tests/test_irdin_support_analysis.f90)
target_link_libraries(test_irdin_support_analysis PRIVATE drmrotor)
target_include_directories(test_irdin_support_analysis PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_irdin_support_analysis PRIVATE -ffree-line-length-none)
endif()
add_test(NAME irdin_support_analysis_contract COMMAND test_irdin_support_analysis)
