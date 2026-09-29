module rd_api617_unbalance_c_api
 use, intrinsic::iso_c_binding,only:c_int,c_double
 use rd_status,only:RD_ERR_INPUT
 use rd_api617_unbalance,only:api617_required_sizes,api617_full
 implicit none(type,external)
 private
 public::rd_api617_unbalance_required_v1,rd_api617_unbalance_v1
contains
 integer(c_int) function rd_api617_unbalance_required_v1(nnode,num_modes,nphysical,max_unbalance) &
   bind(C,name='rd_api617_unbalance_required_v1')
 integer(c_int),value::nnode,num_modes
 integer(c_int),intent(out)::nphysical,max_unbalance
 call api617_required_sizes(nnode,num_modes,nphysical,max_unbalance,rd_api617_unbalance_required_v1)
 end function

 integer(c_int) function rd_api617_unbalance_v1(nn,z,ns,sh,nd,di,nb,be,speed,forward_mode,num_modes,maxout, &
                                                nout,nodes,magnitude,phase,static_load,mode_index,mode_frequency, &
                                                whirl_ratio,major,kappa,major_angle,projection_real,sign_out) &
                                                bind(C,name='rd_api617_unbalance_v1')
 integer(c_int),value::nn,ns,nd,nb,forward_mode,num_modes,maxout
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd),be(34,nb)
 real(c_double),value::speed
 integer(c_int),intent(out)::nout,nodes(maxout),mode_index
 real(c_double),intent(out)::magnitude(maxout),phase(maxout),static_load(maxout),mode_frequency
 real(c_double),intent(out)::whirl_ratio(num_modes/2),major(nn),kappa(nn),major_angle(nn),projection_real(nn),sign_out(nn)
 rd_api617_unbalance_v1=RD_ERR_INPUT;nout=0
 call api617_full(nn,z,ns,sh,nd,di,nb,be,speed,forward_mode,num_modes,maxout,nout,nodes,magnitude,phase,static_load, &
                  mode_index,mode_frequency,whirl_ratio,major,kappa,major_angle,projection_real,sign_out, &
                  rd_api617_unbalance_v1)
 end function
end module rd_api617_unbalance_c_api
