! Frozen ROSS ShaftElement.Kst / DiskElement.Kdt reduced to [x,y,alpha,beta].
module rd_transient_stiffness
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT
 use rd_dynamic_stiffness,only:build_dynamic_stiffness
 implicit none(type,external)
 private
 public::shaft_kst,disk_kdt,assemble_ksdt,speed_gradient,time_matrices
contains
 subroutine shaft_kst(L,od,id,rho,K,status)
 real(rk),intent(in)::L,od,id,rho
 real(rk),intent(out)::K(8,8)
 integer(ik),intent(out)::status
 real(rk)::factor
 status=RD_ERR_INPUT;K=0
 if(.not.all(ieee_is_finite([L,od,id,rho])))return
 if(L<=0.or.od<=id.or.id<0.or.rho<=0)return
 K(1,[2,3,6,7])=[-36._rk,3*L,36._rk,3*L]
 K(4,[2,3,6,7])=[-3*L,4*L**2,3*L,-L**2]
 K(5,[2,3,6,7])=[36._rk,-3*L,-36._rk,-3*L]
 K(8,[2,3,6,7])=[-3*L,-L**2,3*L,4*L**2]
 factor=rho*(acos(-1._rk)*(od**4-id**4)/64)/(15*L)
 K=K*factor
 if(.not.all(ieee_is_finite(K)))return
 status=RD_OK
 end subroutine
 subroutine disk_kdt(Ip,K,status)
 real(rk),intent(in)::Ip
 real(rk),intent(out)::K(4,4)
 integer(ik),intent(out)::status
 status=RD_ERR_INPUT;K=0
 if(.not.ieee_is_finite(Ip).or.Ip<0)return
 K(4,3)=Ip;status=RD_OK
 end subroutine
 subroutine assemble_ksdt(nn,z,ns,sh,nd,di,Ks,Kd,K,status)
 integer(ik),intent(in)::nn,ns,nd
 real(rk),intent(in)::z(nn),sh(11,ns),di(6,nd)
 real(rk),intent(out)::Ks(4*nn,4*nn),Kd(4*nn,4*nn),K(4*nn,4*nn)
 integer(ik),intent(out)::status
 real(rk)::ke(8,8),de(4,4),Ip
 integer::i,lo
 status=RD_ERR_INPUT
 if(nn<2.or.nn>128.or.ns/=nn-1.or.nd<0.or.nd>1024)return
 if(.not.all(ieee_is_finite(z)).or..not.all(ieee_is_finite(sh)).or..not.all(ieee_is_finite(di)))return
 Ks=0;Kd=0;K=0
 do i=1,ns
 status=RD_ERR_INPUT
 if(sh(1,i)/=2.or.sh(2,i)/=i.or.sh(3,i)/=i+1.or.any(sh(9:11,i)/=0))return
 call shaft_kst(z(i+1)-z(i),sh(4,i),sh(5,i),sh(6,i),ke,status)
 if(status/=RD_OK)return
 lo=4*(i-1)+1;Ks(lo:lo+7,lo:lo+7)=Ks(lo:lo+7,lo:lo+7)+ke
 enddo
 do i=1,nd
 status=RD_ERR_INPUT
 if(di(2,i)<1.or.di(2,i)>nn.or.di(2,i)/=nint(di(2,i)))return
 if(di(1,i)==1)then
 if(di(3,i)<=0.or.di(4,i)<=0.or.di(5,i)<=di(6,i).or.di(6,i)<0)return
 Ip=acos(-1._rk)*di(3,i)*di(4,i)*(di(5,i)**4-di(6,i)**4)/32
 elseif(di(1,i)==2)then
 Ip=di(5,i)
 else
 return
 endif
 call disk_kdt(Ip,de,status);if(status/=RD_OK)return
 lo=4*(nint(di(2,i))-1)+1;Kd(lo:lo+3,lo:lo+3)=Kd(lo:lo+3,lo:lo+3)+de
 enddo
 K=Ks+Kd
 if(.not.all(ieee_is_finite(K)))then;status=RD_ERR_INPUT;return;endif
 status=RD_OK
 end subroutine
 subroutine speed_gradient(nt,t,speed,alpha,status)
 integer(ik),intent(in)::nt
 real(rk),intent(in)::t(nt),speed(nt)
 real(rk),intent(out)::alpha(nt)
 integer(ik),intent(out)::status
 integer::i
 real(rk)::h1,h2,a,b,c
 status=RD_ERR_INPUT
 if(nt<2.or.nt>10000)return
 if(.not.all(ieee_is_finite(t)).or..not.all(ieee_is_finite(speed)))return
 if(any(t(2:)<=t(:nt-1)))return
 alpha(1)=(speed(2)-speed(1))/(t(2)-t(1));alpha(nt)=(speed(nt)-speed(nt-1))/(t(nt)-t(nt-1))
 do i=2,nt-1
 h1=t(i)-t(i-1);h2=t(i+1)-t(i)
 a=-h2/(h1*(h1+h2));b=(h2-h1)/(h1*h2);c=h1/(h2*(h1+h2))
 alpha(i)=a*speed(i-1)+b*speed(i)+c*speed(i+1)
 enddo
 if(.not.all(ieee_is_finite(alpha)))return
 status=RD_OK
 end subroutine
 subroutine time_matrices(nn,z,ns,sh,nd,di,nb,nodes,coeff,speed,alpha,M,C,G,K,S,Ce,Ke,Fg,status)
 integer(ik),intent(in)::nn,ns,nd,nb,nodes(nb)
 real(rk),intent(in)::z(nn),sh(11,ns),di(6,nd),coeff(12,nb),speed,alpha
 real(rk),intent(out)::M(4*nn,4*nn),C(4*nn,4*nn),G(4*nn,4*nn),K(4*nn,4*nn),S(4*nn,4*nn),Ce(4*nn,4*nn),Ke(4*nn,4*nn),Fg(4*nn)
 integer(ik),intent(out)::status
 real(rk),allocatable::Mb(:,:),Cb(:,:),Kb(:,:),Ks(:,:),Kd(:,:),gravity(:)
 complex(rk),allocatable::D(:,:)
 integer::n,err
 status=RD_ERR_INPUT
 if(nn<2.or.nn>128.or.ns/=nn-1.or.nd<0.or.nd>1024.or.nb<0.or.nb>2*nn)return
 if(.not.all(ieee_is_finite([speed,alpha])))return
 n=4*nn;allocate(Mb(n,n),Cb(n,n),Kb(n,n),Ks(n,n),Kd(n,n),D(n,n),gravity(n),stat=err);if(err/=0)return
 ! Zero excitation and speed in A2 builder returns base matrices with supplied coefficients.
 call build_dynamic_stiffness(nn,z,ns,sh,nd,di,nb,nodes,coeff,0._rk,0._rk,M,C,G,K,Mb,Cb,Kb,D,status)
 if(status/=RD_OK)return
 call assemble_ksdt(nn,z,ns,sh,nd,di,Ks,Kd,S,status);if(status/=RD_OK)return
 Ce=C+speed*G;Ke=K+alpha*S
 gravity=0;gravity(2:n:4)=-9.8065_rk;Fg=matmul(M,gravity)
 if(.not.all(ieee_is_finite(Ce)).or..not.all(ieee_is_finite(Ke)).or..not.all(ieee_is_finite(Fg)))then;status=RD_ERR_INPUT;return;endif
 status=RD_OK
 end subroutine
end module
