module rd_dynamic_stiffness
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
 use rd_assembly_stationary,only:assemble_rotor
 implicit none(type,external)
 private
 public::build_dynamic_stiffness
contains
 subroutine build_dynamic_stiffness(nn,z,ns,sh,nd,di,nb,nodes,coeff,speed,w,M,C,G,K,Mb,Cb,Kb,D,status)
 integer(ik),intent(in)::nn,ns,nd,nb,nodes(nb)
 real(rk),intent(in)::z(nn),sh(11,ns),di(6,nd),coeff(12,nb),speed,w
 real(rk),intent(out)::M(4*nn,4*nn),C(4*nn,4*nn),G(4*nn,4*nn),K(4*nn,4*nn),Mb(4*nn,4*nn),Cb(4*nn,4*nn),Kb(4*nn,4*nn)
 complex(rk),intent(out)::D(4*nn,4*nn)
 integer(ik),intent(out)::status
 real(rk),allocatable::K1(:,:)
 integer::i,j,col,a,b,err
 status=RD_ERR_INPUT
 if(nn<2.or.nn>128.or.ns/=nn-1.or.nd<0.or.nd>1024.or.nb<0.or.nb>2*nn)return
 if(.not.all(ieee_is_finite(z)).or..not.all(ieee_is_finite(sh)).or..not.all(ieee_is_finite(di)))return
 if(.not.all(ieee_is_finite(coeff)).or..not.ieee_is_finite(speed).or..not.ieee_is_finite(w))return
 if(w<0.or.any(z(2:)<=z(:nn-1)))return
 do i=1,ns
  if(sh(1,i)/=2.or.any(sh(9:11,i)/=0))then;status=RD_ERR_UNSUPPORTED;return;endif
  if(sh(2,i)/=i.or.sh(3,i)/=i+1.or.sh(4,i)<=sh(5,i).or.sh(5,i)<0.or.any(sh(6:8,i)<=0))return
 enddo
 do i=1,nd
  if(di(1,i)/=1.and.di(1,i)/=2)then;status=RD_ERR_UNSUPPORTED;return;endif
  if(di(2,i)<1.or.di(2,i)>nn)return
  if(di(2,i)/=nint(di(2,i)).or.di(3,i)<=0)return
  if(di(1,i)==1)then
   if(di(4,i)<=0.or.di(5,i)<=di(6,i).or.di(6,i)<0)return
  else
   if(any(di(4:5,i)<0))return
  endif
 enddo
 if(any(nodes<1).or.any(nodes>nn))return
 allocate(K1(4*nn,4*nn),stat=err);if(err/=0)return
 call assemble_rotor(nn,z,ns,sh,nd,di,M,C,G,K,K1,status)
 if(status/=RD_OK)return
 Mb=0;Cb=0;Kb=0
 do i=1,nb
  do col=1,2;do j=1,2
   a=4*(nodes(i)-1)+j;b=4*(nodes(i)-1)+col
   Mb(a,b)=Mb(a,b)+coeff(j+2*(col-1),i)
   Cb(a,b)=Cb(a,b)+coeff(4+j+2*(col-1),i)
   Kb(a,b)=Kb(a,b)+coeff(8+j+2*(col-1),i)
  enddo;enddo
 enddo
 M=M+Mb;C=C+Cb;K=K+Kb+speed*K1
 D=cmplx(K-w*w*M,w*(C+speed*G),rk)
 if(.not.all(ieee_is_finite(real(D))).or..not.all(ieee_is_finite(aimag(D))))status=RD_ERR_INPUT
 end subroutine
end module
