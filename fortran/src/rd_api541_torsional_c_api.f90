module rd_api541_torsional_c_api
  use iso_c_binding, only: c_double, c_int, c_int64_t
  use rd_kinds, only: ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  use rd_api541_torsional, only: api541_torsional_modes
  implicit none(type, external)
  private
  public :: rd_api541_torsional_modes_v1
contains

  function rd_api541_torsional_modes_v1(n,inertia,stiffness,damping, &
      mout,cout,kout,ldm,capm,frequency,modes,ldv,capv) &
      bind(C,name="rd_api541_torsional_modes_v1") result(status)
    integer(c_int),value::n,ldm,capm,ldv,capv
    real(c_double),intent(in)::inertia(*),stiffness(*),damping(*)
    real(c_double),intent(inout)::mout(*),cout(*),kout(*),frequency(*),modes(*)
    integer(c_int)::status
    integer(c_int64_t)::needm,needv,off
    integer::i,j
    real(c_double),allocatable::iv(:),kv(:),cv(:),m(:,:),c(:,:),k(:,:),freq(:),vec(:,:)

    status=RD_ERR_INPUT
    if(n<2 .or. n>128)return
    if(ldm<n .or. ldv<n)return
    needm=int((n-1)*ldm+n,c_int64_t)
    needv=int((n-1)*ldv+n,c_int64_t)
    if(int(capm,c_int64_t)<needm .or. int(capv,c_int64_t)<needv)return

    allocate(iv(n),kv(n-1),cv(n-1),m(n,n),c(n,n),k(n,n),freq(n),vec(n,n))
    do i=1,n
      iv(i)=inertia(i)
    enddo
    do i=1,n-1
      kv(i)=stiffness(i);cv(i)=damping(i)
    enddo

    call api541_torsional_modes(int(n,ik),iv,kv,cv,m,c,k,freq,vec,status)
    if(status/=RD_OK)return

    do i=1,n
      frequency(i)=freq(i)
    enddo
    do j=1,n
      do i=1,n
        off=int((j-1)*ldm+i,c_int64_t)
        mout(off)=m(i,j);cout(off)=c(i,j);kout(off)=k(i,j)
        off=int((j-1)*ldv+i,c_int64_t)
        modes(off)=vec(i,j)
      enddo
    enddo
  end function

end module
