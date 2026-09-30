program test_6dof_elements
  use iso_c_binding, only: c_double,c_int
  use, intrinsic :: ieee_arithmetic
  use rd_shaft_6dof
  use rd_disk_6dof
  use rd_6dof_element_c_api
  implicit none(type, external)
  integer, parameter :: dp=c_double
  real(dp), parameter :: guard=-91827.125_dp
  real(dp) :: v(10),w(10),M(12,12),K(12,12),G(12,12),S(12,12)
  real(dp) :: M0(12,12),K0(12,12),G0(12,12),S0(12,12),Kp(12,12)
  real(dp) :: buf(220,4),db(96,3),q(12),A,polar,pi,mass,energy,Inf,NaN
  real(dp) :: dm(6,6),dg(6,6),dk(6,6),d(3),invalid(3)
  integer(c_int) :: flags(4),f(4),lds(4),caps(4),dd(3),dc(3),st
  integer :: i,j,kk,checks
  logical :: mask(220),dmask(96)
  checks=0
  v=[0.173_dp,0.012_dp,0.047_dp,0.012_dp,0.047_dp,7813._dp,207e9_dp,79.5e9_dp,0._dp,0._dp]
  flags=[1_c_int,1_c_int,1_c_int,1_c_int]
  lds=[14_c_int,15_c_int,16_c_int,17_c_int]; caps=11*lds+12
  NaN=ieee_value(0._dp,ieee_quiet_nan); Inf=ieee_value(0._dp,ieee_positive_inf)
  invalid=[NaN,Inf,-Inf]
  call core(v,flags,M0,K0,G0,S0,st)
  call check(st==B1_OK,'valid shaft')
  call check(all(M0==transpose(M0)),'symmetric M')
  call check(all(K0==transpose(K0)),'untorqued symmetric K')
  call check(all(G0==-transpose(G0)),'skew G')
  pi=acos(-1._dp)
  A=pi*(v(3)**2-v(2)**2)/4; polar=pi*(v(3)**4-v(2)**4)/32
  mass=v(6)*A*v(1)
  call close(M0(3,3),mass/3,'axial M diagonal')
  call close(M0(3,9),mass/6,'axial M coupling')
  call close(M0(6,6),v(6)*polar*v(1)/3,'torsional M diagonal')
  call close(K0(3,3),v(7)*A/v(1),'axial K')
  call close(K0(6,6),v(8)*polar/v(1),'torsional K')
  do i=1,6
    q=0
    select case(i)
    case(1); q(1)=1; q(7)=1
    case(2); q(2)=1; q(8)=1
    case(3); q(3)=1; q(9)=1
    case(4); q(6)=1; q(12)=1
    case(5); q(4)=1; q(10)=1; q(8)=-v(1)
    case(6); q(5)=1; q(11)=1; q(7)=v(1)
    end select
    call check(maxval(abs(matmul(K0,q)))<=1024*epsilon(1._dp)*maxval(abs(K0)), 'rigid motion')
  end do
  q=0; q(3)=0.013_dp; q(9)=-0.007_dp
  energy=0.5_dp*dot_product(q,matmul(K0,q))
  call close(energy,v(7)*A/(2*v(1))*(q(9)-q(3))**2,'axial energy')
  q=0; q(6)=-0.02_dp; q(12)=0.031_dp
  energy=0.5_dp*dot_product(q,matmul(K0,q))
  call close(energy,v(8)*polar/(2*v(1))*(q(12)-q(6))**2,'torsional energy')
  do i=0,7
    f=[int(iand(i,1),c_int),int(iand(ishft(i,-1),1),c_int),int(iand(ishft(i,-2),1),c_int),1_c_int]
    call core(v,f,M,K,G,S,st)
    call check(st==B1_OK,'all flag combinations')
    call check(all(S==S0) .and. any(S/=0),'independent Kst for flags')
    call check(M(6,6)==M0(6,6) .and. K(6,6)==K0(6,6),'torsional blocks survive flags')
    if (f(3)==0) call check(all(G==0),'gyro off gives zero G')
  end do
  f=flags; f(4)=2
  call core(v,f,M,K,G,S,st)
  call check(st==B1_OK .and. any(K/=K0),'Hutchinson differs from Cowper')
  w=v; w(2)=0; w(4)=0
  call core(w,flags,M,K,G,S,st)
  call check(st==B1_OK .and. M(3,3)>M0(3,3),'solid versus hollow')
  w=v; w(2)=0.008_dp; w(3)=0.037_dp; w(4)=0.019_dp; w(5)=0.063_dp
  call core(w,flags,M,K,G,S,st); mass=M(1,1)
  call check(st==B1_OK,'conical')
  w=[w(1),w(4),w(5),w(2),w(3),w(6:10)]
  call core(w,flags,M,K,G,S,st)
  call check(st==B1_OK .and. abs(M(1,1)-mass)>0.01_dp,'reversed conical is not cylinder')
  w=v; w(6)=2*v(6)
  call core(w,flags,M,K,G,S,st)
  call check(st==B1_OK,'density call')
  call check(all(M==2*M0) .and. all(G==2*G0) .and. all(S==2*S0) .and. all(K==K0),'density scaling')
  w=v; w(9)=1234.5_dp
  call core(w,flags,M,Kp,G,S,st)
  w(9)=-w(9)
  call core(w,flags,M,K,G,S,st)
  call check(all(abs((Kp-K0)+(K-K0))<=32*epsilon(1._dp)*(abs(Kp)+abs(K0)+abs(K))), 'signed axial load')
  w=v; w(10)=12.375_dp
  call core(w,flags,M,K,G,S,st)
  call close(K(4,5),-w(10)/2,'positive torque offdiagonal')
  call close(K(5,4),w(10)/2,'positive torque reverse sign')
  call check(any(K/=transpose(K)),'torque K not symmetrized')
  w(10)=-w(10)
  call core(w,flags,M,K,G,S,st)
  call close(K(4,5),-w(10)/2,'negative torque offdiagonal')
  ! Valid padded buffers: initial/final canaries and inter-column padding.
  buf=guard; st=raw_shaft(v,flags,buf,lds,caps)
  call check(st==B1_OK,'padded shaft ABI')
  do kk=1,4
    mask=.false.
    do j=1,12
      do i=1,12
        mask(2+i+(j-1)*lds(kk))=.true.
      end do
    end do
    call check(all(pack(buf(:,kk),.not.mask)==guard),'shaft guard zones')
  end do
  call check(buf(2+1+lds(4),4)==S0(1,2),'Kst row/column orientation')
  call check(buf(2+2,4)==0,'Kst opposite entry remains zero')
  do kk=1,4
    f=flags; f(kk)=-1; buf=guard
    st=raw_shaft(v,f,buf,lds,caps)
    call check(st==B1_INVALID_ENUM .and. all(buf==guard),'invalid enum preserves buffers')
  end do
  do kk=1,4
    block
      integer(c_int) :: badld(4),badcap(4)
      badld=lds; badcap=caps; badld(kk)=11; buf=guard
      st=raw_shaft(v,flags,buf,badld,badcap)
      call check(st==B1_INVALID_DIMENSION .and. all(buf==guard),'bad shaft leading dimension')
      badld=lds; badcap(kk)=caps(kk)-1; buf=guard
      st=raw_shaft(v,flags,buf,badld,badcap)
      call check(st==B1_INSUFFICIENT_CAPACITY .and. all(buf==guard),'bad shaft capacity')
      badld(kk)=huge(1_c_int); badcap(kk)=caps(kk); buf=guard
      st=raw_shaft(v,flags,buf,badld,badcap)
      call check(st==B1_INSUFFICIENT_CAPACITY .and. all(buf==guard),'capacity arithmetic cannot wrap')
    end block
  end do
  do i=1,10
    do j=1,3
      w=v; w(i)=invalid(j); buf=guard
      st=raw_shaft(w,flags,buf,lds,caps)
      call check(st==B1_INVALID_INPUT .and. all(buf==guard),'shaft NaN/Inf without writes')
    end do
  end do
  do i=1,8
    w=v; w(i)=-1; buf=guard
    st=raw_shaft(w,flags,buf,lds,caps)
    call check(st==B1_INVALID_INPUT .and. all(buf==guard),'invalid shaft scalar')
  end do
  w=v; w(1)=0; buf=guard; st=raw_shaft(w,flags,buf,lds,caps)
  call check(st==B1_INVALID_INPUT .and. all(buf==guard),'zero length')
  w=v; w(1)=1e-300_dp; buf=guard; st=raw_shaft(w,flags,buf,lds,caps)
  call check(st==B1_NONFINITE_RESULT .and. all(buf==guard),'nonfinite computation from finite inputs')
  d=[17.125_dp,0.0825_dp,0.134_dp]; dm=guard; dg=guard; dk=guard
  call disk_6dof_matrices(d(1),d(2),d(3),dm,dg,dk,st)
  call check(st==B1_OK,'disk kernel')
  do j=1,6
    do i=1,6
      if(i/=j) call check(dm(i,j)==0,'disk diagonal-only mass')
    end do
  end do
  call check(all([dm(1,1),dm(2,2),dm(3,3)]==d(1)), 'disk translational mass')
  call check(dm(4,4)==d(2) .and. dm(5,5)==d(2) .and. dm(6,6)==d(3),'disk inertias')
  call check(dg(4,5)==d(3) .and. dg(5,4)==-d(3) .and. count(dg/=0)==2,'disk G signs')
  call check(dk(5,4)==d(3) .and. count(dk/=0)==1,'one-sided Kdt')
  dd=8; dc=5*dd+6; db=guard; st=raw_disk(d,db,dd,dc)
  call check(st==B1_OK,'disk padded ABI')
  do kk=1,3
    dmask=.false.
    do j=1,6
      do i=1,6
        dmask(2+i+(j-1)*dd(kk))=.true.
      end do
    end do
    call check(all(pack(db(:,kk),.not.dmask)==guard),'disk guard zones')
  end do
  call check(db(2+5+3*dd(3),3)==d(3) .and. db(2+4+4*dd(3),3)==0,'disk column-major orientation')
  do i=1,3
    do j=1,3
      block
        real(dp) :: bad(3)
        bad=d; bad(i)=invalid(j); db=guard; st=raw_disk(bad,db,dd,dc)
        call check(st==B1_INVALID_INPUT .and. all(db==guard),'disk nonfinite input')
      end block
    end do
    block
      real(dp) :: bad(3)
      integer(c_int) :: dl(3),cp(3)
      bad=d; bad(i)=0; db=guard; st=raw_disk(bad,db,dd,dc)
      call check(st==B1_INVALID_INPUT .and. all(db==guard),'zero disk inertia is out of scope')
      dl=dd; cp=dc; dl(i)=5; db=guard; st=raw_disk(d,db,dl,cp)
      call check(st==B1_INVALID_DIMENSION .and. all(db==guard),'disk bad dimension')
      dl=dd; cp(i)=dc(i)-1; db=guard; st=raw_disk(d,db,dl,cp)
      call check(st==B1_INSUFFICIENT_CAPACITY .and. all(db==guard),'disk bad capacity')
    end block
  end do
  print *, 'B1_NATIVE_CTEST_PASS checks=',checks
