! ROSS A5 intersection authority provenance:
! Derived directly from ross.utils.intersection() in petrobras/ross at
! 6320eab9f890f1b3cc1710d508b446fe063ca68d, itself derived from
! https://github.com/sukhbinder/intersection
!
! MIT License
! Copyright (c) 2017 Sukhbinder Singh
! Permission is hereby granted, free of charge, to any person obtaining a copy
! of this software and associated documentation files (the "Software"), to deal
! in the Software without restriction, including without limitation the rights
! to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
! copies of the Software, and to permit persons to whom the Software is
! furnished to do so, subject to the following conditions:
! The above copyright notice and this permission notice shall be included in all
! copies or substantial portions of the Software.
! THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
! IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
! FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
! AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
! LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
! OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
! SOFTWARE.
module rd_intersections
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT
 implicit none(type,external)
 private
 public::curve_intersections
contains
 subroutine curve_intersections(n1,x1,y1,n2,x2,y2,maxout,nout,xout,yout,status)
 integer(ik),intent(in)::n1,n2,maxout
 real(rk),intent(in)::x1(n1),y1(n1),x2(n2),y2(n2)
 integer(ik),intent(out)::nout,status
 real(rk),intent(out)::xout(maxout),yout(maxout)
 integer::i,j
 real(rk)::dx1,dy1,dx2,dy2,den,rx,ry,t,u,xi,yi,scale
 logical::overlap
 status=RD_ERR_INPUT;nout=0
 if(n1<2.or.n2<2.or.maxout<0)return
 if(any(.not.(x1==x1)).or.any(.not.(y1==y1)).or.any(.not.(x2==x2)).or.any(.not.(y2==y2)))return
 xout=0; yout=0
 do i=1,n1-1
   dx1=x1(i+1)-x1(i);dy1=y1(i+1)-y1(i)
   do j=1,n2-1
     overlap=max(min(x1(i),x1(i+1)),min(x2(j),x2(j+1)))<=min(max(x1(i),x1(i+1)),max(x2(j),x2(j+1))) .and. &
             max(min(y1(i),y1(i+1)),min(y2(j),y2(j+1)))<=min(max(y1(i),y1(i+1)),max(y2(j),y2(j+1)))
     if(.not.overlap)cycle
     dx2=x2(j+1)-x2(j);dy2=y2(j+1)-y2(j)
     den=dx1*dy2-dy1*dx2
     scale=max(1._rk,abs(dx1*dy2),abs(dy1*dx2))
     ! np.linalg.solve rejects exactly singular/ill-conditioned segment systems.
     ! A machine-epsilon gate reproduces that fail-closed behavior without a
     ! Python dependency while retaining well-conditioned near intersections.
     if(abs(den)<=epsilon(1._rk)*scale)cycle
     rx=x2(j)-x1(i);ry=y2(j)-y1(i)
     t=(rx*dy2-ry*dx2)/den
     u=(rx*dy1-ry*dx1)/den
     if(t<0._rk.or.t>1._rk.or.u<0._rk.or.u>1._rk)cycle
     if(nout>=maxout)then;status=RD_ERR_INPUT;return;endif
     xi=x1(i)+t*dx1;yi=y1(i)+t*dy1
     nout=nout+1;xout(nout)=xi;yout(nout)=yi
   enddo
 enddo
 status=RD_OK
 end subroutine
end module rd_intersections
