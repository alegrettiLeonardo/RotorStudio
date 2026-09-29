program test_api617_unbalance
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK
 use rd_api617_unbalance,only:api617_required_sizes,api617_full
 implicit none(type,external)
 integer(ik),parameter::nn=7,ns=6,nd=2,nb=2,nmodes=12,maxout=7
 real(rk)::z(nn),sh(11,ns),di(6,nd),be(34,nb),speed
 real(rk)::mag(maxout),phase(maxout),loads(maxout),modefreq
 real(rk)::ratio(nmodes/2),major(nn),kappa(nn),angle(nn),projection(nn),sgn(nn)
 integer(ik)::nout,nodes(maxout),modeidx,status,nphysical,required_out,i

 z=[0._rk,.25_rk,.5_rk,.75_rk,1._rk,1.25_rk,1.5_rk]
 sh=0._rk
 do i=1,ns
   sh(1,i)=2._rk;sh(2,i)=real(i,rk);sh(3,i)=real(i+1,rk)
   sh(4,i)=.05_rk;sh(5,i)=0._rk;sh(6,i)=7810._rk
   sh(7,i)=211.e9_rk;sh(8,i)=81.2e9_rk
 enddo

 di=0._rk
 di(:,1)=[1._rk,3._rk,7810._rk,.07_rk,.28_rk,.05_rk]
 di(:,2)=[1._rk,5._rk,7810._rk,.07_rk,.28_rk,.05_rk]

 be=0._rk
 be(1,1)=5._rk;be(2,1)=1._rk
 be(3,1)=1.e6_rk;be(6,1)=1.e6_rk;be(7,1)=1.e3_rk;be(10,1)=1.e3_rk
 be(1,2)=5._rk;be(2,2)=7._rk
 be(3,2)=1.e6_rk;be(6,2)=1.e6_rk;be(7,2)=1.e3_rk;be(10,2)=1.e3_rk

 speed=9000._rk*2._rk*acos(-1._rk)/60._rk

 call api617_required_sizes(nn,nmodes,nphysical,required_out,status)
 if(status/=RD_OK.or.nphysical/=6.or.required_out/=nn)stop 1

 call api617_full(nn,z,ns,sh,nd,di,nb,be,speed,0_ik,nmodes,maxout, &
                  nout,nodes,mag,phase,loads,modeidx,modefreq, &
                  ratio,major,kappa,angle,projection,sgn,status)
 if(status/=RD_OK)stop 2
 if(nout/=1)stop 3
 if(nodes(1)/=4)stop 4
 if(modeidx/=1)stop 5
 if(abs(mag(1)-1.2443432344562272e-4_rk)>2.e-11_rk)stop 6
 if(abs(loads(1)-88.18180401658304_rk)>2.e-5_rk)stop 7
 if(abs(phase(1))>1.e-10_rk)stop 8
 if(ratio(2)<=.25_rk)stop 9
 if(abs(maxval(major)-major(4))>1.e-7_rk*maxval(major))stop 10

 print *,'PASS: A7 native API 617 unbalance placement contract'
end program
