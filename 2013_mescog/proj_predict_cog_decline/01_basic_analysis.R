#install.packages("GGally")

require(ggplot2)

SRC = paste(Sys.getenv("HOME"),"git/scripts/2013_mescog/proj_predict_cog_decline",sep="/")
BASE_DIR = "/neurospin/mescog/proj_predict_cog_decline"

# INPUT ---
#INPUT_NA = "/neurospin/mescog/proj_predict_cog_decline/data/dataset_clinic_niglob_20140128.csv"
#INPUT = "/neurospin/mescog/proj_predict_cog_decline/data/dataset_clinic_niglob_20140128_imputed.csv"
INPUT_NA =paste(BASE_DIR, "data", "dataset_clinic_niglob_20140205_nomissing_BPF-LLV.csv", sep="/")
INPUT = paste(BASE_DIR, "data", "dataset_clinic_niglob_20140205_nomissing_BPF-LLV_imputed.csv", sep="/")

# OUTPUT ---
OUTPUT = sub(".csv", "", INPUT_NA)
OUTPUT_PAIRS_SCATTER = paste(OUTPUT, "_descriptive_pairs-scatter.pdf", sep="")
OUTPUT_EVOL = paste(OUTPUT, "_descriptive_M36=coef*M0.csv")
OUTPUT_EVOL_PLOT = paste(OUTPUT, "_descriptive_M36xM0.pdf", sep="")
OUTPUT_POP = paste(sub(".csv", "", INPUT), "_descriptive_population.csv", sep="")

source(paste(SRC,"utils.R",sep="/"))

###############################################################################################
## Population descriptive statistics for variables used
################################################################################################
db = read_db(INPUT)
#db = read_db(INPUT_NA)
D = db$DB
D$TMTB_TIME.CHANGE = (D$TMTB_TIME.M36 - D$TMTB_TIME)
D$MDRS_TOTAL.CHANGE = (D$MDRS_TOTAL.M36 - D$MDRS_TOTAL)
D$MRS.CHANGE = (D$MRS.M36 - D$MRS)
D$MMSE.CHANGE = (D$MMSE.M36 - D$MMSE)

# Clinical variables
db$col_clinic
# SEX cada={1:'m', 2:'f'}
D$SEX = as.factor(sub(2, "F", sub(1, 'M', D$SEX)))
# CADASIL: 1 = none, 2 = < 2 drinks a day ; 3 = > 2 drinks a day
D$ALCOHOL = as.factor(sub(1, "None", sub(2, '2 drink/day', sub(3, '>2 drink/day', round(D$ALCOHOL)))))
# cada={1:"current", 2:"never", 3:"former"}
D$SMOKING = as.factor(sub(1, "Current", sub(2, "Never", sub(3, "Former", round(D$SMOKING)))))

# v = "SEX"
# num = NULL
# cate = NULL
# d = D[, colnames(D)[!(colnames(D) %in% "ID")]]
# for(v in colnames(d))
# if(is.numeric(d[,v])){
#   num = rbind(num, data.frame(var=v,
#   N=sum(!is.na(d[, v])),
#   Mean=round(mean(d[, v], na.rm=TRUE),2),
#   Sd=round(sd(d[, v], na.rm=TRUE),2),
#   #median(d[, v], na.rm=TRUE),
#   min=round(min(d[, v], na.rm=TRUE),2),
#   max=round(max(d[, v], na.rm=TRUE),2)))
# }else{
#   t=table(d[,v])
#   string = ""
#   for(n in names(t)) string = paste(string, n, ":", t[n], " (", round(t[n]/sum(t), 2)*100, "%), ", sep="")
#   string = sub(", $", "", string)
#   cate = rbind(cate, data.frame(var=v, "count"= string))
# }
# num
# cate

write.csv(num, OUTPUT_POP, row.names=F)

Age, years
Male sex, n (%)
History of hypertension, n (%)
History of hypercholesterolemia
n, n (%)
Diabetes, n (%)
Any alcohol consumption, n (%)

# Disability and cognitive scores
db$col_targets
db$col_baselines

Modified Rankin’s scale, mean,
median, range
Mattis dementia rating scale,
mean, median, range
Trail making test A, s, mean,
median, range
Trail making test B, s, mean,
median, range

# MRI markers
db$col_niglob

Brain parenchymal fraction,
mean Ϯ SD, range
Volume of white matter
hyperintensities, mm 3 , mean,
median, range
Volume of lacunar lesions, mm 3 ,
mean, median, range
Number of cerebral microbleeds,
mean, median, range

###############################################################################################
## Descriptive statistics: Pairs scatter plot
################################################################################################
db = read_db(INPUT)
dbna = read_db(INPUT_NA)
D = db$DB
Dna = dbna$DB
D$SITE = as.factor(D$SITE)
Dna$SITE = as.factor(D$SITE)

