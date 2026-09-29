module rd_ucs_c_api
 use, intrinsic::iso_c_binding,only:c_int,c_double
 use rd_ucs,only:ucs_required_sizes,ucs_map,ucs_matrix,ucs_full
 use rd_status,only:RD_ERR_INPUT
 implicit none(type,external)
 private
 public::rd_ucs_required_v1,rd_ucs_map_v1,rd_ucs_matrix_v1,rd_ucs_v1
contains
 integer(c_int) function rd_ucs_required_v1(nk,num_modes,ncoeff,nbspeed,nbranch,maxint,ncritmode) bind(C,name='rd_ucs_required_v1')
 integer(c_int),value::nk,num_modes,ncoeff,nbspeed
 integer(c_int),intent(out)::nbranch,maxint,ncritmode
 call ucs_required_sizes(nk,num_modes,ncoeff,nbspeed,nbranch,maxint,ncritmode,rd_ucs_required_v1)
 end function
 integer(c_int) function rd_ucs_map_v1(nn,z,ns,sh,nd,di,nsupport,nodes,start_exp,stop_exp,nk,num_modes,synchronous,nbranch,grid,wn) bind(C,name='rd_ucs_map_v1')
 integer(c_int),value::nn,ns,nd,nsupport,nk,num_modes,synchronous,nbranch
 integer(c_int),intent(in)::nodes(nsupport)
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd)
 real(c_double),value::start_exp,stop_exp
 real(c_double),intent(out)::grid(nk),wn(nbranch,nk)
 rd_ucs_map_v1=RD_ERR_INPUT
 if(nbranch/=num_modes/4)return
 call ucs_map(nn,z,ns,sh,nd,di,nsupport,nodes,start_exp,stop_exp,nk,num_modes,synchronous,grid,wn,rd_ucs_map_v1)
 end function
 integer(c_int) function rd_ucs_matrix_v1(nn,z,ns,sh,nd,di,nsupport,nodes,k,synchronous,M,C,G,Kout) bind(C,name='rd_ucs_matrix_v1')
 integer(c_int),value::nn,ns,nd,nsupport,synchronous
 integer(c_int),intent(in)::nodes(nsupport)
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd)
 real(c_double),value::k
 real(c_double),intent(out)::M(4*nn,4*nn),C(4*nn,4*nn),G(4*nn,4*nn),Kout(4*nn,4*nn)
 call ucs_matrix(nn,z,ns,sh,nd,di,nsupport,nodes,k,synchronous,M,C,G,Kout,rd_ucs_matrix_v1)
 end function
 integer(c_int) function rd_ucs_v1(nn,z,ns,sh,nd,di,nsupport,nodes,start_exp,stop_exp,nk,num_modes,synchronous, &
                                   nbspeed,bs,kxx,kyy,ncoeff,nbranch,maxint,grid,wn,nint,ikcrit,ispeed,imode,isource, &
                                   cer,cei,cwn,cwd,czeta,clogdec) bind(C,name='rd_ucs_v1')
 integer(c_int),value::nn,ns,nd,nsupport,nk,num_modes,synchronous,nbspeed,ncoeff,nbranch,maxint
 integer(c_int),intent(in)::nodes(nsupport)
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd),bs(nbspeed),kxx(nbspeed),kyy(nbspeed)
 real(c_double),value::start_exp,stop_exp
 real(c_double),intent(out)::grid(nk),wn(nbranch,nk),ikcrit(maxint),ispeed(maxint)
 integer(c_int),intent(out)::nint,imode(maxint),isource(maxint)
 real(c_double),intent(out)::cer(6,maxint),cei(6,maxint),cwn(6,maxint),cwd(6,maxint),czeta(6,maxint),clogdec(6,maxint)
 rd_ucs_v1=RD_ERR_INPUT;nint=0
 if(nbranch/=num_modes/4)return
 call ucs_full(nn,z,ns,sh,nd,di,nsupport,nodes,start_exp,stop_exp,nk,num_modes,synchronous,nbspeed,bs,kxx,kyy,ncoeff,maxint, &
               grid,wn,nint,ikcrit,ispeed,imode,isource,cer,cei,cwn,cwd,czeta,clogdec,rd_ucs_v1)
 end function
end module rd_ucs_c_api
