module rd_irdin_support_global
  use rd_kinds, only: rk, ik
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  implicit none(type, external)
  private
  integer(ik), parameter, public :: I8_OK=0_ik
  integer(ik), parameter, public :: I8_INVALID_INPUT=10_ik
  integer(ik), parameter, public :: I8_NONFINITE_RESULT=14_ik
  public :: irdin_support_global_matrices
contains
  subroutine irdin_support_global_matrices(nnode,ns,nodes,mass,kb,cb,ks,cs,mr,cr,gr,kr,m,c,g,k,status)
    integer(ik),intent(in)::nnode,ns,nodes(ns)
    real(rk),intent(in)::mass(ns),kb(2,2,ns),cb(2,2,ns),ks(2,2,ns),cs(2,2,ns)
    real(rk),intent(in)::mr(4*nnode,4*nnode),cr(4*nnode,4*nnode),gr(4*nnode,4*nnode),kr(4*nnode,4*nnode)
    real(rk),intent(out)::m(4*nnode+2*ns,4*nnode+2*ns),c(4*nnode+2*ns,4*nnode+2*ns)
    real(rk),intent(out)::g(4*nnode+2*ns,4*nnode+2*ns),k(4*nnode+2*ns,4*nnode+2*ns)
    integer(ik),intent(out)::status
    integer::s,nd,rx,ry,sx,sy
    status=I8_INVALID_INPUT
    if(nnode<1.or.ns<1)return
    if(any(nodes<1).or.any(nodes>nnode))return
    do s=1,ns
      if(count(nodes==nodes(s))/=1)return
    enddo
    if(any(.not.ieee_is_finite(mass)).or.any(mass<=0._rk))return
    if(.not.all(ieee_is_finite(kb)).or..not.all(ieee_is_finite(cb)))return
    if(.not.all(ieee_is_finite(ks)).or..not.all(ieee_is_finite(cs)))return
    if(.not.all(ieee_is_finite(mr)).or..not.all(ieee_is_finite(cr)))return
    if(.not.all(ieee_is_finite(gr)).or..not.all(ieee_is_finite(kr)))return
    nd=4*nnode
    m=0._rk;c=0._rk;g=0._rk;k=0._rk
    m(1:nd,1:nd)=mr;c(1:nd,1:nd)=cr;g(1:nd,1:nd)=gr;k(1:nd,1:nd)=kr
    do s=1,ns
      rx=4*nodes(s)-3;ry=rx+1
      sx=nd+2*s-1;sy=sx+1
      m(sx,sx)=m(sx,sx)+mass(s);m(sy,sy)=m(sy,sy)+mass(s)
      k(rx:ry,rx:ry)=k(rx:ry,rx:ry)+kb(:,:,s)
      k(rx:ry,sx:sy)=k(rx:ry,sx:sy)-kb(:,:,s)
      k(sx:sy,rx:ry)=k(sx:sy,rx:ry)-kb(:,:,s)
      k(sx:sy,sx:sy)=k(sx:sy,sx:sy)+kb(:,:,s)+ks(:,:,s)
      c(rx:ry,rx:ry)=c(rx:ry,rx:ry)+cb(:,:,s)
      c(rx:ry,sx:sy)=c(rx:ry,sx:sy)-cb(:,:,s)
      c(sx:sy,rx:ry)=c(sx:sy,rx:ry)-cb(:,:,s)
      c(sx:sy,sx:sy)=c(sx:sy,sx:sy)+cb(:,:,s)+cs(:,:,s)
    enddo
    if(.not.all(ieee_is_finite(m)).or..not.all(ieee_is_finite(c)).or. &
       .not.all(ieee_is_finite(g)).or..not.all(ieee_is_finite(k)))then
      status=I8_NONFINITE_RESULT;return
    endif
    status=I8_OK
  end subroutine
end module
