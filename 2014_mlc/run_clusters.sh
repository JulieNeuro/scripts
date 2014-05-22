python $HOME/git/scripts/2014_mlc/02_logistictvenet_gm.py

Interrupt after a while CTL-C
mapreduce.py --mode map --config /neurospin/brainomics/2014_mlc/GM/config.json --ncore 2
# 1) Log on gabriel:
ssh -t gabriel.intra.cea.fr
# 2) Run one Job to test
qsub -I
cd /neurospin/tmp/brainomics/2014_mlc/GM
./job_Global_long.pbs
# 3) Run on cluster
qsub job_Global_long.pbs
# 4) Log out and pull Pull
exit
/neurospin/brainomics/2014_mlc/GM/sync_pull.sh
# Reduce
mapreduce.py --mode reduce --config /neurospin/brainomics/2014_mlc/GM/config.json

