import math
import numpy as np
_COUNTS={1:(0,),2:(0,),3:(4,),4:(8,),5:(8,),6:(32,),7:(5,6),8:(6,),9:(12,),10:(12,),20:(5,)}
def meaningful_properties(b):
    vals=tuple(float(x) for x in b.properties);allowed=_COUNTS.get(b.bearing_type)
    if allowed is None:return vals
    if len(vals)<min(allowed):raise ValueError(f"type {b.bearing_type}: expected property count {allowed}, received {len(vals)}")
    mx=max(allowed)
    if len(vals)>mx and any(abs(x)>0 for x in vals[mx:]):raise ValueError(f"type {b.bearing_type}: nonzero padding beyond K/C contract")
    n=max(n for n in allowed if n<=len(vals));vals=vals[:n]
    if not all(math.isfinite(x) for x in vals):raise ValueError("K/C properties must be finite")
    return vals
def bearing_kc_matrices(b):
    p=meaningful_properties(b);K=np.zeros((4,4));C=np.zeros((4,4));t=b.bearing_type
    if t in (1,2):return K,C
    if t==3:K[0,0],K[1,1]=p[:2];C[0,0],C[1,1]=p[2:4]
    elif t==4:K[np.diag_indices(4)]=p[:4];C[np.diag_indices(4)]=p[4:8]
    elif t==5:K[:2,:2]=np.asarray(p[:4]).reshape(2,2);C[:2,:2]=np.asarray(p[4:8]).reshape(2,2)
    elif t==6:K[:]=np.asarray(p[:16]).reshape(4,4);C[:]=np.asarray(p[16:32]).reshape(4,4)
    elif t in (9,10):K[:2,:2]=np.asarray(p[:4]).reshape(2,2);C[:2,:2]=np.asarray(p[4:8]).reshape(2,2)
    else:raise ValueError(f"type {t}: no constant single-node K/C contract")
    return K,C
def validate_bearing_contract(b):
    p=meaningful_properties(b);t=b.bearing_type
    if t==3 and (any(x<0 for x in p[:2]) or any(x<0 for x in p[2:4])):raise ValueError("type 3 direct K/C must be >=0")
    if t==4 and (any(x<0 for x in p[:4]) or any(x<0 for x in p[4:8])):raise ValueError("type 4 direct K/C must be >=0")
    if t==7:
        F,D,L,c,eta=p[:5]
        if F<0 or min(D,L,c,eta)<=0:raise ValueError("type 7 expects F>=0 and D,L,c,eta>0")
    if t==8:
        P,R,L,c,V,fric=p[:6]
        if P<0 or min(R,L,c,V,fric)<=0:raise ValueError("type 8 seal expects P>=0 and R,L,c,V,fric>0")


def bearing_kcm_matrices(b):
    """Return constant single-node K/C/M matrices.

    Type 9 is the additive B19 translational K/C/M bridge. Existing legacy
    bearing contracts remain unchanged.
    """
    p=meaningful_properties(b)
    K,C=bearing_kc_matrices(b)
    M=np.zeros((4,4))
    if b.bearing_type in (9,10):
        M[:2,:2]=np.asarray(p[8:12]).reshape(2,2)
    return K,C,M
