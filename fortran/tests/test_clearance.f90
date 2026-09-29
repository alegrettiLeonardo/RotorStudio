program test_clearance
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK
 use rd_clearance,only:clearance_required_sizes,clearance_full
 implicit none(type,external)
 integer(ik),parameter::nn=7,ns=6,nd=2,nb=2,nf=13,npb=2,ncl=3,maxout=7
 real(rk)::z(nn),sh(11,ns),di(6,nd),coeff(12,nb,nf),be(34,nb),speed(nf)
 integer(ik)::bnodes(nb),pnode(npb),cnode(ncl),ubin(maxout),ubout(maxout),passed(ncl)
 real(rk)::pang(npb),radial(ncl),ubmi(maxout),ubpi(maxout),ubm(maxout),ubp(maxout)
 real(rk)::probe(npb,nf),diam(ncl),cr(ncl,nf),maxcr(ncl),spmax(ncl)
 real(rk)::avl,amax,scc,modefreq,nma,nmc,pi_,rpmstep
 integer(ik)::nout,modeidx,status,required,i,j

 pi_=acos(-1._rk)
 z=[0._rk,.25_rk,.5_rk,.75_rk,1._rk,1.25_rk,1.5_rk]
 sh=0._rk
 do i=1,ns
   sh(1,i)=2;sh(2,i)=i;sh(3,i)=i+1;sh(4,i)=.05_rk
   sh(6,i)=7810._rk;sh(7,i)=211.e9_rk;sh(8,i)=81.2e9_rk
 enddo
 di=0._rk
 di(:,1)=[1._rk,3._rk,7810._rk,.07_rk,.28_rk,.05_rk]
 di(:,2)=[1._rk,5._rk,7810._rk,.07_rk,.28_rk,.05_rk]

 bnodes=[1_ik,7_ik]
 be=0._rk
 do j=1,nb
   be(1,j)=5._rk;be(2,j)=bnodes(j)
   be(3,j)=1.e6_rk;be(6,j)=1.e6_rk;be(7,j)=1.e3_rk;be(10,j)=1.e3_rk
 enddo
 coeff=0._rk
 do i=1,nf
   do j=1,nb
     coeff(5,j,i)=1.e3_rk;coeff(8,j,i)=1.e3_rk
     coeff(9,j,i)=1.e6_rk;coeff(12,j,i)=1.e6_rk
   enddo
 enddo

 ! Sorted user sweep with Nma/Nmc inserted explicitly.
 speed=[0._rk,104.71975511965977_rk,209.43951023931953_rk,314.1592653589793_rk, &
        418.87902047863906_rk,523.5987755982989_rk,628.3185307179587_rk, &
        680.6784082777884_rk,733.0382858376184_rk,837.7580409572782_rk, &
        890.117918517108_rk,942.4777960769379_rk,1047.1975511965977_rk]
 nma=680.6784082777884_rk;nmc=890.117918517108_rk

 pnode=[1_ik,7_ik];pang=[pi_/4._rk,-pi_/4._rk]
 cnode=[1_ik,4_ik,7_ik];radial=[100e-6_rk,250e-6_rk,120e-6_rk]
 ubin=0;ubmi=0;ubpi=0

 call clearance_required_sizes(nn,nf,npb,ncl,required,status)
 if(status/=RD_OK.or.required/=nn)stop 1

 call clearance_full(nn,z,ns,sh,nd,di,nb,bnodes,coeff,be,nf,speed,nma,nmc, &
                     npb,pnode,pang,ncl,cnode,radial,0_ik,0_ik,ubin,ubmi,ubpi,0_ik,12_ik, &
                     0_ik,0._rk,maxout,nout,ubout,ubm,ubp,modeidx,modefreq,probe,avl,amax,scc, &
                     diam,cr,maxcr,spmax,passed,status)
 if(status/=RD_OK)stop 2
 if(nout/=1.or.ubout(1)/=4.or.modeidx/=1)stop 3
 if(abs(avl-25.4e-6_rk)>5e-14_rk)stop 4
 if(any(abs(diam-[200e-6_rk,500e-6_rk,240e-6_rk])>5e-14_rk))stop 5
 if(amax<=0._rk.or.scc<=0._rk)stop 6
 if(any(cr<0._rk).or.any(maxcr<=0._rk))stop 7
 if(any(passed<0).or.any(passed>1))stop 8

 ! Explicit-unbalance scaling must cancel in uncapped scaled clearance response.
 ubin(1)=4;ubmi(1)=20e-6_rk;ubpi(1)=0._rk
 call clearance_full(nn,z,ns,sh,nd,di,nb,bnodes,coeff,be,nf,speed,nma,nmc, &
                     npb,pnode,pang,ncl,cnode,radial,1_ik,1_ik,ubin,ubmi,ubpi,0_ik,12_ik, &
                     0_ik,0._rk,maxout,nout,ubout,ubm,ubp,modeidx,modefreq,probe,avl,amax,scc, &
                     diam,cr,maxcr,spmax,passed,status)
 if(status/=RD_OK.or.modeidx/=-1)stop 9
 if(abs(scc*amax-avl)>5e-13_rk)stop 10
 print *,'PASS: A8 native clearance force/probe/scaling/clearance contract'
end program
