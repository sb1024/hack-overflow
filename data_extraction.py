import yaml
import pandas as pd
import matplotlib.pyplot as plt


# get params from config
stream = open("config.yaml", 'r')
config = yaml.safe_load(stream)

input_inpatient_data_paths = config['data_paths']['input_inpatient']
input_hospital_data_paths = config['data_paths']['input_hospital']
filtered_inpatient_data_path = config['data_paths']['filtered_inpatient']
filtered_hospital_data_path = config['data_paths']['filtered_hospital']
input_diagnosis_codes_roots_path = config['diagnosis_codes_roots']['input_path']
input_diagnosis_codes_roots_col = config['diagnosis_codes_roots']['input_column_name']
num_diags_to_filter_on = config['diagnosis_codes_roots']['num_diags_to_filter_on']
min_age = config['age']['min']
max_age = config['age']['max']
input_categorical_variables_dict = config['baseline_analysis']['categorical']
input_continuous_variables_dict = config['baseline_analysis']['continuous']

# define variables of interest for filtering
inpatient_id_col = 'key_nis'
hospital_id_col = 'hosp_nis'
age_col = 'age'
diag_cols = [f'i10_dx{num}' for num in range(1, num_diags_to_filter_on + 1)]

if input_diagnosis_codes_roots_col is not None:
    input_diagnosis_codes_roots_df = pd.read_csv(input_diagnosis_codes_roots_path)
    input_diag_roots = input_diagnosis_codes_roots_df[input_diagnosis_codes_roots_col].to_list()
else:
    input_diagnosis_codes_roots_df = pd.read_csv(input_diagnosis_codes_roots_path, header=None)
    input_diag_roots = input_diagnosis_codes_roots_df.iloc[:, 0].to_list()

input_diags_regex = f".* ({'|'.join([f'{input_diag_root}.*' for input_diag_root in input_diag_roots])}) .*"

# read and concat data of interest
inpatient_data_dfs = []
hospital_data_dfs = []

for inpatient_data_path, hospital_data_path in zip(input_inpatient_data_paths, input_hospital_data_paths):
    # read data
    inpatient_data_df = pd.read_csv(inpatient_data_path)
    hospital_data_df = pd.read_csv(hospital_data_path)

    # # trim
    # for str_col in inpatient_data_df.dtypes[inpatient_data_df.dtypes == 'object'].index:
    #     inpatient_data_df[str_col] = inpatient_data_df[str_col].map(lambda x: x.strip() if pd.notna(x) else x)
    # for str_col in hospital_data_df.dtypes[hospital_data_df.dtypes == 'object'].index:
    #     hospital_data_df[str_col] = hospital_data_df[str_col].map(lambda x: x.strip() if pd.notna(x) else x)

    # filter by age if specified
    if min_age is not None:
        inpatient_data_df = inpatient_data_df[inpatient_data_df[age_col] >= min_age].reset_index(drop=True)
    if max_age is not None:
        inpatient_data_df = inpatient_data_df[inpatient_data_df[age_col] <= max_age].reset_index(drop=True)

    # filter by diags
    inpatient_data_df['i10_dx_concat'] = inpatient_data_df\
        .apply(lambda x: ' ' +
                         ' '.join([str(x[diag_col]) for diag_col in diag_cols
                                   if pd.notna(x[diag_col]) and x[diag_col] != '']) +
                         ' ',
               axis='columns')
    inpatient_data_df = inpatient_data_df[inpatient_data_df['i10_dx_concat'].str.contains(input_diags_regex)]\
        .reset_index(drop=True)

    # find unique hospital ids and filter
    hospital_ids = list(inpatient_data_df[hospital_id_col].unique())
    hospital_data_df = hospital_data_df[hospital_data_df[hospital_id_col].isin(hospital_ids)].reset_index(drop=True)

    # add file name to identify
    inpatient_data_df['source_file_name'] = inpatient_data_path
    hospital_data_df['source_file_name'] = hospital_data_path

    # drop custom column
    inpatient_data_df = inpatient_data_df.drop('i10_dx_concat', axis='columns')

    # save filtered dataframe
    inpatient_data_dfs.append(inpatient_data_df)
    hospital_data_dfs.append(hospital_data_df)

# put into one dataframe
inpatient_data_df = pd.concat(inpatient_data_dfs, axis='rows', ignore_index=True)
assert inpatient_data_df.shape[0] == inpatient_data_df[inpatient_id_col].nunique(), \
    'Some ids have more than one row for inpatient data'

