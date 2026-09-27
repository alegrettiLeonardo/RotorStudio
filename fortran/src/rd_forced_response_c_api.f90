module rd_forced_response_c_api
 use, intrinsic::iso_c_binding,only:c_int,c_double
 use rd_forced_response,only:forced_response,forced_size_valid
 use rd_status,only:RD_ERR_INPUT
 implicit none(type,external)
 private
 public::rd_forced_response_v1
contains
 integer(c_int) function rd_forced_response_v1(nn,z,ns,sh,nd,di,nb,nodes,nf,freq,policy,fixed,coeff,fd,ff,fr,fi,qr,qi,vr,vi,ar,ai,residual,condition) bind(C,name='rd_forced_response_v1')
 integer(c_int),value::nn,ns,nd,nb,nf,policy,fd,ff
 integer(c_int),intent(in)::nodes(nb)
 real(c_double),value::fixed
 real(c_double),intent(in)::z(nn),sh(11,ns),di(6,nd),freq(nf),coeff(12,nb,nf),fr(fd,ff),fi(fd,ff)
 real(c_double),intent(out)::qr(4*nn,nf),qi(4*nn,nf),vr(4*nn,nf),vi(4*nn,nf),ar(4*nn,nf),ai(4*nn,nf),residual(nf),condition(nf)
 rd_forced_response_v1=RD_ERR_INPUT
 if(.not.forced_size_valid(nn,nf))return
 if(fd/=4*nn.or.ff/=nf)return
 call forced_response(nn,z,ns,sh,nd,di,nb,nodes,nf,freq,policy,fixed,coeff,fd,ff,fr,fi,qr,qi,vr,vi,ar,ai,residual,condition,rd_forced_response_v1)
 end function
end module
