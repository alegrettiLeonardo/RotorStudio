module rd_irdin_support_global_c_api
  use iso_c_binding, only:c_double,c_int,c_int64_t
  use rd_kinds, only:ik
  use rd_irdin_support_global, only:irdin_support_global_matrices,I8_OK,I8_INVALID_DIMENSION,I8_INSUFFICIENT_CAPACITY
  implicit none(type, external);private
  public::rd_irdin_support_global_matrices_v1
contains
  function rd_irdin_support_global_matrices_v1(nnode,ns,nodes,mass,kb_in,cb_in,ks_in,cs_in, &
      mr_in,cr_in,gr_in,kr_in,ldin,capin,mout,cout,gout,kout,ldout,capout) &
      bind(C,name="rd_irdin_support_global_matrices_v1") result(status)
    integer(c_int),value::nnode,ns,ldin,capin,ldout,capout
    integer(c_int),intent(in)::nodes(*)
    real(c_double),intent(in)::mass(*),kb_in(*),cb_in(*),ks_in(*),cs_in(*)
    real(c_double),intent(in)::mr_in(*),cr_in(*),gr_in(*),kr_in(*)
    real(c_double),intent(inout)::mout(*),cout(*),gout(*),kout(*)
    integer(c_int)::status
    integer::nd,no,i,j,s
    integer(c_int64_t)::off
    integer(ik),allocatable::ndv(:)
    real(c_double),allocatable::mv(:),kb(:,:,:),cb(:,:,:),ks(:,:,:),cs(:,:,:)
    real(c_double),allocatable::mr(:,:),cr(:,:),gr(:,:),kr(:,:),m(:,:),c(:,:),g(:,:),k(:,:)
    status=I8_INVALID_DIMENSION
    if(nnode<1.or.ns<1)return
    nd=4*nnode;no=nd+2*ns
    if(ldin<nd.or.ldout<no)return
    status=I8_INSUFFICIENT_CAPACITY
    if(int(capin,c_int64_t)<int((nd-1)*ldin+nd,c_int64_t))return
    if(int(capout,c_int64_t)<int((no-1)*ldout+no,c_int64_t))return
    allocate(ndv(ns),mv(ns),kb(2,2,ns),cb(2,2,ns),ks(2,2,ns),cs(2,2,ns))
    allocate(mr(nd,nd),cr(nd,nd),gr(nd,nd),kr(nd,nd),m(no,no),c(no,no),g(no,no),k(no,no))
    do s=1,ns
      ndv(s)=int(nodes(s),ik);mv(s)=mass(s)
      do j=1,2;do i=1,2
        off=int((s-1)*4+(j-1)*2+i,c_int64_t)
        kb(i,j,s)=kb_in(off);cb(i,j,s)=cb_in(off);ks(i,j,s)=ks_in(off);cs(i,j,s)=cs_in(off)
      enddo;enddo
    enddo
    do j=1,nd;do i=1,nd
      off=int((j-1)*ldin+i,c_int64_t)
      mr(i,j)=mr_in(off);cr(i,j)=cr_in(off);gr(i,j)=gr_in(off);kr(i,j)=kr_in(off)
    enddo;enddo
    call irdin_support_global_matrices(int(nnode,ik),int(ns,ik),ndv,mv,kb,cb,ks,cs,mr,cr,gr,kr,m,c,g,k,status)
    if(status/=I8_OK)return
    do j=1,no;do i=1,no
      off=int((j-1)*ldout+i,c_int64_t)
      mout(off)=m(i,j);cout(off)=c(i,j);gout(off)=g(i,j);kout(off)=k(i,j)
    enddo;enddo
  end function
end module