sum(is.na(D[, db$col_niglob]))
#[1] 0
sum(is.na(Dna[, db$col_niglob]))
#[1] 68
sum(is.na(D[, db$col_clinic]))
#[1] 0
sum(is.na(Dna[, db$col_clinic]))
#[1] 243

library(GGally)
pdf(OUTPUT_PAIRS_SCATTER)
pairs(Dna[, db$col_baselines], col=Dna$SITE, main="Pairs (with NA) @ BASELINE (black:FR, red:GE)")
pairs(D[, db$col_baselines], col=D$SITE, main="Pairs (imputed) @ BASELINE (black:FR, red:GE)")
p = ggpairs(D[, c(db$col_baselines, "SITE")], colour='SITE', alpha=0.4, , title = "Pairs (Imputed) @ BASELINE")
print(p)
p = plotmatrix(as.data.frame(scale(Dna[, db$col_baselines]))) + geom_smooth(method="lm") + ggtitle("Pairs (with NA) scaled @ BASELINE")
print(p)
p = plotmatrix(as.data.frame(scale(D[, db$col_baselines]))) + geom_smooth(method="lm") + ggtitle("Pairs (Imputed) scaled @ BASELINE")
print(p)
pairs(D[, db$col_targets], col=D$SITE, main="Pairs @ M36 (black:FR, red:GE)")
p = plotmatrix(as.data.frame(scale(Dna[, db$col_targets]))) + geom_smooth(method="lm") + ggtitle("Pairs scaled @ M36")
print(p)
dev.off()



################################################################################################
## Descriptive statistics: M36 ~ BASELINE
################################################################################################
db = read_db(INPUT)
dbna = read_db(INPUT_NA)
D = db$DB
Dna = dbna$DB
Dfr = D[D$SITE == "FR", ]; Dge = D[D$SITE == "GE", ]
Dnafr = Dna[Dna$SITE == "FR", ]; Dnage = Dna[Dna$SITE == "GE", ]


STAT = NULL
for(TARGET in db$col_targets){
  BASELINE = strsplit(TARGET, "[.]")[[1]][1]
  formula = formula(paste(TARGET, "~", BASELINE, "-1"))
  stat = data.frame(
    VAR=BASELINE,
    SITE=c("FR", "GE", "FR", "GE"), DATA=c("withNAs", "withNAs", "Imputed", "Imputed"),
    COEF=c(lm(formula, Dnafr)$coefficients[[1]], lm(formula, Dnage)$coefficients[[1]],
           lm(formula, Dfr)$coefficients[[1]], lm(formula, Dge)$coefficients[[1]]))
  STAT = rbind(STAT, stat)
}


write.csv(STAT, OUTPUT_EVOL, row.names=FALSE)

# VAR SITE    DATA      COEF
# 1   TMTB_TIME   FR withNAs 0.9773488
# 2   TMTB_TIME   GE withNAs 0.8932809
# 3   TMTB_TIME   FR Imputed 0.9773488
# 4   TMTB_TIME   GE Imputed 0.9168418
# 5  MDRS_TOTAL   FR withNAs 0.9829722
# 6  MDRS_TOTAL   GE withNAs 0.9971494
# 7  MDRS_TOTAL   FR Imputed 0.9829722
# 8  MDRS_TOTAL   GE Imputed 0.9971494
# 9         MRS   FR withNAs 1.0159151
# 10        MRS   GE withNAs 0.8791209
# 11        MRS   FR Imputed 1.0159151
# 12        MRS   GE Imputed 0.8791209
# 13       MMSE   FR withNAs 1.0136127
# 14       MMSE   GE withNAs 1.0013020
# 15       MMSE   FR Imputed 1.0136612
# 16       MMSE   GE Imputed 1.0013020

D2 = NULL
D2na = NULL
for(TARGET in db$col_targets){
  #TARGET = "TMTB_TIME.M36"
  BASELINE = strsplit(TARGET, "[.]")[[1]][1]
  D2 = rbind(D2, data.frame(VAR=BASELINE, M36=D[, TARGET], BASELINE=D[, BASELINE], SITE=D[, "SITE"]))
  D2na = rbind(D2na, data.frame(VAR=BASELINE, M36=Dna[, TARGET], BASELINE=Dna[, BASELINE], SITE=Dna[, "SITE"]))
}


pdf(OUTPUT_EVOL_PLOT, width = 10, height = 7)
p = ggplot(D2na, aes(x = BASELINE, y = M36)) + geom_point(aes(colour=SITE), alpha=.5)+#, position = "jitter")
  geom_abline(linetype="dotted") + 
  stat_smooth(formula=y~x-1, method="lm", aes(colour=SITE)) +  facet_wrap(~VAR, scales="free") + scale_color_manual(values=c("blue", "red")) +
  ggtitle("M36 ~ BASELINE (with NA)")
print(p)

