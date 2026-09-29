module rd_rouch
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT
 implicit none(type,external)
 private
 public::rouch_mass
contains
 subroutine rouch_mass(nnode,M,G,Msync,status)
 integer(ik),intent(in)::nnode
 real(rk),intent(in)::M(4*nnode,4*nnode),G(4*nnode,4*nnode)
 real(rk),intent(out)::Msync(4*nnode,4*nnode)
 integer(ik),intent(out)::status
 integer::i,j,ndof,x,y,a,b
 status=RD_ERR_INPUT
 if(nnode<1)return
 ndof=4*nnode;Msync=M
 ! Exact 4-DOF form of frozen ROSS Rotor.M(..., synchronous=True).
 ! Applying the node-local coordinate rotation to the globally assembled G is
 ! algebraically identical to the element-by-element ROSS implementation,
 ! including disk gyroscopic terms.
 do i=1,ndof
   do j=1,nnode
     x=4*j-3;y=4*j-2;a=4*j-1;b=4*j
     select case(mod(i-1,4)+1)
     case(1,4) ! x or beta row
       Msync(i,x)=Msync(i,x)-G(i,y)
       Msync(i,b)=Msync(i,b)+G(i,a)
     case(2,3) ! y or alpha row
       Msync(i,y)=Msync(i,y)+G(i,x)
       Msync(i,a)=Msync(i,a)-G(i,b)
     end select
   enddo
 enddo
 status=RD_OK
 end subroutine
end module rd_rouch
