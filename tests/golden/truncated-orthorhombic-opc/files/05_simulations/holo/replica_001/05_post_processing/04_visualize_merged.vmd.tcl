mol new ../system.prmtop type parm7 waitfor all
mol addfile merged_protein.nc type netcdf waitfor all
display projection Orthographic
color Display Background white
mol modstyle 0 0 NewCartoon
