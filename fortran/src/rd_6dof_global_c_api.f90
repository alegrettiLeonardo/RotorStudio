! SPDX-License-Identifier: Apache-2.0
! B2 additive C ABI. Existing B1/A0-A8 symbols remain unchanged.
module rd_6dof_global_c_api
  use iso_c_binding, only: c_double,c_double_complex,c_int,c_int64_t
  use rd_6dof_assembly, only: assemble_6dof,B2_OK,B2_INVALID_INPUT,B2_INVALID_DIMENSION,B2_INSUFFICIENT_CAPACITY
  use rd_6dof_modal, only: modal_from_matrices,build_state_space
  use rd_6dof_campbell, only: campbell_6dof
  implicit none(type,external)
  private
  public :: rd_6dof_global_required_v1,rd_6dof_global_matrices_v1
  public :: rd_6dof_modal_required_v1,rd_6dof_modal_v1
  public :: rd_6dof_campbell_required_v1,rd_6dof_campbell_v1,rd_6dof_campbell_v2
contains
  integer(c_int) function rd_6dof_global_required_v1(nn,ndof,matrix_values) bind(C,name='rd_6dof_global_required_v1')
    integer(c_int),value::nn
    integer(c_int),intent(out)::ndof,matrix_values
    rd_6dof_global_required_v1=B2_INVALID_INPUT;ndof=0;matrix_values=0
    if(nn<2.or.nn>100)return
    ndof=6*nn;matrix_values=ndof*ndof;rd_6dof_global_required_v1=B2_OK
  end function

  subroutine unpack_model(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar,shaft_nodes,shaft_par,shaft_flags,disk_nodes,disk_par,bearing_nodes,bearing_par)
    integer(c_int),intent(in)::nn,ns,nd,nb,snodes(2,*),sflags(4,*),dnodes(*),bnodes(*)
    real(c_double),intent(in)::spar(10,*),dpar(3,*),bpar(12,*)
    integer(c_int),allocatable,intent(out)::shaft_nodes(:,:),shaft_flags(:,:),disk_nodes(:),bearing_nodes(:)
    real(c_double),allocatable,intent(out)::shaft_par(:,:),disk_par(:,:),bearing_par(:,:)
    integer::i,j
    allocate(shaft_nodes(2,max(1,ns)),shaft_flags(4,max(1,ns)),shaft_par(10,max(1,ns)))
    allocate(disk_nodes(max(1,nd)),disk_par(3,max(1,nd)),bearing_nodes(max(1,nb)),bearing_par(12,max(1,nb)))
    shaft_nodes=0;shaft_flags=0;shaft_par=0;disk_nodes=0;disk_par=0;bearing_nodes=0;bearing_par=0
    do j=1,ns;do i=1,2;shaft_nodes(i,j)=snodes(i,j);end do;do i=1,4;shaft_flags(i,j)=sflags(i,j);end do;do i=1,10;shaft_par(i,j)=spar(i,j);end do;end do
    do j=1,nd;disk_nodes(j)=dnodes(j);do i=1,3;disk_par(i,j)=dpar(i,j);end do;end do
    do j=1,nb;bearing_nodes(j)=bnodes(j);do i=1,12;bearing_par(i,j)=bpar(i,j);end do;end do
  end subroutine

  subroutine copy_real_matrix(A,b,ld,n)
    integer(c_int),intent(in)::ld,n
    real(c_double),intent(in)::A(n,n)
    real(c_double),intent(inout)::b(*)
    integer::i,j
    do j=1,n;do i=1,n;b((j-1)*ld+i)=A(i,j);end do;end do
  end subroutine

  logical function layout_ok(n,ld,cap)
    integer(c_int),intent(in)::n,ld,cap
    integer(c_int64_t)::need
    layout_ok=.false.;if(ld<n)return
    need=int(n-1,c_int64_t)*int(ld,c_int64_t)+int(n,c_int64_t)
    if(int(cap,c_int64_t)<need)return
    layout_ok=.true.
  end function

  integer(c_int) function rd_6dof_global_matrices_v1(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar, &
      bm,ldm,capm,bk,ldk,capk,bc,ldc,capc,bg,ldg,capg,bs,lds,caps) bind(C,name='rd_6dof_global_matrices_v1')
    integer(c_int),value::nn,ns,nd,nb,ldm,capm,ldk,capk,ldc,capc,ldg,capg,lds,caps
    integer(c_int),intent(in)::snodes(2,*),sflags(4,*),dnodes(*),bnodes(*)
    real(c_double),intent(in)::spar(10,*),dpar(3,*),bpar(12,*)
    real(c_double),intent(inout)::bm(*),bk(*),bc(*),bg(*),bs(*)
    integer(c_int),allocatable::shaft_nodes(:,:),shaft_flags(:,:),disk_nodes(:),bearing_nodes(:)
    real(c_double),allocatable::shaft_par(:,:),disk_par(:,:),bearing_par(:,:),M(:,:),K(:,:),C(:,:),G(:,:),S(:,:)
    integer(c_int)::st
    integer::n
    rd_6dof_global_matrices_v1=B2_INVALID_INPUT
    if(nn<2.or.nn>100.or.ns/=nn-1.or.nd<0.or.nb<0)return
    n=6*nn
    if(.not.layout_ok(n,ldm,capm).or..not.layout_ok(n,ldk,capk).or..not.layout_ok(n,ldc,capc).or. &
       .not.layout_ok(n,ldg,capg).or..not.layout_ok(n,lds,caps))then
      rd_6dof_global_matrices_v1=B2_INSUFFICIENT_CAPACITY;return
    end if
    call unpack_model(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar,shaft_nodes,shaft_par,shaft_flags,disk_nodes,disk_par,bearing_nodes,bearing_par)
    allocate(M(n,n),K(n,n),C(n,n),G(n,n),S(n,n))
    call assemble_6dof(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,bearing_par,M,K,C,G,S,st)
    if(st/=B2_OK)then;rd_6dof_global_matrices_v1=st;return;end if
    call copy_real_matrix(M,bm,ldm,int(n,c_int));call copy_real_matrix(K,bk,ldk,int(n,c_int))
    call copy_real_matrix(C,bc,ldc,int(n,c_int));call copy_real_matrix(G,bg,ldg,int(n,c_int));call copy_real_matrix(S,bs,lds,int(n,c_int))
    rd_6dof_global_matrices_v1=B2_OK
  end function

  integer(c_int) function rd_6dof_modal_required_v1(nn,num_modes,ndof,state_dim,max_retained,selected,q_values,a_values) bind(C,name='rd_6dof_modal_required_v1')
    integer(c_int),value::nn,num_modes
    integer(c_int),intent(out)::ndof,state_dim,max_retained,selected,q_values,a_values
    rd_6dof_modal_required_v1=B2_INVALID_INPUT;ndof=0;state_dim=0;max_retained=0;selected=0;q_values=0;a_values=0
    if(nn<2.or.nn>100.or.num_modes<2.or.mod(num_modes,2)/=0)return
    ndof=6*nn;state_dim=2*ndof;max_retained=state_dim;selected=min(num_modes/2,max_retained)
    q_values=ndof*selected;a_values=state_dim*state_dim;rd_6dof_modal_required_v1=B2_OK
  end function

  integer(c_int) function rd_6dof_modal_v1(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar,speed,num_modes, &
      capall,capsel,qld,qcap,alda,acap,nret,nsel,rcond,allr,alli,er,ei,wn,wd,zeta,logdec,whirl,residual,mtype,qr,qi,aout) &
      bind(C,name='rd_6dof_modal_v1')
    integer(c_int),value::nn,ns,nd,nb,num_modes,capall,capsel,qld,qcap,alda,acap
    integer(c_int),intent(in)::snodes(2,*),sflags(4,*),dnodes(*),bnodes(*)
    real(c_double),intent(in)::spar(10,*),dpar(3,*),bpar(12,*)
    real(c_double),value::speed
    integer(c_int),intent(out)::nret,nsel,mtype(*)
    real(c_double),intent(out)::rcond
    real(c_double),intent(inout)::allr(*),alli(*),er(*),ei(*),wn(*),wd(*),zeta(*),logdec(*),whirl(*),residual(*),qr(*),qi(*),aout(*)
    integer(c_int),allocatable::shaft_nodes(:,:),shaft_flags(:,:),disk_nodes(:),bearing_nodes(:),types(:)
    real(c_double),allocatable::shaft_par(:,:),disk_par(:,:),bearing_par(:,:),M(:,:),K(:,:),C(:,:),G(:,:),S(:,:),A(:,:)
    real(c_double),allocatable::wna(:),wda(:),za(:),lda(:),wa(:),ra(:)
    complex(c_double_complex),allocatable::eall(:),Vall(:,:),evals(:),qvec(:,:)
    integer(c_int)::st
    integer::n,state,i,j
    rd_6dof_modal_v1=B2_INVALID_INPUT;nret=0;nsel=0;rcond=0
    if(nn<2.or.nn>100.or.ns/=nn-1)return;n=6*nn;state=2*n
    if(capall<state.or.capsel<num_modes/2.or.qld<n.or.qcap<qld*(num_modes/2).or.alda<state.or.acap<alda*state)then
      rd_6dof_modal_v1=B2_INSUFFICIENT_CAPACITY;return
    end if
    call unpack_model(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar,shaft_nodes,shaft_par,shaft_flags,disk_nodes,disk_par,bearing_nodes,bearing_par)
    allocate(M(n,n),K(n,n),C(n,n),G(n,n),S(n,n),A(state,state))
    call assemble_6dof(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,bearing_par,M,K,C,G,S,st)
    if(st/=B2_OK)then;rd_6dof_modal_v1=st;return;end if
    call build_state_space(M,K,C,G,speed,A,rcond,st);if(st/=B2_OK)then;rd_6dof_modal_v1=st;return;end if
    call modal_from_matrices(M,K,C,G,speed,num_modes,eall,Vall,nret,evals,qvec,wna,wda,za,lda,types,wa,ra,nsel,rcond,st)
    if(st/=B2_OK)then;rd_6dof_modal_v1=st;return;end if
    if(nret>capall.or.nsel>capsel.or.qcap<qld*nsel)then;rd_6dof_modal_v1=B2_INSUFFICIENT_CAPACITY;return;end if
    do i=1,nret;allr(i)=real(eall(i),c_double);alli(i)=aimag(eall(i));end do
    do j=1,nsel
      er(j)=real(evals(j),c_double);ei(j)=aimag(evals(j));wn(j)=wna(j);wd(j)=wda(j);zeta(j)=za(j);logdec(j)=lda(j)
      whirl(j)=wa(j);residual(j)=ra(j);mtype(j)=types(j)
      do i=1,n;qr((j-1)*qld+i)=real(qvec(i,j),c_double);qi((j-1)*qld+i)=aimag(qvec(i,j));end do
    end do
    call copy_real_matrix(A,aout,alda,int(state,c_int))
    rd_6dof_modal_v1=B2_OK
  end function

  integer(c_int) function rd_6dof_campbell_required_v1(nn,nsp,frequencies,branch_values,track_values,mac_values) bind(C,name='rd_6dof_campbell_required_v1')
    integer(c_int),value::nn,nsp,frequencies
    integer(c_int),intent(out)::branch_values,track_values,mac_values
    integer::nt
    rd_6dof_campbell_required_v1=B2_INVALID_INPUT;branch_values=0;track_values=0;mac_values=0
    if(nn<2.or.nn>100.or.nsp<2.or.frequencies<1.or.frequencies+2>6*nn)return
    nt=frequencies+2;branch_values=frequencies*nsp;track_values=nt*nsp;mac_values=nt*nt*nsp
    rd_6dof_campbell_required_v1=B2_OK
  end function

  integer(c_int) function rd_6dof_campbell_v1(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,nsp,speeds,bmap,frequencies, &
      branch_cap,track_cap,mac_cap,wd,wn,zeta,logdec,whirl,mtype,track_index,track_mac,macs) bind(C,name='rd_6dof_campbell_v1')
    integer(c_int),value::nn,ns,nd,nb,nsp,frequencies,branch_cap,track_cap,mac_cap
    integer(c_int),intent(in)::snodes(2,*),sflags(4,*),dnodes(*),bnodes(*)
    real(c_double),intent(in)::spar(10,*),dpar(3,*),speeds(*),bmap(*)
    real(c_double),intent(inout)::wd(*),wn(*),zeta(*),logdec(*),whirl(*),track_mac(*),macs(*)
    integer(c_int),intent(inout)::mtype(*),track_index(*)
    integer(c_int),allocatable::shaft_nodes(:,:),shaft_flags(:,:),disk_nodes(:),bearing_nodes(:),types(:,:),tidx(:,:)
    real(c_double),allocatable::shaft_par(:,:),disk_par(:,:),bearing_dummy_in(:,:),bearing_dummy_out(:,:),map3(:,:,:),wdo(:,:),wno(:,:),zo(:,:),lo(:,:),wo(:,:),tm(:,:),mm(:,:,:)
    integer(c_int)::st
    integer::i,j,k,p,nt
    rd_6dof_campbell_v1=B2_INVALID_INPUT
    if(nn<2.or.ns/=nn-1.or.nsp<2.or.frequencies<1)return;nt=frequencies+2
    if(branch_cap<frequencies*nsp.or.track_cap<nt*nsp.or.mac_cap<nt*nt*nsp)then;rd_6dof_campbell_v1=B2_INSUFFICIENT_CAPACITY;return;end if
    allocate(bearing_dummy_in(12,max(1,nb)),bearing_dummy_out(12,max(1,nb)));bearing_dummy_in=0
    call unpack_model(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bearing_dummy_in,shaft_nodes,shaft_par,shaft_flags,disk_nodes,disk_par,bearing_nodes,bearing_dummy_out)
    allocate(map3(12,max(1,nb),nsp));map3=0;p=0
    do k=1,nsp;do j=1,nb;do i=1,12;p=p+1;map3(i,j,k)=bmap(p);end do;end do;end do
    allocate(wdo(frequencies,nsp),wno(frequencies,nsp),zo(frequencies,nsp),lo(frequencies,nsp),wo(frequencies,nsp),types(frequencies,nsp), &
             tidx(nt,nsp),tm(nt,nsp),mm(nt,nt,nsp))
    call campbell_6dof(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,nsp,speeds(1:nsp),map3,frequencies, &
                       wdo,wno,zo,lo,wo,types,tidx,tm,mm,st)
    if(st/=B2_OK)then;rd_6dof_campbell_v1=st;return;end if
    p=0;do k=1,nsp;do i=1,frequencies;p=p+1;wd(p)=wdo(i,k);wn(p)=wno(i,k);zeta(p)=zo(i,k);logdec(p)=lo(i,k);whirl(p)=wo(i,k);mtype(p)=types(i,k);end do;end do
    p=0;do k=1,nsp;do i=1,nt;p=p+1;track_index(p)=tidx(i,k);track_mac(p)=tm(i,k);end do;end do
    p=0;do k=1,nsp;do j=1,nt;do i=1,nt;p=p+1;macs(p)=mm(i,j,k);end do;end do;end do
    rd_6dof_campbell_v1=B2_OK
  end function

  integer(c_int) function rd_6dof_campbell_v2(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,nsp,speeds,bmap,frequencies,frequency_type, &
      branch_cap,track_cap,mac_cap,wd,wn,zeta,logdec,whirl,mtype,track_index,track_mac,macs) bind(C,name='rd_6dof_campbell_v2')
    integer(c_int),value::nn,ns,nd,nb,nsp,frequencies,frequency_type,branch_cap,track_cap,mac_cap
    integer(c_int),intent(in)::snodes(2,*),sflags(4,*),dnodes(*),bnodes(*)
    real(c_double),intent(in)::spar(10,*),dpar(3,*),speeds(*),bmap(*)
    real(c_double),intent(inout)::wd(*),wn(*),zeta(*),logdec(*),whirl(*),track_mac(*),macs(*)
    integer(c_int),intent(inout)::mtype(*),track_index(*)
    integer(c_int),allocatable::shaft_nodes(:,:),shaft_flags(:,:),disk_nodes(:),bearing_nodes(:),types(:,:),tidx(:,:)
    real(c_double),allocatable::shaft_par(:,:),disk_par(:,:),bearing_dummy_in(:,:),bearing_dummy_out(:,:),map3(:,:,:),wdo(:,:),wno(:,:),zo(:,:),lo(:,:),wo(:,:),tm(:,:),mm(:,:,:)
    integer(c_int)::st
    integer::i,j,k,p,nt
    rd_6dof_campbell_v2=B2_INVALID_INPUT
    if(nn<2.or.ns/=nn-1.or.nsp<2.or.frequencies<1.or.(frequency_type/=0.and.frequency_type/=1))return
    nt=frequencies+2
    if(branch_cap<frequencies*nsp.or.track_cap<nt*nsp.or.mac_cap<nt*nt*nsp)then
      rd_6dof_campbell_v2=B2_INSUFFICIENT_CAPACITY;return
    end if
    allocate(bearing_dummy_in(12,max(1,nb)),bearing_dummy_out(12,max(1,nb)));bearing_dummy_in=0
    call unpack_model(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bearing_dummy_in,shaft_nodes,shaft_par,shaft_flags,disk_nodes,disk_par,bearing_nodes,bearing_dummy_out)
    allocate(map3(12,max(1,nb),nsp));map3=0;p=0
    do k=1,nsp;do j=1,nb;do i=1,12;p=p+1;map3(i,j,k)=bmap(p);end do;end do;end do
    allocate(wdo(frequencies,nsp),wno(frequencies,nsp),zo(frequencies,nsp),lo(frequencies,nsp),wo(frequencies,nsp),types(frequencies,nsp), &
             tidx(nt,nsp),tm(nt,nsp),mm(nt,nt,nsp))
    call campbell_6dof(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,nsp,speeds(1:nsp),map3,frequencies, &
                       wdo,wno,zo,lo,wo,types,tidx,tm,mm,st,frequency_type)
    if(st/=B2_OK)then;rd_6dof_campbell_v2=st;return;end if
    p=0;do k=1,nsp;do i=1,frequencies;p=p+1;wd(p)=wdo(i,k);wn(p)=wno(i,k);zeta(p)=zo(i,k);logdec(p)=lo(i,k);whirl(p)=wo(i,k);mtype(p)=types(i,k);end do;end do
    p=0;do k=1,nsp;do i=1,nt;p=p+1;track_index(p)=tidx(i,k);track_mac(p)=tm(i,k);end do;end do
    p=0;do k=1,nsp;do j=1,nt;do i=1,nt;p=p+1;macs(p)=mm(i,j,k);end do;end do;end do
    rd_6dof_campbell_v2=B2_OK
  end function
end module rd_6dof_global_c_api
