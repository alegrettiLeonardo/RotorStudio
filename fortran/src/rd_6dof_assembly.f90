! SPDX-License-Identifier: Apache-2.0
! B2 additive 6-DOF global assembly. Consumes the qualified B1 element kernels.
module rd_6dof_assembly
  use iso_c_binding, only: c_double,c_int
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_shaft_6dof, only: shaft_6dof_matrices,B1_OK
  use rd_disk_6dof, only: disk_6dof_matrices
  implicit none(type,external)
  private
  integer, parameter :: dp=c_double
  integer(c_int), parameter, public :: B2_OK=0, B2_INVALID_INPUT=20, B2_INVALID_DIMENSION=21
  integer(c_int), parameter, public :: B2_UNSUPPORTED=22, B2_SINGULAR=23, B2_LAPACK=24
  integer(c_int), parameter, public :: B2_INSUFFICIENT_CAPACITY=25, B2_NONFINITE=26, B2_ELEMENT_FAILURE=27
  public :: assemble_6dof
contains
  pure subroutine add_block(global,local,idx)
    real(dp),intent(inout)::global(:,:)
    real(dp),intent(in)::local(:,:)
    integer,intent(in)::idx(:)
    integer::i,j
    do j=1,size(idx)
      do i=1,size(idx)
        global(idx(i),idx(j))=global(idx(i),idx(j))+local(i,j)
      end do
    end do
  end subroutine

  subroutine assemble_6dof(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,bearing_par, &
                            M,K,C,G,Ksdt,status)
    integer(c_int),intent(in)::nn,ns,nd,nb
    integer(c_int),intent(in)::shaft_nodes(2,max(1,ns)),shaft_flags(4,max(1,ns))
    integer(c_int),intent(in)::disk_nodes(max(1,nd)),bearing_nodes(max(1,nb))
    real(dp),intent(in)::shaft_par(10,max(1,ns)),disk_par(3,max(1,nd)),bearing_par(12,max(1,nb))
    real(dp),intent(out)::M(6*nn,6*nn),K(6*nn,6*nn),C(6*nn,6*nn),G(6*nn,6*nn),Ksdt(6*nn,6*nn)
    integer(c_int),intent(out)::status
    real(dp)::Me(12,12),Ke(12,12),Ge(12,12),Se(12,12),Md(6,6),Gd(6,6),Sd(6,6)
    integer::e,i,j,n1,n2,node,idx12(12),idx6(6),ix,iy
    integer(c_int)::st
    M=0._dp;K=0._dp;C=0._dp;G=0._dp;Ksdt=0._dp;status=B2_INVALID_INPUT
    if(nn<2 .or. nn>100 .or. ns/=nn-1 .or. nd<0 .or. nb<0) return
    if(ns>0)then
      if(.not.all(ieee_is_finite(shaft_par(:,1:ns))))return
    end if
    if(nd>0)then
      if(.not.all(ieee_is_finite(disk_par(:,1:nd))))return
    end if
    if(nb>0)then
      if(.not.all(ieee_is_finite(bearing_par(:,1:nb))))return
    end if
    do e=1,ns
      n1=shaft_nodes(1,e);n2=shaft_nodes(2,e)
      if(n1/=e .or. n2/=e+1)return
      if(any(shaft_flags(:,e)<0_c_int))return
      do i=1,6
        idx12(i)=6*(n1-1)+i;idx12(6+i)=6*(n2-1)+i
      end do
      call shaft_6dof_matrices(shaft_par(1,e),shaft_par(2,e),shaft_par(3,e),shaft_par(4,e),shaft_par(5,e), &
        shaft_par(6,e),shaft_par(7,e),shaft_par(8,e),shaft_par(9,e),shaft_par(10,e), &
        shaft_flags(1,e),shaft_flags(2,e),shaft_flags(3,e),shaft_flags(4,e),Me,Ke,Ge,Se,st)
      if(st/=B1_OK)then;status=B2_ELEMENT_FAILURE;return;end if
      call add_block(M,Me,idx12);call add_block(K,Ke,idx12);call add_block(G,Ge,idx12);call add_block(Ksdt,Se,idx12)
    end do
    do e=1,nd
      node=disk_nodes(e);if(node<1.or.node>nn)return
      do i=1,6;idx6(i)=6*(node-1)+i;end do
      call disk_6dof_matrices(disk_par(1,e),disk_par(2,e),disk_par(3,e),Md,Gd,Sd,st)
      if(st/=B1_OK)then;status=B2_ELEMENT_FAILURE;return;end if
      call add_block(M,Md,idx6);call add_block(G,Gd,idx6);call add_block(Ksdt,Sd,idx6)
    end do
    do e=1,nb
      node=bearing_nodes(e);if(node<1.or.node>nn)return
      ix=6*(node-1)+1;iy=ix+1
      ! [Kxx,Kxy,Kyx,Kyy,Cxx,Cxy,Cyx,Cyy,Mxx,Mxy,Myx,Myy].
      K(ix,ix)=K(ix,ix)+bearing_par(1,e);K(ix,iy)=K(ix,iy)+bearing_par(2,e)
      K(iy,ix)=K(iy,ix)+bearing_par(3,e);K(iy,iy)=K(iy,iy)+bearing_par(4,e)
      C(ix,ix)=C(ix,ix)+bearing_par(5,e);C(ix,iy)=C(ix,iy)+bearing_par(6,e)
      C(iy,ix)=C(iy,ix)+bearing_par(7,e);C(iy,iy)=C(iy,iy)+bearing_par(8,e)
      M(ix,ix)=M(ix,ix)+bearing_par(9,e);M(ix,iy)=M(ix,iy)+bearing_par(10,e)
      M(iy,ix)=M(iy,ix)+bearing_par(11,e);M(iy,iy)=M(iy,iy)+bearing_par(12,e)
    end do
    if(.not.all(ieee_is_finite(M)).or..not.all(ieee_is_finite(K)).or..not.all(ieee_is_finite(C)).or. &
       .not.all(ieee_is_finite(G)).or..not.all(ieee_is_finite(Ksdt)))then
      status=B2_NONFINITE;return
    end if
    status=B2_OK
  end subroutine
end module rd_6dof_assembly
