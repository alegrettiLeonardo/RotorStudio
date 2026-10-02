module rd_api541_torsional_response_c_api
  use iso_c_binding, only: c_double, c_int, c_int64_t
  use rd_kinds, only: ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  use rd_api541_torsional_response, only: api541_torsional_harmonic_response
  implicit none(type, external)
  private
  public :: rd_api541_torsional_response_v1
contains

  function rd_api541_torsional_response_v1(n,inertia,stiffness,damping,nf,omega, &
      fr_in,fi_in,ldf,capf,qr_out,qi_out,tr_out,ti_out,ldt,capt) &
      bind(C,name="rd_api541_torsional_response_v1") result(status)
    integer(c_int),value::n,nf,ldf,capf,ldt,capt
    real(c_double),intent(in)::inertia(*),stiffness(*),damping(*),omega(*),fr_in(*),fi_in(*)
    real(c_double),intent(inout)::qr_out(*),qi_out(*),tr_out(*),ti_out(*)
    integer(c_int)::status
    integer(c_int64_t)::needf,needt,off
    integer::i,j
    real(c_double),allocatable::iv(:),kv(:),cv(:),wv(:),fr(:,:),fi(:,:),qr(:,:),qi(:,:),tr(:,:),ti(:,:)

    status=RD_ERR_INPUT
    if(n<2 .or. n>128 .or. nf<1 .or. nf>10000)return
    if(ldf<n .or. ldt<n-1)return
    needf=int((nf-1)*ldf+n,c_int64_t)
    needt=int((nf-1)*ldt+(n-1),c_int64_t)
    if(int(capf,c_int64_t)<needf .or. int(capt,c_int64_t)<needt)return

    allocate(iv(n),kv(n-1),cv(n-1),wv(nf),fr(n,nf),fi(n,nf),qr(n,nf),qi(n,nf),tr(n-1,nf),ti(n-1,nf))
    do i=1,n
      iv(i)=inertia(i)
    enddo
    do i=1,n-1
      kv(i)=stiffness(i);cv(i)=damping(i)
    enddo
    do j=1,nf
      wv(j)=omega(j)
      do i=1,n
        off=int((j-1)*ldf+i,c_int64_t)
        fr(i,j)=fr_in(off);fi(i,j)=fi_in(off)
      enddo
    enddo

    call api541_torsional_harmonic_response(int(n,ik),iv,kv,cv,int(nf,ik),wv,fr,fi,qr,qi,tr,ti,status)
    if(status/=RD_OK)return

    do j=1,nf
      do i=1,n
        off=int((j-1)*ldf+i,c_int64_t)
        qr_out(off)=qr(i,j);qi_out(off)=qi(i,j)
      enddo
      do i=1,n-1
        off=int((j-1)*ldt+i,c_int64_t)
        tr_out(off)=tr(i,j);ti_out(off)=ti(i,j)
      enddo
    enddo
  end function

end module
