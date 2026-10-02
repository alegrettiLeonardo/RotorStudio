! SPDX-License-Identifier: Apache-2.0
! B3 additive C ABI for dedicated axial/torsional modal workflows.
module rd_axial_torsional_c_api
  use iso_c_binding, only: c_double,c_int,c_int64_t
  use rd_6dof_assembly, only: assemble_6dof,B2_OK
  use rd_axial_torsional, only: family_modal_from_global,B3_OK,B3_INVALID_INPUT
  implicit none(type,external)
  private
  public::rd_axial_torsional_required_v1,rd_axial_torsional_modal_v1
contains

  integer(c_int) function rd_axial_torsional_required_v1(nn,max_modes,matrix_values,vector_values) &
      bind(C,name='rd_axial_torsional_required_v1')
    integer(c_int),value::nn
    integer(c_int),intent(out)::max_modes,matrix_values,vector_values
    rd_axial_torsional_required_v1=B3_INVALID_INPUT
    max_modes=0;matrix_values=0;vector_values=0
    if(nn<2.or.nn>100)return
    max_modes=nn-1;matrix_values=nn*nn;vector_values=nn*max_modes
    rd_axial_torsional_required_v1=B3_OK
  end function

  subroutine unpack_model(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar, &
      shaft_nodes,shaft_par,shaft_flags,disk_nodes,disk_par,bearing_nodes,bearing_par)
    integer(c_int),intent(in)::nn,ns,nd,nb,snodes(2,*),sflags(4,*),dnodes(*),bnodes(*)
    real(c_double),intent(in)::spar(10,*),dpar(3,*),bpar(12,*)
    integer(c_int),allocatable,intent(out)::shaft_nodes(:,:),shaft_flags(:,:),disk_nodes(:),bearing_nodes(:)
    real(c_double),allocatable,intent(out)::shaft_par(:,:),disk_par(:,:),bearing_par(:,:)
    integer::i,j
    allocate(shaft_nodes(2,max(1,ns)),shaft_flags(4,max(1,ns)),shaft_par(10,max(1,ns)))
    allocate(disk_nodes(max(1,nd)),disk_par(3,max(1,nd)),bearing_nodes(max(1,nb)),bearing_par(12,max(1,nb)))
    shaft_nodes=0;shaft_flags=0;shaft_par=0;disk_nodes=0;disk_par=0;bearing_nodes=0;bearing_par=0
    do j=1,ns
      do i=1,2;shaft_nodes(i,j)=snodes(i,j);end do
      do i=1,4;shaft_flags(i,j)=sflags(i,j);end do
      do i=1,10;shaft_par(i,j)=spar(i,j);end do
    end do
    do j=1,nd
      disk_nodes(j)=dnodes(j)
      do i=1,3;disk_par(i,j)=dpar(i,j);end do
    end do
    do j=1,nb
      bearing_nodes(j)=bnodes(j)
      do i=1,12;bearing_par(i,j)=bpar(i,j);end do
    end do
  end subroutine

  subroutine copy_matrix(A,b,ld,n)
    integer(c_int),intent(in)::ld,n
    real(c_double),intent(in)::A(n,n)
    real(c_double),intent(inout)::b(*)
    integer::i,j
    do j=1,n;do i=1,n;b((j-1)*ld+i)=A(i,j);end do;end do
  end subroutine

  logical function layout_ok(n,ld,cap)
    integer(c_int),intent(in)::n,ld,cap
    integer(c_int64_t)::need
    layout_ok=.false.
    if(ld<n)return
    need=int(n-1,c_int64_t)*int(ld,c_int64_t)+int(n,c_int64_t)
    if(int(cap,c_int64_t)<need)return
    layout_ok=.true.
  end function

  integer(c_int) function rd_axial_torsional_modal_v1(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar, &
      family,speed,mode_cap,qld,qcap,mld,mcap,nmode,max_decouple,wn,wd,zeta,logdec,residual,qout, &
      mout,kout,cout,gout,sout) bind(C,name='rd_axial_torsional_modal_v1')
    integer(c_int),value::nn,ns,nd,nb,family,mode_cap,qld,qcap,mld,mcap
    integer(c_int),intent(in)::snodes(2,*),sflags(4,*),dnodes(*),bnodes(*)
    real(c_double),intent(in)::spar(10,*),dpar(3,*),bpar(12,*)
    real(c_double),value::speed
    integer(c_int),intent(out)::nmode
    real(c_double),intent(out)::max_decouple
    real(c_double),intent(inout)::wn(*),wd(*),zeta(*),logdec(*),residual(*),qout(*)
    real(c_double),intent(inout)::mout(*),kout(*),cout(*),gout(*),sout(*)
    integer(c_int),allocatable::shaft_nodes(:,:),shaft_flags(:,:),disk_nodes(:),bearing_nodes(:)
    real(c_double),allocatable::shaft_par(:,:),disk_par(:,:),bearing_par(:,:)
    real(c_double),allocatable::M6(:,:),K6(:,:),C6(:,:),G6(:,:),S6(:,:)
    real(c_double),allocatable::M(:,:),K(:,:),C(:,:),G(:,:),S(:,:),wna(:),wda(:),za(:),lda(:),ra(:),q(:,:)
    integer(c_int)::st
    integer::n6,maxm,i,j
    rd_axial_torsional_modal_v1=B3_INVALID_INPUT;nmode=0;max_decouple=0._c_double
    if(nn<2.or.nn>100.or.ns/=nn-1.or.nd<0.or.nb<0)return
    if(family/=1_c_int.and.family/=2_c_int)return
    maxm=nn-1
    if(mode_cap<maxm.or.qld<nn.or.qcap<qld*maxm)return
    if(.not.layout_ok(nn,mld,mcap))return

    call unpack_model(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar, &
      shaft_nodes,shaft_par,shaft_flags,disk_nodes,disk_par,bearing_nodes,bearing_par)
    n6=6*nn
    allocate(M6(n6,n6),K6(n6,n6),C6(n6,n6),G6(n6,n6),S6(n6,n6))
    call assemble_6dof(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,bearing_par, &
      M6,K6,C6,G6,S6,st)
    if(st/=B2_OK)then;rd_axial_torsional_modal_v1=st;return;end if

    allocate(M(nn,nn),K(nn,nn),C(nn,nn),G(nn,nn),S(nn,nn))
    allocate(wna(maxm),wda(maxm),za(maxm),lda(maxm),ra(maxm),q(nn,maxm))
    call family_modal_from_global(nn,family,speed,M6,K6,C6,G6,S6,M,K,C,G,S, &
      wna,wda,za,lda,q,ra,max_decouple,nmode,st)
    if(st/=B3_OK)then;rd_axial_torsional_modal_v1=st;return;end if
    if(nmode>mode_cap.or.qcap<qld*nmode)then;rd_axial_torsional_modal_v1=B3_INVALID_INPUT;return;end if
    do j=1,nmode
      wn(j)=wna(j);wd(j)=wda(j);zeta(j)=za(j);logdec(j)=lda(j);residual(j)=ra(j)
      do i=1,nn;qout((j-1)*qld+i)=q(i,j);end do
    end do
    call copy_matrix(M,mout,mld,nn);call copy_matrix(K,kout,mld,nn)
    call copy_matrix(C,cout,mld,nn);call copy_matrix(G,gout,mld,nn);call copy_matrix(S,sout,mld,nn)
    rd_axial_torsional_modal_v1=B3_OK
  end function
end module rd_axial_torsional_c_api
