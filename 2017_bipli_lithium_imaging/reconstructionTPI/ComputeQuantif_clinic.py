# -*- coding: utf-8 -*-
"""
Created on Tue Feb 13 17:17:38 2018

@author: js247994
"""

#This code serves to brin the raw signal to theconcentration values by basing itself on T1 input.

import nibabel as nib
import numpy as np, os#, sys
from scipy import stats
from visualization import PlotReconstructedImage
import argparse,sys
#from ComputeDensity3D_clinic import degtorad,rval
#python ComputeQuantif_clinic.py --i V:\projects\BIPLi7\ClinicalData\Processed_Data\2018_06_01\TPI\Reconstruct_gridding\01-Raw\Patient...

parser = argparse.ArgumentParser(epilog="ComputeDensity version 1.0")

parser.add_argument("--v","--verbose", help="output verbosity", action="store_true")
parser.add_argument("--i", type=str,help="Input first file path")
parser.add_argument("--deg", type=int,help="Flip angle of first file")
parser.add_argument("--o", type=str,help="Output file path and name (as NIfTI)")
parser.add_argument("--m", type=str,help="Possible mask path")
parser.add_argument("--t1", type=float, help="Overall T1 value (in seconds)")
parser.add_argument("--B0map", type=str, help="Input B0 map path (if absent, set to 1 everywhere)")

args = parser.parse_args()

if args.v: verbose=True
else: verbose = False
if not args.i :
	#windll.Kernel32.SetConsoleTextAttribute(std_output_hdl, 12)
	print('ERROR   : Input file not specified')
	#windll.Kernel32.SetConsoleTextAttribute(std_output_hdl, 7)
	sys.exit()
if args.i :
    Img_path = args.i
    Img=nib.load(Img_path)
    Img=Img.get_data()   
if not args.deg: 
    print('Error    : Missing flip angle')
if args.deg: degval=args.deg
if args.t1: T1=args.t1
if not args.t1: T1= 3.947000 #4.56
if args.B0map:
    RatioMap = nib.load(args.B0map) #Can be supposed as a 1 matrix (to add)
    RatioMap =RatioMap.get_data() 
if not args.B0map:    
    RatioMap=np.ones(np.shape(Img))
if args.m:
    mask= nib.loag(args.m)
    mask= mask.get_data()
if not args.m:
    mask=RatioMap
if args.o:
    outputnii=args.o
    
def rval(E1,alpha,E2):
    parray=1-E1*np.cos(alpha)-E2*E2*(E1-np.cos(alpha))
    qarray=E2*(1-E1)*(1+np.cos(alpha))
    return((1-E2*E2)/(np.sqrt(parray*parray-qarray*qarray)))  
   
#values are displayed in micro-seconds (consistent with .dat values)    
    
TR=200000 #Lithium
TE=300 #Lithium
res= 15 #Resolution in mm (isotropic)
T1=3947000
T2=63000
T2star=12000
#kvalSPGR=2.264665697646913e-06
kvalSPGR=2.2113e-06
kvalSSFP=2.2621e-06
E2star=np.exp(-TE/T2star)
E1=np.exp(-TR/T1)
E2=np.exp(-TR/T2)

FAMap = RatioMap*float(degval)

FAMap=np.squeeze(FAMap)
FAMap=FAMap*np.pi/180.0
mask=np.squeeze(mask)

M0_T1SPGR = np.zeros(shape=Img.shape)
rho_T1SPGR = np.zeros(shape=Img.shape)
rho_T1SSFP = np.zeros(shape=Img.shape)

#T1hyp=4.56
#E1hyp=np.exp(-TR/T1hyp)
for i in range(Img.shape[0]):
    for j in range(Img.shape[1]):
        for k in range(Img.shape[2]):
            if mask[i,j,k]>0:
                rho_T1SPGR[i,j,k]=Img[i,j,k]*((1-E1*E2-np.cos(FAMap[i,j,k])*(E1-E2))/(np.sin(FAMap[i,j,k])*(1-E1)))/kvalSPGR
                rho_T1SSFP[i,j,k]=Img[i,j,k]/(kvalSSFP*(np.tan(FAMap[i,j,k]/2)*(1-(E1-np.cos(FAMap[i,j,k]))*rval(E1,FAMap[i,j,k],E2))));
                # 1/(kvalSSFP*(np.tan(degval/2)*(1-(E1spec-np.cos(degval))*rval(E1spec,degval,E2))))
from nifty_funclib import SaveArrayAsNIfTI
Hpath, Fname = os.path.split(str(outputnii))
Fname = Fname.split('.')
OutputPathrho_T1SPGR = os.path.join( Hpath + '\\' + Fname[0]+ "_rhoSPGR.nii")
OutputPathrho_T1SSFP = os.path.join( Hpath + '\\' + Fname[0]+ "_rhoSSFP.nii")

if verbose:
    print((degval,T1,E1))
SaveArrayAsNIfTI(rho_T1SSFP,res,res,res,OutputPathrho_T1SSFP) 
SaveArrayAsNIfTI(rho_T1SPGR,res,res,res,OutputPathrho_T1SPGR) 