program test_newmark
 use rd_kinds,only:rk,ik
 use rd_newmark,only:newmark_step
 implicit none
 real(rk)::M(1,1),C(1,1),K(1,1),F(1),q(1),v(1),a(1),q0(1),v0(1),a0(1),res,ar,cond,dt,t,exact,error(3),zeta,wd
 integer(ik)::it,st
 integer::i,j,nt,mode
 M=2;K=200;dt=.001_rk
 ! Analytic undamped free, damped free, and constant-force step with consistent IC.
 do mode=1,4
 do j=1,3
 dt=.004_rk/2**(j-1);nt=nint(1._rk/dt)
 C=0;F=0;q0=1;v0=0;a0=-100
 if(mode==2)C=4
 if(mode==3)then;q0=0;a0=1;F=2;endif
 if(mode==4)then;q0=0;a0=0;endif
 error(j)=0
 do i=1,nt
 if(mode==4)F=2*sin(3*i*dt)
 call newmark_step(1_ik,M,C,K,F,dt,.5_rk,.25_rk,1e-10_rk,q0,v0,a0,q,v,a,it,res,ar,cond,st)
 if(st/=0.or.res>1e-12)stop 1
 t=i*dt;exact=cos(10*t)
 if(mode==2)then
 zeta=.1_rk;wd=10*sqrt(1-zeta*zeta)
 exact=exp(-t)*(cos(wd*t)+sin(wd*t)/wd)
 endif
 if(mode==4)exact=(sin(3*t)-.3_rk*sin(10*t))/91
 if(mode==3)exact=(1-cos(10*t))/100
 error(j)=max(error(j),abs(q(1)-exact));q0=q;v0=v;a0=a
 enddo
 enddo
 if(error(3)>error(2)/3.or.error(2)>error(1)/3)stop 2
 enddo
 ! Zero force is exact, including variable dt; singular J must still fail closed.
 M=1;C=0;K=1;F=0;q0=0;v0=0;a0=0
 do i=1,5
 call newmark_step(1_ik,M,C,K,F,.001_rk*i,.5_rk,.25_rk,1e-6_rk,q0,v0,a0,q,v,a,it,res,ar,cond,st)
 if(st/=0.or.any(q/=0).or.any(v/=0).or.any(a/=0).or.it/=0)stop 3
 enddo
 M=0;K=0
 call newmark_step(1_ik,M,C,K,F,.001_rk,.5_rk,.25_rk,1e-6_rk,q0,v0,a0,q,v,a,it,res,ar,cond,st)
 if(st/=30)stop 4
 print *, 'PASS: analytic free/damped/step/harmonic SDOF, dt refinement, zero and singular rejection'
end program
