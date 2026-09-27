module rd_time_response_general
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use, intrinsic::iso_fortran_env,only:int64
 use rd_kinds,only:rk,ik
 use rd_transient_stiffness,only:time_matrices,speed_gradient
 use rd_newmark,only:newmark_step
 implicit none(type,external)
 private
 public::general_time_response
contains
 subroutine general_time_response(nn,z,ns,sh,nd,di,nb,nodes,nt,t,speed,variable,coeff,F,weight,gamma,beta,tol,q,v,a,alpha,Fe,iterations,residual,absres,condition,failed_step,status)
 integer(ik),intent(in)::nn,ns,nd,nb,nt,nodes(nb),variable,weight
 real(rk),intent(in)::z(nn),sh(11,ns),di(6,nd),t(nt),speed(nt),coeff(12,nb,nt),F(4*nn,nt),gamma,beta,tol
 real(rk),intent(out)::q(4*nn,nt),v(4*nn,nt),a(4*nn,nt),alpha(nt),Fe(4*nn,nt),residual(nt),absres(nt),condition(nt)
 integer(ik),intent(out)::iterations(nt),failed_step,status
 real(rk),allocatable::M(:,:),Mt(:,:),C(:,:),G(:,:),K(:,:),S(:,:),Ce(:,:),Ke(:,:),Fg(:)
 integer::n,i,err
 integer(int64)::budget
 status=10;failed_step=0
 if(nn<2.or.nn>128.or.ns/=nn-1.or.nd<0.or.nd>1024.or.nb<0.or.nb>2*nn.or.nt<2.or.nt>10000)return
 n=4*nn;budget=320_int64*n*nt+240_int64*n*n
 if(budget>512_int64*1024*1024)return
 if((variable/=0.and.variable/=1).or.(weight/=0.and.weight/=1))return
 if(.not.all(ieee_is_finite(t)).or..not.all(ieee_is_finite(speed)).or..not.all(ieee_is_finite(F)).or..not.all(ieee_is_finite(coeff)))return
 if(any(t(2:)<=t(:nt-1)).or..not.all(ieee_is_finite([gamma,beta,tol])))return
 if(gamma<=0.or.beta<=0.or.tol<=0)return
 if(variable==0.and.any(speed/=speed(1)))return
 ! ROSS integrates one M=self.M() for the entire history. Varying bearing mass is unsupported.
 do i=2,nt
 if(any(coeff(1:4,:,i)/=coeff(1:4,:,1)))return
 enddo
 allocate(M(n,n),Mt(n,n),C(n,n),G(n,n),K(n,n),S(n,n),Ce(n,n),Ke(n,n),Fg(n),stat=err);if(err/=0)return
 q=0;v=0;a=0;iterations=0;residual=0;absres=0;condition=0;alpha=0;Fe=F
 if(variable==1)then
 call speed_gradient(nt,t,speed,alpha,status);if(status/=0)return
 endif
 call time_matrices(nn,z,ns,sh,nd,di,nb,nodes,coeff(:,:,1),speed(1),alpha(1),M,C,G,K,S,Ce,Ke,Fg,status)
 if(status/=0)return
 if(weight==1)then
 do i=1,nt
 Fe(:,i)=F(:,i)+Fg
 enddo
 endif
 if(.not.all(ieee_is_finite(Fe)))then;status=10;return;endif
 ! Prescribed zero initial q/v/a is NOT an equilibrium solve, even when F(t0) /= 0.
 absres(1)=norm2(Fe(:,1));if(any(Fe(:,1)/=0))residual(1)=1
 do i=2,nt
 failed_step=i
 call time_matrices(nn,z,ns,sh,nd,di,nb,nodes,coeff(:,:,i),speed(i),alpha(i),Mt,C,G,K,S,Ce,Ke,Fg,status)
 if(status/=0)return
 if(any(Mt/=M))then;status=10;return;endif
 call newmark_step(n,M,Ce,Ke,Fe(:,i),t(i)-t(i-1),gamma,beta,tol,q(:,i-1),v(:,i-1),a(:,i-1), &
 q(:,i),v(:,i),a(:,i),iterations(i),residual(i),absres(i),condition(i),status)
 if(status/=0)return
 enddo
 failed_step=0;status=0
 end subroutine
end module
