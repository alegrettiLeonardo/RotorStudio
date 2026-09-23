import math
def rpm_to_rad_s(rpm:float)->float: return rpm*2*math.pi/60.0
def rad_s_to_rpm(w:float)->float: return w*60.0/(2*math.pi)
