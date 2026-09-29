module rd_time_response_c_api
 use, intrinsic::iso_c_binding,only:c_int,c_double
 use rd_transient_stiffness,only:shaft_kst,disk_kdt,assemble_ksdt,speed_gradient,time_matrices
 use rd_time_response_general,only:general_time_response
 use rd_status,only:RD_ERR_INPUT
 implicit none(type,external)
 private
 public::rd_transient_shaft_v1,rd_transient_disk_v1,rd_transient_stiffness_v1,rd_speed_gradient_v1,rd_time_matrices_v1
 public::rd_general_time_response_v1
contains
 integer(c_int) function rd_transient_shaft_v1(L,od,id,rho,K) bind(C,name='rd_transient_shaft_v1')
 real(c_double),value::L,od,id,rho
 real(c_double),intent(out)::K(8,8)
 call shaft_kst(L,od,id,rho,K,rd_transient_shaft_v1)
 end function
 integer(c_int) function rd_transient_disk_v1(Ip,K) bind(C,name='rd_transient_disk_v1')
 real(c_double),value::Ip
 real(c_double),intent(out)::K(4,4)
 call disk_kdt(Ip,K,rd_transient_disk_v1)
 end function
 integer(c_int) function rd_transient_stiffness_v1(nn,z,ns,sh,nd,di,Ks,Kd,K) bind(C,name='rd_transient_stiffness_v1')
 integer(c_int),value::nn,ns,nd
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd)
 real(c_double),intent(out)::Ks(4*nn,4*nn),Kd(4*nn,4*nn),K(4*nn,4*nn)
 call assemble_ksdt(nn,z,ns,sh,nd,di,Ks,Kd,K,rd_transient_stiffness_v1)
 end function
 integer(c_int) function rd_speed_gradient_v1(nt,t,speed,alpha) bind(C,name='rd_speed_gradient_v1')
 integer(c_int),value::nt
 real(c_double),intent(in)::t(nt),speed(nt)
 real(c_double),intent(out)::alpha(nt)
 call speed_gradient(nt,t,speed,alpha,rd_speed_gradient_v1)
 end function
 integer(c_int) function rd_time_matrices_v1(nn,z,ns,sh,nd,di,nb,nodes,coeff,speed,alpha,M,C,G,K,S,Ce,Ke,Fg) bind(C,name='rd_time_matrices_v1')
 integer(c_int),value::nn,ns,nd,nb
 integer(c_int),intent(in)::nodes(nb)
 real(c_double),value::speed,alpha
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd),coeff(12,nb)
 real(c_double),intent(out)::M(4*nn,4*nn),C(4*nn,4*nn),G(4*nn,4*nn),K(4*nn,4*nn),S(4*nn,4*nn),Ce(4*nn,4*nn),Ke(4*nn,4*nn),Fg(4*nn)
 call time_matrices(nn,z,ns,sh,nd,di,nb,nodes,coeff,speed,alpha,M,C,G,K,S,Ce,Ke,Fg,rd_time_matrices_v1)
 end function
 integer(c_int) function rd_general_time_response_v1(nn,z,ns,sh,nd,di,nb,nodes,nt,t,speed,variable,coeff,fd,ft,F,weight,gamma,beta,tol,q,v,a,alpha,Fe,iterations,residual,absres,condition,failed_step) bind(C,name='rd_general_time_response_v1')
 integer(c_int),value::nn,ns,nd,nb,nt,variable,fd,ft,weight
 integer(c_int),intent(in)::nodes(nb)
 real(c_double),value::gamma,beta,tol
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd),t(nt),speed(nt),coeff(12,nb,nt),F(fd,ft)
 real(c_double),intent(out)::q(4*nn,nt),v(4*nn,nt),a(4*nn,nt),alpha(nt),Fe(4*nn,nt),residual(nt),absres(nt),condition(nt)
 integer(c_int),intent(out)::iterations(nt),failed_step
 rd_general_time_response_v1=RD_ERR_INPUT;failed_step=0
 if(nn<2.or.nn>128.or.fd/=4*nn.or.ft/=nt)return
 call general_time_response(nn,z,ns,sh,nd,di,nb,nodes,nt,t,speed,variable,coeff,F,weight,gamma,beta,tol,q,v,a,alpha,Fe,iterations,residual,absres,condition,failed_step,rd_general_time_response_v1)
 end function
end module
