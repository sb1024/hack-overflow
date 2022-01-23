import yaml
import pandas as pd


# function for groups
def generate_group_df(df, var_col, dict1, dict2, group_col, not_grouped='None'):
    """
    :param df: dataframe with data to be grouped
    :param var_col: column name in df to use to assign groups
    :param dict1: dict with keys min, max, list, and name for group 1
    :param dict2: dict with keys min, max, list, and name for group 2
    :param group_col: column name in output df that will indicate group
    :param not_grouped: name to assign if not in either group
    :return: dataframe with group_col indicating assigned groups
    """
    results_df = df.copy(deep=True)

    group_1_min = dict1['min']
    group_1_max = dict1['max']
    group_1_list = dict1['list']
    group_1_name = dict1['name']

    group_2_min = dict2['min']
    group_2_max = dict2['max']
    group_2_list = dict2['list']
    group_2_name = dict2['name']

    results_df[group_col] = results_df.apply(
        lambda x: group_1_name if
        (((group_1_min is None) or x[var_col] >= group_1_min) and
         ((group_1_max is None) or x[var_col] <= group_1_min) and
         ((group_1_list is None) or x[var_col] in group_1_list)) else
        group_2_name if
        (((group_2_min is None) or x[var_col] >= group_2_min) and
         ((group_2_max is None) or x[var_col] <= group_2_min) and
         ((group_2_list is None) or x[var_col] in group_2_list)) else
        not_grouped,
        axis='columns')
    results_df['z'] = results_df.apply(
        lambda x: 0 if x[group_col] == group_1_name else 1 if x[group_col] == group_2_name else -1,
        axis='columns')

    return results_df


# get params from config
stream = open("config.yaml", 'r')
config = yaml.safe_load(stream)['default']

filtered_inpatient_data_path = config['data_paths']['filtered_inpatient']
filtered_hospital_data_path = config['data_paths']['filtered_hospital']
variable_column = config['generate_groups']['variable_column']
group_column = config['generate_groups']['group_column']
results_path = config['generate_groups']['results_path']
group_1_dict = config['generate_groups']['group1']
group_2_dict = config['generate_groups']['group2']
hospital_id_col = 'hosp_nis'

inpatient_df = pd.read_csv(filtered_inpatient_data_path)
hospital_df = pd.read_csv(filtered_hospital_data_path)

# merge using common columns
common_cols = list(set(inpatient_df.columns).intersection(hospital_df.columns))
hospital_cols_for_merge = [hospital_id_col] + [col for col in hospital_df.columns
                                               if col not in common_cols and col != hospital_id_col]
data_df = inpatient_df.merge(hospital_df[hospital_cols_for_merge], how='left', on=hospital_id_col)

grouped_df = generate_group_df(df=data_df, var_col=variable_column, dict1=group_1_dict, dict2=group_2_dict,
                               group_col=group_column, not_grouped='None')
grouped_df.to_csv(results_path, index=False)