hospital_data_df = pd.concat(hospital_data_dfs, axis='rows', ignore_index=True)
assert hospital_data_df.shape[0] == hospital_data_df[
                                        [hospital_id_col, 'source_file_name']
                                    ].drop_duplicates().shape[0], \
    'Some ids have more than one row for hospital data for same source file'

inpatient_data_df.to_csv(filtered_inpatient_data_path, index=False)
hospital_data_df.to_csv(filtered_hospital_data_path, index=False)

# store dataframes in dicts to do analyses on each
data_dict = {
    'inpatient': {
        'df': inpatient_data_df,
        'id_col': inpatient_id_col,
        'name_for_graph': 'Inpatient Visits',
    },
    'hospital': {
        'df': hospital_data_df,
        'id_col': hospital_id_col,
        'name_for_graph': 'Hospitals',
    },
}

# categorical base analysis
for data_name, data_info_dict in input_categorical_variables_dict.items():
    input_path = data_info_dict['input_path']
    variable_col = data_info_dict['variable_column']
    is_root_col = data_info_dict['is_root_column']
    num_to_plot = data_info_dict['num_to_plot']
    results_path_root = data_info_dict['results_path_root']

    data_df = pd.DataFrame(data_dict[data_name]['df'])
    id_col = data_dict[data_name]['id_col']
    name_for_graph = data_dict[data_name]['name_for_graph']
    n = data_df[id_col].nunique()

    output_data_path = f'{results_path_root}, n={n}.xlsx'

    input_var_df = pd.read_csv(input_path)

    with pd.ExcelWriter(output_data_path) as excel_file:
        for index, row in input_var_df.iterrows():
            variable = row[variable_col]
            is_root = row[is_root_col]
            if is_root == 1:
                var_cols = [col for col in data_df.columns if col.startswith(variable)]
                subset_data_df = data_df[[id_col] + var_cols]
                subset_data_df = subset_data_df.melt(id_vars=id_col, value_vars=var_cols, var_name=f'{variable}_root',
                                                     value_name=variable)
            else:
                subset_data_df = data_df[[id_col, variable]]

            categorical_results_df = subset_data_df.groupby(variable).agg({id_col: 'nunique'})\
                .rename(columns={id_col: f'Number of {name_for_graph}'}).reset_index()\
                .sort_values(by=[f'Number of {name_for_graph}', variable], ascending=False, ignore_index=True)

            categorical_results_df.to_excel(excel_file, sheet_name=variable[:31], index=False)

            # plot
            x_values = categorical_results_df[variable].astype(str).to_list()[:num_to_plot]
            y_values = categorical_results_df[f'Number of {name_for_graph}'].to_list()[:num_to_plot]
            plt.bar(x_values, y_values)
            plt.title(f'Number of {name_for_graph} by {variable}, n={n}')
            plt.xlabel(variable)
            plt.ylabel(f'Number of {name_for_graph}')
            plt.xticks(rotation=30, horizontalalignment='right')

            plt.savefig(f'{results_path_root} for {variable}, n={n}.png', bbox_inches='tight')
            plt.close('all')

# continuous base analysis
for data_name, data_info_dict in input_continuous_variables_dict.items():
    input_path = data_info_dict['input_path']
    variable_col = data_info_dict['variable_column']
    results_path_root = data_info_dict['results_path_root']

    data_df = pd.DataFrame(data_dict[data_name]['df'])
    id_col = data_dict[data_name]['id_col']
    name_for_graph = data_dict[data_name]['name_for_graph']
    n = data_df[id_col].nunique()

    output_data_path = f'{results_path_root}, n={n}.xlsx'

    input_var_df = pd.read_csv(input_path)

    with pd.ExcelWriter(output_data_path) as excel_file:
        for index, row in input_var_df.iterrows():
            variable = row[variable_col]
            continuous_results_df = data_df[variable].describe()
            continuous_results_df.to_excel(excel_file, sheet_name=variable[:31])

            # plot
            plt.hist(data_df[variable].to_list())
            plt.title(f'{variable} Distribution across {name_for_graph}')
            plt.xlabel(variable)
            plt.ylabel(f'{variable}')

            plt.savefig(f'{results_path_root} for {variable}, n={n}.png', bbox_inches='tight')
            plt.close('all')
