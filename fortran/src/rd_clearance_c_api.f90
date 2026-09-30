module rd_clearance_c_api
 use, intrinsic::iso_c_binding,only:c_int,c_double
 use rd_status,only:RD_ERR_INPUT
 use rd_clearance,only:clearance_required_sizes,clearance_full
 implicit none(type,external)
 private
 public::rd_clearance_required_v1,rd_clearance_v1
contains
 integer(c_int) function rd_clearance_required_v1(nnode,nf,nprobe,nclear,max_unbalance) bind(C,name='rd_clearance_required_v1')
 integer(c_int),value::nnode,nf,nprobe,nclear
 integer(c_int),intent(out)::max_unbalance
 call clearance_required_sizes(nnode,nf,nprobe,nclear,max_unbalance,rd_clearance_required_v1)
 end function

 integer(c_int) function rd_clearance_v1(nn,z,ns,sh,nd,di,nb,bnodes,coeff,be_nmc,nf,speed,nma,nmc, &
                                        nprobe,probe_nodes,probe_angles,nclear,clear_nodes,radial_clearance, &
                                        explicit_ub,nub_in,ub_nodes_in,ub_mag_in,ub_phase_in,mode,num_modes, &
                                        cap_enabled,cap,maxout,nout,ub_nodes,ub_mag,ub_phase,mode_index,mode_frequency, &
                                        probe_response,vibration_limit,max_probe_amplitude,scale_factor, &
                                        diametral_clearance,clearance_response,max_clearance_response,speed_at_max,passed) &
                                        bind(C,name='rd_clearance_v1')
 integer(c_int),value::nn,ns,nd,nb,nf,nprobe,nclear,explicit_ub,nub_in,mode,num_modes,cap_enabled,maxout
 integer(c_int),intent(in)::bnodes(nb),probe_nodes(nprobe),clear_nodes(nclear),ub_nodes_in(maxout)
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd),coeff(12,nb,nf),be_nmc(34,nb),speed(nf)
 real(c_double),value::nma,nmc,cap
 real(c_double),intent(in)::probe_angles(nprobe),radial_clearance(nclear),ub_mag_in(maxout),ub_phase_in(maxout)
 integer(c_int),intent(out)::nout,ub_nodes(maxout),mode_index,passed(nclear)
 real(c_double),intent(out)::ub_mag(maxout),ub_phase(maxout),mode_frequency
 real(c_double),intent(out)::probe_response(nprobe,nf),vibration_limit,max_probe_amplitude,scale_factor
 real(c_double),intent(out)::diametral_clearance(nclear),clearance_response(nclear,nf),max_clearance_response(nclear),speed_at_max(nclear)
 rd_clearance_v1=RD_ERR_INPUT
 call clearance_full(nn,z,ns,sh,nd,di,nb,bnodes,coeff,be_nmc,nf,speed,nma,nmc,nprobe,probe_nodes,probe_angles, &
                     nclear,clear_nodes,radial_clearance,explicit_ub,nub_in,ub_nodes_in,ub_mag_in,ub_phase_in,mode,num_modes, &
                     cap_enabled,cap,maxout,nout,ub_nodes,ub_mag,ub_phase,mode_index,mode_frequency,probe_response, &
                     vibration_limit,max_probe_amplitude,scale_factor,diametral_clearance,clearance_response, &
                     max_clearance_response,speed_at_max,passed,rd_clearance_v1)
 end function
end module rd_clearance_c_api
