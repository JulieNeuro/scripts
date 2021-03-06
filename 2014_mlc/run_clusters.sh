## utils
find results -name "*_lock" | while read f ; do rm $f ; done
find results -name "*_run*" | while read f ; do rm $f ; done
find results -name beta.npy | while read f ; do gzip $f ; done


##
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
#print "CONESTA loop", i, "FISTA=",self.fista_info[Info.num_iter], "TOT iter:", self.num_iter

# On gabriel
mapreduce.py --mode map --config /neurospin/tmp/brainomics/2014_mlc/GM/config.json --ncore 2

# ON NS
mapreduce.py --mode map --config /neurospin/brainomics/2014_mlc/GM/config.json --ncore 1
scp /home/ed203246/git/pylearn-parsimony/parsimony/algorithms/explicit.py gabriel:/home/ed203246/git/pylearn-parsimony/parsimony/algorithms/explicit.py

################################################################################
python $HOME/git/scripts/2014_mlc/02_logistictvenet_gm_univ.py

# Start by running Locally with 2 cores, to check that everything os OK)
Interrupt after a while CTL-C
mapreduce.py --mode map --config /neurospin/brainomics/2014_mlc/GM_UNIV/config.json --ncore 2
# 1) Log on gabriel:
ssh -t gabriel.intra.cea.fr
# 2) Run one Job to test
qsub -I
cd /neurospin/tmp/brainomics/2014_mlc/GM_UNIV
./job_Global_long.pbs
# 3) Run on cluster
qsub job_Global_long.pbs
# 4) Log out and pull Pull
mapreduce.py --mode reduce --config /neurospin/tmp/brainomics/2014_mlc/GM_UNIV/config.json
exit
/neurospin/brainomics/2014_mlc/GM_UNIV/sync_pull.sh
# Reduce
mapreduce.py --mode reduce --config /neurospin/brainomics/2014_mlc/GM_UNIV/config.json

scp gabriel:/neurospin/tmp/brainomics/2014_mlc/GM_UNIV/results.csv .


################################################################################
python $HOME/git/scripts/2014_mlc/02_logistictvenet_gm_10cv.py

# Start by running Locally with 2 cores, to check that everything os OK)
Interrupt after a while CTL-C
mapreduce.py --mode map --config /neurospin/brainomics/2014_mlc/GM_10CV/config.json --ncore 2
# 1) Log on gabriel:
ssh -t gabriel.intra.cea.fr
# 2) Run one Job to test
qsub -I
cd /neurospin/tmp/brainomics/2014_mlc/GM_10CV
./job_Global_long.pbs
# 3) Run on cluster
qsub job_Global_long.pbs
# 4) Log out and pull Pull
exit
/neurospin/brainomics/2014_mlc/GM_10CV/sync_pull.sh
# Reduce
mapreduce.py --mode reduce --config /neurospin/brainomics/2014_mlc/GM_10CV/config.json



################################################################################
python $HOME/git/scripts/2014_mlc/02_logistic_gtvenet_gm_univ.py

# Start by running Locally with 2 cores, to check that everything os OK)
Interrupt after a while CTL-C
mapreduce.py --mode map --config /neurospin/brainomics/2014_mlc/GM_GTV/config.json --ncore 2
# 1) Log on gabriel:
ssh -t gabriel.intra.cea.fr
# 2) Run one Job to test
qsub -I
cd /neurospin/tmp/brainomics/2014_mlc/GM_GTV
./job_Global_long.pbs
# 3) Run on cluster
qsub job_Global_long.pbs
# 4) Log out and pull Pull
exit
/neurospin/brainomics/2014_mlc/GM_GTV/sync_pull.sh
# Reduce
mapreduce.py --mode reduce --config /neurospin/brainomics/2014_mlc/GM_GTV/config.json

###########################
fslview /tmp/sub.nii.gz /tmp/cort.nii.gz /tmp/merge.nii.gz         /tmp/atlas_smoothed.nii.gz /neurospin/brainomics/2014_mlc/gm_gtvenet/mask_atlas.nii.gz /neurospin/tmp/mlc2014/processed/binary/Train_Sbj100/mwrc1Train_Sbj100.nii.gz

# Start by running Locally with 2 cores, to check that everything os OK)
Interrupt after a while CTL-C
mapreduce.py --map --config /neurospin/brainomics/2014_mlc/gm_gtvenet/config.json --ncore 2
# 1) Log on gabriel:
ssh -t gabriel.intra.cea.fr
# 2) Run one Job to test
qsub -I
cd /neurospin/tmp/ed203246/gm_gtvenet
./job_Global_long.pbs
# 3) Run on cluster
qsub job_Global_long.pbs
# 4) Log out and pull Pull
exit
/neurospin/brainomics/2014_mlc/gm_gtvenet/sync_pull.sh
# Reduce
mapreduce.py --mode reduce --config /neurospin/brainomics/2014_mlc/gm_gtvenet/config.json

