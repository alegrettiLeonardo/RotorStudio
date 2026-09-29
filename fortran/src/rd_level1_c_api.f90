module rd_level1_c_api
 use, intrinsic::iso_c_binding,only:c_int,c_double
 use rd_kinds,only:ik
 use rd_status,only:RD_ERR_INPUT
 use rd_level1,only:level1_required_sizes,level1_matrix,level1_full
 implicit none(type,external)
 private
 public::rd_level1_required_v1,rd_level1_matrix_v1,rd_level1_v1
contains
 integer(c_int) function rd_level1_required_v1(nnode,nq,nmodes,nstate) bind(C,name='rd_level1_required_v1')
 integer(c_int),value::nnode,nq
 integer(c_int),intent(out)::nmodes,nstate
 call level1_required_sizes(int(nnode,ik),int(nq,ik),nmodes,nstate,rd_level1_required_v1)
 end function

 integer(c_int) function rd_level1_matrix_v1(nn,z,ns,sh,nd,di,nb,be,speed,node,Q,M,C,G,K) bind(C,name='rd_level1_matrix_v1')
 integer(c_int),value::nn,ns,nd,nb,node
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd),be(34,nb)
 real(c_double),value::speed,Q
 real(c_double),intent(out)::M(4*nn,4*nn),C(4*nn,4*nn),G(4*nn,4*nn),K(4*nn,4*nn)
 call level1_matrix(nn,z,ns,sh,nd,di,nb,be,speed,node,Q,M,C,G,K,rd_level1_matrix_v1)
 end function

 integer(c_int) function rd_level1_v1(nn,z,ns,sh,nd,di,nb,be,speed,node,q0,q1,nq,nmode, &
                                      qgrid,selected_logdec,selected_mode,mode_dir,wr,wi,wn,wd,zeta,logdec) &
                                      bind(C,name='rd_level1_v1')
 integer(c_int),value::nn,ns,nd,nb,node,nq,nmode
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd),be(34,nb)
 real(c_double),value::speed,q0,q1
 real(c_double),intent(out)::qgrid(nq),selected_logdec(nq)
 integer(c_int),intent(out)::selected_mode(nq),mode_dir(nmode,nq)
 real(c_double),intent(out)::wr(nmode,nq),wi(nmode,nq),wn(nmode,nq),wd(nmode,nq),zeta(nmode,nq),logdec(nmode,nq)
 rd_level1_v1=RD_ERR_INPUT
 if(nmode<1.or.nq<2)return
 call level1_full(nn,z,ns,sh,nd,di,nb,be,speed,node,q0,q1,nq,nmode,qgrid,selected_logdec,selected_mode,mode_dir, &
                  wr,wi,wn,wd,zeta,logdec,rd_level1_v1)
 end function
end module rd_level1_c_api
