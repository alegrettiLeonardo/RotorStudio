module rd_irdin_support_analysis_c_api
  use iso_c_binding, only:c_double,c_int,c_int64_t
  use rd_kinds, only:rk,ik
  use rd_status, only:RD_OK,RD_ERR_INPUT
  use rd_irdin_support_analysis, only:irdin_expanded_modal,irdin_expanded_synchronous
  implicit none(type, external)
  private
  public::rd_irdin_support_modal_v1,rd_irdin_support_synchronous_v1
contains
  function rd_irdin_support_modal_v1(ndof,m_in,c_in,k_in,ldin,capin,nout,wr,wi,vr,vi,ldv,capv) &
      bind(C,name="rd_irdin_support_modal_v1") result(status)
    integer(c_int),value::ndof,ldin,capin,nout,ldv,capv
    real(c_double),intent(in)::m_in(*),c_in(*),k_in(*)
    real(c_double),intent(inout)::wr(*),wi(*),vr(*),vi(*)
    integer(c_int)::status
    integer::i,j
    integer(c_int64_t)::off
    real(rk),allocatable::m(:,:),c(:,:),k(:,:)
    complex(rk),allocatable::w(:),v(:,:)
    status=RD_ERR_INPUT
    if(ndof<1.or.ndof>1024)return
    if(ldin<ndof.or.nout<2*ndof.or.ldv<ndof)return
    if(int(capin,c_int64_t)<int((ndof-1)*ldin+ndof,c_int64_t))return
    if(int(capv,c_int64_t)<int((2*ndof-1)*ldv+ndof,c_int64_t))return
    allocate(m(ndof,ndof),c(ndof,ndof),k(ndof,ndof),w(2*ndof),v(ndof,2*ndof))
    do j=1,ndof;do i=1,ndof
      off=int((j-1)*ldin+i,c_int64_t)
      m(i,j)=m_in(off);c(i,j)=c_in(off);k(i,j)=k_in(off)
    enddo;enddo
    call irdin_expanded_modal(m,c,k,w,v,status)
    if(status/=RD_OK)return
    do i=1,2*ndof
      wr(i)=real(w(i),rk);wi(i)=aimag(w(i))
    enddo
    do j=1,2*ndof;do i=1,ndof
      off=int((j-1)*ldv+i,c_int64_t)
      vr(off)=real(v(i,j),rk);vi(off)=aimag(v(i,j))
    enddo;enddo
  end function

  function rd_irdin_support_synchronous_v1(nnode,ndof,m_in,c_in,k_in,ldin,capin,omega,nforce,nodes,mag,phase, &
      qr,qi,capq,residual) bind(C,name="rd_irdin_support_synchronous_v1") result(status)
    integer(c_int),value::nnode,ndof,ldin,capin,nforce,capq
    real(c_double),value::omega
    integer(c_int),intent(in)::nodes(*)
    real(c_double),intent(in)::m_in(*),c_in(*),k_in(*),mag(*),phase(*)
    real(c_double),intent(inout)::qr(*),qi(*)
    real(c_double),intent(out)::residual
    integer(c_int)::status
    integer::i,j
    integer(c_int64_t)::off
    integer(ik),allocatable::ndv(:)
    real(rk),allocatable::m(:,:),c(:,:),k(:,:),mv(:),pv(:)
    complex(rk),allocatable::q(:)
    status=RD_ERR_INPUT;residual=0._rk
    if(nnode<1.or.ndof<4*nnode.or.ndof>1024.or.nforce<1)return
    if(ldin<ndof.or.capq<ndof)return
    if(int(capin,c_int64_t)<int((ndof-1)*ldin+ndof,c_int64_t))return
    allocate(m(ndof,ndof),c(ndof,ndof),k(ndof,ndof),ndv(nforce),mv(nforce),pv(nforce),q(ndof))
    do j=1,ndof;do i=1,ndof
      off=int((j-1)*ldin+i,c_int64_t)
      m(i,j)=m_in(off);c(i,j)=c_in(off);k(i,j)=k_in(off)
    enddo;enddo
    do i=1,nforce
      ndv(i)=int(nodes(i),ik);mv(i)=mag(i);pv(i)=phase(i)
    enddo
    call irdin_expanded_synchronous(int(nnode,ik),m,c,k,omega,int(nforce,ik),ndv,mv,pv,q,residual,status)
    if(status/=RD_OK)return
    do i=1,ndof
      qr(i)=real(q(i),rk);qi(i)=aimag(q(i))
    enddo
  end function
end module