contains
  subroutine check(ok,label)
    logical,intent(in) :: ok
    character(*),intent(in) :: label
    checks=checks+1
    if(.not.ok) then
      print *, 'FAIL: ',label
      error stop 1
    end if
  end subroutine
  subroutine close(a,b,label)
    real(dp),intent(in) :: a,b
    character(*),intent(in) :: label
    call check(abs(a-b)<=1024*epsilon(1._dp)*max(abs(b),tiny(1._dp)),label)
  end subroutine
  subroutine core(p,f,mo,ko,go,so,rc)
    real(dp),intent(in) :: p(10)
    integer(c_int),intent(in) :: f(4)
    real(dp),intent(inout) :: mo(12,12),ko(12,12),go(12,12),so(12,12)
    integer(c_int),intent(out) :: rc
    call shaft_6dof_matrices(p(1),p(2),p(3),p(4),p(5),p(6),p(7),p(8),p(9),p(10), &
                             f(1),f(2),f(3),f(4),mo,ko,go,so,rc)
  end subroutine
  function raw_shaft(p,f,b,ld,cp) result(rc)
    real(dp),intent(in) :: p(10)
    integer(c_int),intent(in) :: f(4),ld(4),cp(4)
    real(dp),intent(inout) :: b(:,:)
    integer(c_int) :: rc
    rc=rd_shaft_6dof_matrices_v1(p(1),p(2),p(3),p(4),p(5),p(6),p(7),p(8),p(9),p(10), &
       f(1),f(2),f(3),f(4),b(3:,1),ld(1),cp(1),b(3:,2),ld(2),cp(2),b(3:,3),ld(3),cp(3),b(3:,4),ld(4),cp(4))
  end function
  function raw_disk(p,b,ld,cp) result(rc)
    real(dp),intent(in) :: p(3)
    integer(c_int),intent(in) :: ld(3),cp(3)
    real(dp),intent(inout) :: b(:,:)
    integer(c_int) :: rc
    rc=rd_disk_6dof_matrices_v1(p(1),p(2),p(3),b(3:,1),ld(1),cp(1),b(3:,2),ld(2),cp(2),b(3:,3),ld(3),cp(3))
  end function
end program test_6dof_elements
