list.of.packages <- c("config", "dplyr", "MatchIt")
new.packages <- list.of.packages[!(list.of.packages %in% installed.packages()[,"Package"])]
if(length(new.packages)) install.packages(new.packages)

library(config)
library(dplyr)
library(MatchIt)

params <- config::get(value=NULL, config='default', file='config.yaml')
data_path <- params[['cci']][['results_path']]
seed <- params[['matching']][['seed']]
matching_variables_path <- params[['matching']][['input_path']]
matching_variable_col <- params[['matching']][['variable_column']]
ratio <- params[['matching']][['ratio']]
caliper <- params[['matching']][['caliper']]
nearest <- params[['matching']][['nearest']]
distance <- params[['matching']][['distance']]
m.order <- params[['matching']][['m.order']]
discard <- params[['matching']][['discard']]
results_path <- params[['matching']][['results_path']]
results_summary_path <- params[['matching']][['results_summary_path']]
inpatient_id_col <- 'key_nis'

set.seed(seed)  # to get consistent results when matching

# filter data only for those in group
data_df <- read.csv(file=data_path)
data_df <- data_df %>% filter(z %in% c(0, 1))

matching_variables_df <- read.csv(file=matching_variables_path)
matching_variables <- matching_variables_df[[matching_variable_col]]
match_formula_str <- paste('z~', paste(matching_variables, collapse=' + '))
match_formula <- as.formula(match_formula_str)

inpatient_match_df <- data_df[c(inpatient_id_col, 'z', matching_variables)]
inpatient_match_df <- inpatient_match_df %>% na.omit()  # drop missing values
rownames(inpatient_match_df) <- NULL

m.out <- matchit(match_formula, data=inpatient_match_df, ratio=ratio, caliper=caliper, nearest=nearest,
                 distance=distance, m.order=m.order, discard=discard)

matched_matrix <- m.out$match.matrix %>% na.omit()
treatment_indices <- row.names(matched_matrix)
control_indices <- unlist(matched_matrix)
treatment_inpatient_visits <- inpatient_match_df[treatment_indices,][[inpatient_id_col]]
control_inpatient_visits <- inpatient_match_df[control_indices,][[inpatient_id_col]]

matched_inpatient_df <- data.frame(treatment=treatment_inpatient_visits, control=control_inpatient_visits)
matched_inpatient_df <- matched_inpatient_df %>% na.omit()
write.csv(matched_inpatient_df, results_path, row.names=FALSE)

matching_summary <- summary(m.out)

sink(results_summary_path)
matching_summary
sink()