p = ggplot(D2, aes(x = BASELINE, y = M36)) + geom_point(aes(colour=SITE), alpha=.5) + #, position = "jitter")
  geom_abline(linetype="dotted") + 
  stat_smooth(formula=y~x-1, method="lm", aes(colour=SITE)) +  facet_wrap(~VAR, scales="free") + scale_color_manual(values=c("blue", "red")) +
  ggtitle("M36 ~ BASELINE (Imputed)")
print(p)

p = ggplot(D2, aes(x = BASELINE, y = M36)) + geom_point(alpha=.5) + #, position = "jitter")
  geom_abline(linetype="dotted") + 
  stat_smooth(formula=y~x-1, method="lm") +  facet_wrap(~VAR, scales="free") + scale_color_manual(values=c("blue", "red")) +
  ggtitle("FR+GE M36 ~ BASELINE (Imputed)")
print(p)

dev.off()


################################################################################################
## Partition RULE: M36 ~ BASELINE color by group
################################################################################################
db = read_db(INPUT)
D = db$DB
grp = rep(NA, nrow(D))
#grp[D$LLV >= 1500] = "Lacunes"
#grp[D$BPF < 0.773] = "Atrophy"
grp[D$LLV >= 1500] = "Lacunes"
grp[D$BPF < 0.75] = "Atrophy"
D$GRP = as.factor(grp)
D$MDRS_TOTAL.M36[D$MDRS_TOTAL.M36 == min(D$MDRS_TOTAL.M36, na.rm=T)]=NA
D2 = NULL
for(TARGET in db$col_targets){
  #TARGET = "TMTB_TIME.M36"
  BASELINE = strsplit(TARGET, "[.]")[[1]][1]
  D2 = rbind(D2, data.frame(VAR=BASELINE, M36=D[, TARGET], M0=D[, BASELINE], SITE=D[, "SITE"], ID=D[, "ID"], GRP=D[, "GRP"]))
}

Dg = D2[!is.na(D2$GRP), ]
Dng = D2[is.na(D2$GRP), ]

pdf("/neurospin/mescog/proj_predict_cog_decline/20140205_nomissing_BPF-LLV_imputed/M36~M0_cutoff_LLV-BPF.pdf")

p = ggplot(D2, aes(x = M0, y = M36)) + 
  geom_point(data=Dng, aes(colour=GRP), alpha=.4, position = "jitter") +
  geom_point(data=Dg, aes(colour=GRP), alpha=1)+#, position = "jitter") +
  geom_abline(linetype="dotted") + 
  #stat_smooth(formula=y~x-1, method="lm", aes(colour=GRP))+
  facet_wrap(~VAR, scales="free") +
  ggtitle("M36 ~ M0")
print(p)
dev.off()

# ################################################################################################
# ## M36~each variable
# ################################################################################################
# RESULTS = NULL
# 
# for(TARGET in db$col_targets){
#   #TARGET = "TMTB_TIME.M36"
#   #TARGET = "MDRS_TOTAL.M36"
#   dbfr = db$DB_FR[!is.na(db$DB_FR[, TARGET]), ]
#   dbgr = db$DB_GE[!is.na(db$DB_GE[, TARGET]), ]
#   RES = NULL
#   for(PRED in c(db$col_clinic, db$col_niglob)){
#     #PRED="TMTB_TIME"
#     #PRED= "MDRS_TOTAL"
#     formula = formula(paste(TARGET,"~",PRED))
#     modfr = lm(formula, data = dbfr)
#     modgr = lm(formula, data = dbgr)
#     
#     loss.frfr=round(loss.reg(dbfr[, TARGET], predict(modfr, dbfr), df=2),digit=2)[c("R2", "cor")]
#     loss.frgr=round(loss.reg(dbgr[, TARGET], predict(modfr, dbgr), df=2),digit=2)[c("R2", "cor")]
#     loss.grgr=round(loss.reg(dbgr[, TARGET], predict(modgr, dbgr), df=2),digit=2)[c("R2", "cor")]
#     loss.grfr=round(loss.reg(dbfr[, TARGET], predict(modgr, dbfr), df=2),digit=2)[c("R2", "cor")]
#     
#     names(loss.frfr) = c("r2_ff","cor_ff")
#     names(loss.frgr) = c("r2_fg","cor_fg")
#     names(loss.grgr) = c("r2_gg","cor_gg")
#     names(loss.grfr) = c("r2_gf","cor_gf")
#     res = data.frame(target=TARGET, pred=PRED, as.list(c(loss.frfr, loss.frgr, loss.grgr, loss.grfr)))
#     if(is.null(RES)) RES = res else RES = rbind(RES, res)
#   }
#   RES = RES[order(RES$r2_fg, decreasing=TRUE),]
#   if(is.null(RESULTS)) RESULTS = RES else RESULTS = rbind(RESULTS, RES)
# }
# 
# write.csv(RESULTS, OUTPUT_MULM, row.names=FALSE)


