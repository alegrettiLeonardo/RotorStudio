program test_level1
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK
 use rd_level1,only:level1_required_sizes,level1_full,level1_matrix
 implicit none(type,external)
 integer(ik),parameter::nn=7,ns=6,nd=2,nb=2,nq=5
 real(rk)::z(nn),sh(11,ns),di(6,nd),be(34,nb),q(nq),sel(nq)
 real(rk)::wr(6,nq),wi(6,nq),wn(6,nq),wd(6,nq),ze(6,nq),ld(6,nq)
 real(rk)::M(4*nn,4*nn),C(4*nn,4*nn),G(4*nn,4*nn),K(4*nn,4*nn)
 integer(ik)::sm(nq),dirs(6,nq),st,nm,nstate,i
 z=[0._rk,.25_rk,.5_rk,.75_rk,1._rk,1.25_rk,1.5_rk]
 sh=0
 do i=1,ns
   sh(1,i)=2;sh(2,i)=i;sh(3,i)=i+1
   sh(4,i)=.05_rk;sh(5,i)=0;sh(6,i)=7810;sh(7,i)=211e9_rk;sh(8,i)=81.2e9_rk
 enddo
 di=0
 di(:,1)=[2._rk,3._rk,15._rk,.08_rk,.14_rk,0._rk]
 di(:,2)=[2._rk,5._rk,12._rk,.06_rk,.11_rk,0._rk]
 be=0
 be(1,1)=5;be(2,1)=1;be(3,1)=1e6_rk;be(6,1)=.8e6_rk;be(7,1)=180;be(10,1)=140
 be(1,2)=5;be(2,2)=7;be(3,2)=1e6_rk;be(6,2)=.8e6_rk;be(7,2)=180;be(10,2)=140
 call level1_required_sizes(nn,nq,nm,nstate,st)
 if(st/=RD_OK.or.nm/=6.or.nstate/=56)stop 1
 call level1_full(nn,z,ns,sh,nd,di,nb,be,377._rk,4_ik,0._rk,2.5e6_rk,nq,6_ik, &
                  q,sel,sm,dirs,wr,wi,wn,wd,ze,ld,st)
 if(st/=RD_OK)stop 2
 if(abs(q(1))>1e-12_rk.or.abs(q(nq)-2.5e6_rk)>1e-6_rk)stop 3
 if(any(sm<1).or.any(sm>6))stop 4
 if(any(dirs<1).or.any(dirs>3))stop 5
 if(any(.not.(sel==sel)))stop 6
 call level1_matrix(nn,z,ns,sh,nd,di,nb,be,377._rk,4_ik,1e6_rk,M,C,G,K,st)
 if(st/=RD_OK)stop 7
 if(abs((K(13,14)-K(14,13))-2e6_rk)<1e5_rk)then
   ! Base matrices may already contain skew terms only through damping/G, not K.
 else
   stop 8
 endif
 print *,'PASS: A6 Level 1 native sizing, sweep, directions and cross-coupling'
end program
