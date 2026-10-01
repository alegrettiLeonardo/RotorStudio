program test_6dof_global
  use iso_c_binding, only: c_double,c_int
  use rd_shaft_6dof, only: shaft_6dof_matrices,B1_OK
  use rd_6dof_assembly, only: assemble_6dof,B2_OK,B2_INVALID_INPUT
  use rd_6dof_modal, only: modal_from_matrices
  use rd_6dof_campbell, only: campbell_6dof
  implicit none
  integer,parameter::dp=c_double
  integer(c_int),parameter::nn=3,ns=2,nd=1,nb=2
  integer(c_int)::sn(2,ns),sf(4,ns),dn(nd),bn(nb),status,nret,nsel
  real(dp)::sp(10,ns),dd(3,nd),bp(12,nb),M(18,18),K(18,18),C(18,18),G(18,18),S(18,18)
  real(dp)::Me(12,12),Ke(12,12),Ge(12,12),Se(12,12),rcond
  complex(dp),allocatable::eall(:),Vall(:,:),evals(:),qvec(:,:)
  real(dp),allocatable::wn(:),wd(:),zeta(:),logdec(:),whirl(:),residual(:)
  integer(c_int),allocatable::mtype(:)
  real(dp)::speeds(3),bmap(12,nb,3),c_wd(2,3),c_wn(2,3),c_zeta(2,3),c_log(2,3),c_whirl(2,3)
  integer(c_int)::c_type(2,3),track_idx(4,3)
  real(dp)::track_mac(4,3),macs(4,4,3)
  integer::i,j,k
  sn=reshape([1_c_int,2_c_int,2_c_int,3_c_int],[2,2])
  sf=1;sf(4,:)=1
  sp=0
  do j=1,ns
    sp(:,j)=[0.22_dp,0._dp,0.05_dp,0._dp,0.05_dp,7810._dp,211e9_dp,81.2e9_dp,0._dp,0._dp]
  end do
  dn=[2_c_int];dd(:,1)=[12._dp,0.04_dp,0.08_dp]
  bn=[1_c_int,3_c_int];bp=0
  do j=1,nb
    bp(1,j)=1e6_dp;bp(4,j)=1e6_dp;bp(5,j)=1e3_dp;bp(8,j)=1e3_dp
  end do
  call assemble_6dof(nn,ns,sn,sp,sf,nd,dn,dd,nb,bn,bp,M,K,C,G,S,status)
  call check(status==B2_OK,'global assembly status')
  call check(maxval(abs(M-transpose(M)))<1e-10_dp,'M symmetry')
  call check(maxval(abs(G+transpose(G)))<1e-10_dp,'G skew symmetry')
  call check(abs(C(1,1)-1e3_dp)<1e-12_dp.and.abs(C(2,2)-1e3_dp)<1e-12_dp,'bearing radial C insertion')
  call check(C(3,3)==0._dp.and.K(3,3)>0._dp,'bearing axial terms are zero while shaft axial stiffness remains')
  ! Local-to-global sentinel: first shaft block equals B1 plus overlapping second-shaft contribution only outside its private first-node block.
  call shaft_6dof_matrices(sp(1,1),sp(2,1),sp(3,1),sp(4,1),sp(5,1),sp(6,1),sp(7,1),sp(8,1),sp(9,1),sp(10,1), &
       sf(1,1),sf(2,1),sf(3,1),sf(4,1),Me,Ke,Ge,Se,status)
  call check(status==B1_OK,'B1 direct shaft')
  call check(maxval(abs(M(1:6,1:6)-Me(1:6,1:6)))<1e-8_dp,'B1 mapped first node')
  call modal_from_matrices(M,K,C,G,120._dp,12_c_int,eall,Vall,nret,evals,qvec,wn,wd,zeta,logdec,mtype,whirl,residual,nsel,rcond,status)
  call check(status==B2_OK,'modal status')
  call check(nsel==6.and.nret>=nsel,'modal counts')
  call check(rcond>1e-14_dp,'mass conditioning')
  call check(maxval(residual)<1e-8_dp,'second-order residual')
  call check(all(wd>0._dp),'positive branch selection')
  speeds=[0._dp,100._dp,200._dp]
  do k=1,3;bmap(:,:,k)=bp;end do
  call campbell_6dof(nn,ns,sn,sp,sf,nd,dn,dd,nb,bn,3_c_int,speeds,bmap,2_c_int,c_wd,c_wn,c_zeta,c_log,c_whirl,c_type,track_idx,track_mac,macs,status)
  call check(status==B2_OK,'Campbell status')
  call check(all(c_wd>0._dp).and.all(c_wn>0._dp),'Campbell frequencies')
  call check(all(track_idx>=0_c_int).and.all(track_idx<4_c_int),'Campbell tracked indices')
  call check(all(track_mac>=0._dp).and.all(track_mac<=1._dp),'Campbell MAC range')
  speeds=[0._dp,100._dp,100._dp]
  call campbell_6dof(nn,ns,sn,sp,sf,nd,dn,dd,nb,bn,3_c_int,speeds,bmap,2_c_int,c_wd,c_wn,c_zeta,c_log,c_whirl,c_type,track_idx,track_mac,macs,status)
  call check(status==B2_INVALID_INPUT,'invalid speed grid fail closed')
  print *,'B2 6DOF GLOBAL/MODAL/CAMPBELL NATIVE CONTRACT: PASS'
contains
  subroutine check(ok,msg)
    logical,intent(in)::ok;character(*),intent(in)::msg
    if(.not.ok)then;print *,'FAIL: ',trim(msg);error stop 1;end if
  end subroutine
end program
