program test_axial_torsional
  use iso_c_binding, only:c_double,c_int
  use rd_6dof_assembly, only:assemble_6dof,B2_OK
  use rd_axial_torsional, only:family_modal_from_global,B3_OK,B3_INVALID_INPUT,B3_UNSUPPORTED
  use rd_axial_torsional_c_api, only:rd_axial_torsional_required_v1
  implicit none
  integer,parameter::dp=c_double
  integer(c_int),parameter::nn=3,ns=2,nd=1,nb=2
  integer(c_int)::sn(2,ns),sf(4,ns),dn(nd),bn(nb),st,nm,nm2,maxm,mvals,vvals
  real(dp)::sp(10,ns),dd(3,nd),bp(12,nb)
  real(dp)::M6(18,18),K6(18,18),C6(18,18),G6(18,18),S6(18,18),Kbad(18,18)
  real(dp)::M(3,3),K(3,3),C(3,3),G(3,3),S(3,3),wn(2),wd(2),zeta(2),logdec(2),q(3,2),res(2),dec
  real(dp)::M2(3,3),K2(3,3),C2(3,3),G2(3,3),S2(3,3),wn2(2),wd2(2),zeta2(2),logdec2(2),q2(3,2),res2(2),dec2
  integer::i,j

  sn=reshape([1_c_int,2_c_int,2_c_int,3_c_int],[2,2])
  sf=1;sf(4,:)=1
  sp=0._dp
  do j=1,ns
    sp(:,j)=[0.22_dp,0._dp,0.05_dp,0._dp,0.05_dp,7810._dp,211e9_dp,81.2e9_dp,0._dp,0._dp]
  end do
  dn=[2_c_int];dd(:,1)=[12._dp,0.04_dp,0.08_dp]
  bn=[1_c_int,3_c_int];bp=0._dp
  do j=1,nb
    bp(1,j)=1e6_dp;bp(4,j)=1e6_dp;bp(5,j)=1e3_dp;bp(8,j)=1e3_dp
  end do

  call assemble_6dof(nn,ns,sn,sp,sf,nd,dn,dd,nb,bn,bp,M6,K6,C6,G6,S6,st)
  call check(st==B2_OK,'B2 assembly')

  call family_modal_from_global(nn,1_c_int,0._dp,M6,K6,C6,G6,S6,M,K,C,G,S, &
    wn,wd,zeta,logdec,q,res,dec,nm,st)
  call check(st==B3_OK.and.nm==2,'axial modal status/count')
  call check(dec==0._dp,'axial exact decoupling')
  call check(all(wn>0._dp).and.all(wd==wn),'axial positive undamped frequency')
  call check(all(zeta==0._dp).and.all(logdec==0._dp),'axial undamped scalars')
  call check(maxval(abs(C))+maxval(abs(G))+maxval(abs(S))==0._dp,'axial zero C/G/Ksdt')
  call check(maxval(res)<1e-10_dp,'axial generalized residual')
  do j=1,nm
    call check(abs(sum(q(:,j)*q(:,j))-1._dp)<1e-12_dp,'axial vector normalization')
  end do

  call family_modal_from_global(nn,1_c_int,200._dp,M6,K6,C6,G6,S6,M2,K2,C2,G2,S2, &
    wn2,wd2,zeta2,logdec2,q2,res2,dec2,nm2,st)
  call check(st==B3_OK.and.nm2==nm,'axial speed repeat')
  call check(maxval(abs(wn2-wn))<1e-10_dp,'axial speed invariance')

  call family_modal_from_global(nn,2_c_int,0._dp,M6,K6,C6,G6,S6,M,K,C,G,S, &
    wn,wd,zeta,logdec,q,res,dec,nm,st)
  call check(st==B3_OK.and.nm==2,'torsional modal status/count')
  call check(dec==0._dp,'torsional exact decoupling')
  call check(all(wn>0._dp).and.all(wd==wn),'torsional positive undamped frequency')
  call check(maxval(res)<1e-10_dp,'torsional generalized residual')

  call family_modal_from_global(nn,2_c_int,250._dp,M6,K6,C6,G6,S6,M2,K2,C2,G2,S2, &
    wn2,wd2,zeta2,logdec2,q2,res2,dec2,nm2,st)
  call check(st==B3_OK.and.maxval(abs(wn2-wn))<1e-10_dp,'torsional speed invariance')

  call family_modal_from_global(nn,3_c_int,0._dp,M6,K6,C6,G6,S6,M,K,C,G,S, &
    wn,wd,zeta,logdec,q,res,dec,nm,st)
  call check(st==B3_INVALID_INPUT,'invalid family fail closed')

  Kbad=K6;Kbad(3,1)=1._dp;Kbad(1,3)=1._dp
  call family_modal_from_global(nn,1_c_int,0._dp,M6,Kbad,C6,G6,S6,M,K,C,G,S, &
    wn,wd,zeta,logdec,q,res,dec,nm,st)
  call check(st==B3_UNSUPPORTED.and.dec>0._dp,'coupled family fail closed')

  st=rd_axial_torsional_required_v1(1_c_int,maxm,mvals,vvals)
  call check(st==B3_INVALID_INPUT,'required invalid dimension')
  st=rd_axial_torsional_required_v1(nn,maxm,mvals,vvals)
  call check(st==B3_OK.and.maxm==2.and.mvals==9.and.vvals==6,'required sizes')

  print *,'B3 AXIAL/TORSIONAL NATIVE CONTRACT: PASS'
contains
  subroutine check(ok,msg)
    logical,intent(in)::ok
    character(*),intent(in)::msg
    if(.not.ok)then
      print *,'FAIL: ',trim(msg)
      error stop 1
    end if
  end subroutine
end program
