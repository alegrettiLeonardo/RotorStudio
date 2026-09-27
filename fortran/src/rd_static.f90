! ROSS-derived static semantics: petrobras/ross@6320eab9, Rotor.run_static.
! Algorithm attribution: ROSS developers, Apache-2.0. See implementation document.
! Existing circular element formulas are reused only for the qualified M/K scope.
module rd_static
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT, RD_ERR_UNSUPPORTED, RD_ERR_LAPACK
  use rd_assembly_stationary, only: assemble_rotor
  use rd_lapack, only: solve_real
  implicit none(type, external)
  private
  public :: static_solve
  real(rk), parameter :: gravity=-9.8065_rk, support_k=1.e20_rk
contains
  subroutine static_solve(nn,z,ns,shaft,nd,disk,nb,bearing,q,reaction,sw,dw,shear,bending,station,diagnostics,status)
    integer(ik), intent(in) :: nn,ns,nd,nb
    real(rk), intent(in) :: z(nn),shaft(11,ns),disk(6,nd),bearing(34,nb)
    real(rk), intent(out) :: q(4*nn),reaction(nn),sw(ns),dw(nd),shear(2*ns),bending(2*ns),station(2*ns),diagnostics(3)
    integer(ik), intent(out) :: status
    real(rk), allocatable :: mass(:,:),k0(:,:),c0(:,:),g0(:,:),k1(:,:),kp(:,:),a(:,:),rhs(:,:)
    real(rk), allocatable :: acceleration(:),weight(:),internal(:),nodal_weight(:),nf(:),ef(:,:),vx(:,:),mx(:,:)
    logical, allocatable :: support(:)
    integer :: i,n,t,j,alloc_status
    real(rk) :: pi,volume,element_length,total_weight,moment_load,denom
    q=0;reaction=0;sw=0;dw=0;shear=0;bending=0;station=0;diagnostics=0
    status=RD_ERR_INPUT
    if(nn<2.or.ns/=nn-1.or.nd<0.or.nb<1)return
    if(nn>1000)then;status=RD_ERR_UNSUPPORTED;return;endif
    if(.not.all(ieee_is_finite(z)).or..not.all(ieee_is_finite(shaft)))return
    if(.not.all(ieee_is_finite(disk)).or..not.all(ieee_is_finite(bearing)))return
    if(any(z(2:nn)<=z(1:nn-1)))return
    do i=1,ns
      if(shaft(1,i)<1.or.shaft(1,i)>8)then;status=RD_ERR_UNSUPPORTED;return;endif
      t=nint(shaft(1,i));if(shaft(1,i)/=real(t,rk))return
      if(shaft(2,i)/=real(i,rk).or.shaft(3,i)/=real(i+1,rk))then
        status=RD_ERR_UNSUPPORTED;return
      endif
      if(shaft(4,i)<=shaft(5,i).or.shaft(5,i)<0.or.shaft(6,i)<=0.or.shaft(7,i)<=0)return
      if(t/=1.and.t/=5.and.t/=7.and.t/=8)then
        if(shaft(8,i)<=0)return
      endif
      if(any(shaft(10:11,i)/=0))then;status=RD_ERR_UNSUPPORTED;return;endif
    enddo
    do i=1,nd
      if(disk(1,i)<1.or.disk(1,i)>4)then;status=RD_ERR_UNSUPPORTED;return;endif
      t=nint(disk(1,i));if(disk(1,i)/=real(t,rk))return
      if(disk(2,i)<1.or.disk(2,i)>nn)return
      n=nint(disk(2,i));if(disk(2,i)/=real(n,rk))return
      if(disk(3,i)<=0)return
      if(t==1.or.t==3)then
        if(disk(4,i)<=0.or.disk(5,i)<=disk(6,i).or.disk(6,i)<0)return
      else
        if(any(disk(4:5,i)<0))return
      endif
    enddo
    do i=1,nb
      if(bearing(1,i)<1.or.bearing(1,i)>8)then;status=RD_ERR_UNSUPPORTED;return;endif
      t=nint(bearing(1,i));if(bearing(1,i)/=real(t,rk))return
      if(bearing(2,i)<1.or.bearing(2,i)>nn)return
      n=nint(bearing(2,i));if(bearing(2,i)/=real(n,rk))return
    enddo
    n=4*nn
    allocate(mass(n,n),k0(n,n),c0(n,n),g0(n,n),k1(n,n),kp(n,n),a(n,n),rhs(n,1), &
      acceleration(n),weight(n),internal(n),nodal_weight(nn),nf(nn),ef(ns,2),vx(ns,2),mx(ns,2),support(nn),stat=alloc_status)
    if(alloc_status/=0)return
    support=.false.
    do i=1,nb
      if(nint(bearing(1,i))/=8)support(nint(bearing(2,i)))=.true.
    enddo
    if(count(support)==0)return
    ! A single radial support leaves a rigid rotation. Detect it before a
    ! floating-point factorization accidentally accepts the near-singular K.
    if(count(support)<2)then;status=RD_ERR_LAPACK;return;endif
    call assemble_rotor(nn,z,ns,shaft,nd,disk,mass,c0,g0,k0,k1,status)
    if(status/=RD_OK)return
    if(.not.all(ieee_is_finite(mass)).or..not.all(ieee_is_finite(k0)))then
      status=RD_ERR_INPUT;return
    endif
    kp=k0
    do i=1,nb
      if(nint(bearing(1,i))==8)cycle ! Seals never act as static supports.
      j=4*nint(bearing(2,i))-3
      kp(j,j)=kp(j,j)+support_k;kp(j+1,j+1)=kp(j+1,j+1)+support_k
    enddo
    acceleration=0;acceleration(2:n:4)=gravity
    weight=matmul(mass,acceleration)
    a=kp;rhs(:,1)=weight
    call solve_real(a,rhs,status)
    if(status/=RD_OK)return
    if(.not.all(ieee_is_finite(rhs)))then;status=RD_ERR_LAPACK;return;endif
    q=rhs(:,1);internal=matmul(k0,q)
    where(support)reaction=internal(2:n:4)-weight(2:n:4)
    pi=acos(-1._rk);nodal_weight=0;ef=0;moment_load=0
    do i=1,ns
      element_length=z(i+1)-z(i)
      sw(i)=-gravity*shaft(6,i)*pi*(shaft(4,i)**2-shaft(5,i)**2)*element_length/4
      nodal_weight(i:i+1)=nodal_weight(i:i+1)-sw(i)/2
      moment_load=moment_load+sw(i)*(z(i)+element_length/2)
      station(2*i-1:2*i)=[z(i),z(i+1)]
      ef(i,2)=-sw(i)
    enddo
    do i=1,nd
      t=nint(disk(1,i))
      if(t==1.or.t==3)then
        volume=pi*disk(4,i)*(disk(5,i)**2-disk(6,i)**2)/4
        dw(i)=-gravity*disk(3,i)*volume
      else
        dw(i)=-gravity*disk(3,i)
      endif
      moment_load=moment_load+dw(i)*z(nint(disk(2,i)))
    enddo
    ! Preserve the ROSS repeated-end-station recovery, including its final span.
    nf=internal(2:n:4)-nodal_weight
    ef(:,1)=nf(1:nn-1);ef(ns,2)=-nf(nn)
    vx=0;mx=0
    do i=1,ns
      if(i==1)then
        vx(i,:)=[ef(i,1),sum(ef(i,:))]
      elseif(i==ns)then
        vx(i,:)=[vx(i-1,2)+ef(i,1),ef(i,2)]
      else
        vx(i,1)=vx(i-1,2)+ef(i,1);vx(i,2)=vx(i,1)+ef(i,2)
      endif
    enddo
    vx=-vx
    do i=1,ns
      element_length=z(i+1)-z(i)
      if(i==ns)then
        mx(i,:)=[-sum(vx(i,:))*element_length/2,0._rk]
      else
        if(i>1)mx(i,1)=mx(i-1,2)
        mx(i,2)=mx(i,1)+sum(vx(i,:))*element_length/2
      endif
      shear(2*i-1:2*i)=vx(i,:);bending(2*i-1:2*i)=mx(i,:)
    enddo
    total_weight=sum(sw)+sum(dw)
    diagnostics(1)=sum(reaction)-total_weight
    diagnostics(2)=dot_product(reaction,z)-moment_load
    ! Infinity-norm backward residual; penalty conditioning is reported separately
    ! in qualification, not mistaken for a small forward-error guarantee.
    denom=maxval(sum(abs(kp),dim=2))*maxval(abs(q))+maxval(abs(weight))
    diagnostics(3)=maxval(abs(matmul(kp,q)-weight))/max(denom,tiny(1._rk))
    if(.not.all(ieee_is_finite(diagnostics)).or..not.all(ieee_is_finite(shear)).or. &
       .not.all(ieee_is_finite(bending)))then;status=RD_ERR_LAPACK;return;endif
    status=RD_OK
  end subroutine
end module
