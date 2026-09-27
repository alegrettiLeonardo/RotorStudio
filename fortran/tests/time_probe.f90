! Validation-only file driver, before public time ABI integration.
program time_probe
 use rd_kinds,only:rk,ik
 use rd_time_response_general,only:general_time_response
 implicit none
 integer(ik)::nn,ns,nd,nb,nt,var,weight,failed,st
 integer::i,j
 real(rk)::gamma,beta,tol
 integer(ik),allocatable::nodes(:),it(:)
 real(rk),allocatable::z(:),sh(:,:),di(:,:),t(:),speed(:),coeff(:,:,:),F(:,:),q(:,:),v(:,:),a(:,:),alpha(:),Fe(:,:),res(:),ar(:),cond(:)
 read(*,*)nn,ns,nd,nb,nt,var,weight,gamma,beta,tol
 allocate(z(nn),sh(11,ns),di(6,nd),nodes(nb),t(nt),speed(nt),coeff(12,nb,nt),F(4*nn,nt),q(4*nn,nt),v(4*nn,nt),a(4*nn,nt),alpha(nt),Fe(4*nn,nt),it(nt),res(nt),ar(nt),cond(nt))
 read(*,*)z;read(*,*)sh;read(*,*)di;read(*,*)nodes;read(*,*)t;read(*,*)speed;read(*,*)coeff;read(*,*)F
 call general_time_response(nn,z,ns,sh,nd,di,nb,nodes,nt,t,speed,var,coeff,F,weight,gamma,beta,tol,q,v,a,alpha,Fe,it,res,ar,cond,failed,st)
 if(st/=0)then
 print *,st,failed;stop 1
 endif
 do i=1,nt
 do j=1,4*nn
 write(*,'(3ES26.17)')q(j,i),v(j,i),a(j,i)
 enddo
 enddo
end program
