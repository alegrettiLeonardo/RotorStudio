cmake_minimum_required(VERSION 3.20)
project(drmrotor LANGUAGES Fortran)
set(CMAKE_Fortran_STANDARD 2018)
set(CMAKE_Fortran_STANDARD_REQUIRED ON)
find_package(BLAS REQUIRED)
find_package(LAPACK REQUIRED)
add_library(drmrotor SHARED
 src/rd_kinds.f90
 src/rd_status.f90
 src/rd_lapack.f90
 src/rd_shaft_circular.f90
 src/rd_shaft_tapered.f90
 src/rd_shaft_asymmetric.f90
 src/rd_bearings.f90
 src/rd_assembly_stationary.f90
 src/rd_eigensystem.f90
 src/rd_frequency_response.f90
 src/rd_critical_speed.f90
 src/rd_c_api.f90)
target_link_libraries(drmrotor PRIVATE LAPACK::LAPACK BLAS::BLAS)
set_target_properties(drmrotor PROPERTIES OUTPUT_NAME drmrotor)
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(drmrotor PRIVATE
   $<$<CONFIG:Debug>:-Wall -Wextra -Wimplicit-interface -fcheck=all -fbacktrace -ffpe-trap=invalid,zero,overflow>
   $<$<CONFIG:Release>:-O2>)
endif()
enable_testing()
foreach(t shaft taper asymmetric bearings assembly analysis)
  add_executable(test_${t} tests/test_${t}.f90)
  target_link_libraries(test_${t} PRIVATE drmrotor)
  add_test(NAME ${t} COMMAND test_${t})
endforeach()
