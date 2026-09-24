# MATLAB V2 call graph

Inventory of all 28 MATLAB V2 functions from the authoritative archive. Edges below are direct calls to another V2 function; MATLAB builtins are omitted.

```text
bearasym       -> (none)
bearmtx        -> (none)
chr_asym       -> bearasym, rotorasym
chr_root       -> bearmtx, rotormtx, whirl
chr_root_coax  -> bearmtx, rotormtx
crit_spd       -> bearmtx, rotormtx
fftscale       -> (none)
freq_asym      -> bearasym, rotorasym
freq_aux       -> bearmtx, rotormtx
freq_fdn       -> bearmtx, rotormtx
freq_rsp       -> bearmtx, rotormtx
freq_rsp_coax  -> bearmtx, rotormtx
picrotor       -> (none)
plotcamp       -> (none)
ploteig        -> (none)
plotfrf        -> (none)
plotloci       -> (none)
plotmode       -> (none)
plotorbit      -> (none)
plotresp       -> whirl
rotorasym      -> shftasym
rotormtx       -> shftelem, taper
runup          -> bearmtx, rotormtx
shftasym       -> (none)
shftelem       -> (none)
taper          -> (none)
time_fdn       -> bearmtx, rotormtx
whirl          -> (none)
```

The architectural migration follows this graph: numerical leaves and assembly/analysis functions move to Fortran; `whirl`, `fftscale`, schematic/plotting and exports remain Python post-processing.
