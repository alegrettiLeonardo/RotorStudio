program test_ucs
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK
 use rd_ucs,only:ucs_logspace,ucs_required_sizes
 use rd_intersections,only:curve_intersections
 implicit none
 real(rk)::g(5),x1(5),y1(5),x2(5),y2(5),xo(16),yo(16)
 integer(ik)::st,nb,mi,ncm,nout
 call ucs_logspace(6._rk,10._rk,5_ik,g,st)
 if(st/=RD_OK)stop 1
 if(maxval(abs(g-[1e6_rk,1e7_rk,1e8_rk,1e9_rk,1e10_rk]))>1e-4_rk)stop 2
 if(any(g(2:)<=g(:4)))stop 3
 call ucs_required_sizes(5_ik,16_ik,2_ik,30_ik,nb,mi,ncm,st)
 if(st/=RD_OK.or.nb/=4.or.mi/=4*2*4*29.or.ncm/=6)stop 4
 ! Multiple intersections: preserve authority generation order.
 x1=[0._rk,1._rk,2._rk,3._rk,4._rk];y1=[0._rk,2._rk,0._rk,2._rk,0._rk]
 x2=x1;y2=1._rk
 call curve_intersections(5_ik,x1,y1,5_ik,x2,y2,16_ik,nout,xo,yo,st)
 if(st/=RD_OK.or.nout/=4)stop 5
 if(maxval(abs(xo(:4)-[.5_rk,1.5_rk,2.5_rk,3.5_rk]))>1e-12_rk)stop 6
 if(maxval(abs(yo(:4)-1._rk))>1e-12_rk)stop 7

 ! A crossing exactly at segment endpoints is emitted once per intersecting
 ! segment pair by frozen ross.utils.intersection(): four coincident points.
 x1(:3)=[0._rk,1._rk,2._rk];y1(:3)=[0._rk,1._rk,2._rk]
 x2(:3)=[0._rk,1._rk,2._rk];y2(:3)=[2._rk,1._rk,0._rk]
 call curve_intersections(3_ik,x1,y1,3_ik,x2,y2,16_ik,nout,xo,yo,st)
 if(st/=RD_OK.or.nout/=4)stop 8
 if(maxval(abs(xo(:4)-1._rk))>1e-12_rk.or.maxval(abs(yo(:4)-1._rk))>1e-12_rk)stop 9

 ! No intersection.
 x1(:3)=[0._rk,1._rk,2._rk];y1(:3)=0._rk
 x2(:3)=[0._rk,1._rk,2._rk];y2(:3)=2._rk
 call curve_intersections(3_ik,x1,y1,3_ik,x2,y2,16_ik,nout,xo,yo,st)
 if(st/=RD_OK.or.nout/=0)stop 10

 ! Single endpoint intersection retained exactly once for this geometry.
 x1(:3)=[0._rk,1._rk,2._rk];y1(:3)=[0._rk,1._rk,0._rk]
 x2(:3)=[1._rk,2._rk,3._rk];y2(:3)=[1._rk,2._rk,3._rk]
 call curve_intersections(3_ik,x1,y1,3_ik,x2,y2,16_ik,nout,xo,yo,st)
 if(st/=RD_OK.or.nout/=1)stop 11
 if(abs(xo(1)-1._rk)>1e-12_rk.or.abs(yo(1)-1._rk)>1e-12_rk)stop 12

 ! Near-parallel non-intersecting authority sentinel.
 x1(:3)=[0._rk,1._rk,2._rk];y1(:3)=[0._rk,1._rk,2._rk]
 x2(:3)=[0._rk,1._rk,2._rk]
 y2(:3)=[1e-10_rk,1._rk+1e-10_rk,2._rk+2e-10_rk]
 call curve_intersections(3_ik,x1,y1,3_ik,x2,y2,16_ik,nout,xo,yo,st)
 if(st/=RD_OK.or.nout/=0)stop 13

 print *,'PASS: A5 logspace, safe sizes and all frozen ROSS intersection sentinels'
end program
