import matplotlib
matplotlib.use("Agg",force=True)
import matplotlib.pyplot as plt
def plot_rotor(model,ax=None):
    ax=ax or plt.subplots()[1]
    z={n.number:n.z_m for n in model.nodes}
    for s in model.shafts:
        if hasattr(s,"outer_diameter_m"): width=s.outer_diameter_m
        else: width=max(s.outer_diameter_1_m,s.outer_diameter_2_m)
        ax.plot([z[s.node1],z[s.node2]],[0,0],linewidth=max(1,width*100))
    for d in model.disks: ax.axvline(z[d.node])
    for b in model.bearings: ax.plot(z[b.node],0,marker='v')
    ax.set_xlabel('z (m)');ax.set_yticks([]);return ax
