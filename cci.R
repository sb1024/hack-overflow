list.of.packages <- c("config", "dplyr", "reshape", "comorbidity")
new.packages <- list.of.packages[!(list.of.packages %in% installed.packages()[,"Package"])]
if(length(new.packages)) install.packages(new.packages)

library(config)
library(dplyr)
library(reshape)
library(comorbidity)

params <- config::get(value=NULL, config='default', file='config.yaml')
data_path <- params[['generate_groups']][['results_path']]
diag_columns_prefix <- params[['cci']][['diag_columns_prefix']]
cci_weights_path <- params[['cci']][['weights_path']]
cci_category_col <- params[['cci']][['cci_category_column']]
cci_weight_col <- params[['cci']][['cci_weight_column']]
results_path <- params[['cci']][['results_path']]
inpatient_id_col <- 'key_nis'

cci_weights_df <- read.csv(file=cci_weights_path)

data_df <- read.csv(file=data_path)

# calculate cci
diag_df_columns <- c(inpatient_id_col, colnames(data_df)[startsWith(colnames(data_df), diag_columns_prefix)])
diag_df <- data_df[diag_df_columns]
diag_df <- diag_df %>% melt(id=inpatient_id_col)
diag_df <- diag_df[c(inpatient_id_col, 'value')]
colnames(diag_df) <- c(inpatient_id_col, 'diag')
cci_df <- comorbidity(diag_df, id=inpatient_id_col, code='diag', map= "charlson_icd10_quan", assign0 = FALSE)
cci_categories <- colnames(cci_df)[colnames(cci_df) != inpatient_id_col]
cci_df[['num_cci_conditions']] <- rowSums(cci_df[cci_categories], na.rm=TRUE)
for(cci_category in cci_categories){
  weight <- cci_weights_df[cci_weights_df[cci_category_col] == cci_category, cci_weight_col]
  cci_df[paste0('weighted_', cci_category)] <- cci_df[cci_category] * weight
}
weighted_cci_categories <- paste0('weighted_', cci_categories)
cci_df[['cci']] <- rowSums(cci_df[weighted_cci_categories], na.rm=TRUE)
data_df <- base::merge(data_df, cci_df, by=inpatient_id_col, all=TRUE)
write.csv(data_df, results_path, row.names=FALSE)
