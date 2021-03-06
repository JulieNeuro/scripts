#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 21 12:08:33 2017

@author: ad247405
"""


import os
import numpy as np
import pandas as pd
import nibabel as nb
import shutil
import scipy.stats
import matplotlib.pyplot as plt
import seaborn as sns
import parsimony.utils.check_arrays as check_arrays
from sklearn import preprocessing
from nibabel import gifti
from sklearn.cluster import KMeans


##############################################################################
y_all = np.load("/neurospin/brainomics/2016_schizConnect/analysis/all_studies+VIP/VBM/all_subjects/data/y.npy")

pop_all = pd.read_csv("/neurospin/brainomics/2016_schizConnect/2018_analysis_2ndpart_clinic/results/clustering_based_on_predictive_markers/data/pop_all.csv")
site = np.load("/neurospin/brainomics/2016_schizConnect/analysis/all_studies+VIP/VBM/all_subjects/data/site.npy")

features_name = ['cluster1_cingulate_gyrus', 'cluster2_right_caudate_putamen',
       'cluster3_precentral_postcentral_gyrus', 'cluster4_frontal_pole',
       'cluster5_temporal_pole', 'cluster6_left_hippocampus_amygdala',
       'cluster7_left_caudate_putamen', 'cluster8_left_thalamus',
       'cluster9_right_thalamus', 'cluster10_middle_temporal_gyrus']
features = pop_all[features_name].as_matrix()



features = scipy.stats.zscore(features)


features_scz = features[y_all==1,:]
features_con = features[y_all==0,:]


mod = KMeans(n_clusters=2)
mod.fit(features_scz[:,:])
#mod.fit(U_all_scz[:,[2,3,4,5,8,9]])

labels_all_scz = mod.labels_

df = pd.DataFrame()
df["labels"] = labels_all_scz
df["age"] = pop_all["age"].values[y_all==1]

i=0
for f in features_name:
    df[f] = features_scz[:,i]
    i= i+1


output = "/neurospin/brainomics/2016_schizConnect/2018_analysis_2ndpart_clinic/\
results/clustering_based_on_predictive_markers/results/non_corrected_results/2_clusters"
np.save(os.path.join(output,"labels_cluster.npy"),labels_all_scz)

#############################################################################
#PLOT WEIGHTS OF PC FOR EACH CLUSTER
df_complete = pd.DataFrame()
df_complete["Feature"] = 99
df_complete["score"] = 99

ind = 0
for i in (df.index.values):
    for k in features_name :
        df_complete = df_complete.append(df[df.index==i][['labels', 'age']],ignore_index=True)
        df_complete.loc[df_complete.index==ind,"Feature"] = k
        df_complete.loc[df_complete.index==ind,"score"] = df[df.index==i][k].values
        ind = ind +1

fig = plt.figure()
fig.set_size_inches(11.7, 8.27)
ax = sns.barplot(x="labels", y="score", hue="Feature", data=df_complete)
plt.legend(loc ='lower left' )
plt.savefig(os.path.join(output,"cluster_weights.png"))

plt.figure()
sns.set_style("whitegrid")
ax = sns.barplot(x="labels", y="age",data=df)
plt.savefig(os.path.join(output,"age.png"))

#############################################################################

#ANOVA on age

T, p = scipy.stats.f_oneway(df[df["labels"]==0]["age"],\
                     df[df["labels"]==1]["age"])
ax = sns.violinplot(x="labels", y="age", data=df)
plt.title("ANOVA: t = %s, and  p= %s"%(T,p))
plt.savefig(os.path.join(output,"age_anova.png"))