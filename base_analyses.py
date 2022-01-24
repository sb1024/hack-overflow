import pandas as pd
import matplotlib.pyplot as plt


def categorical_base_analysis(data_dict, input_categorical_variables_dict):
    """
    :param data_dict: dictionary of dictionaries with data, where outer key is what analysis is for (i.e. inpatient) and
    inner keys must include df, id_col, and name_for_graph
    :param input_categorical_variables_dict: dictionary of dictionaries with categorical variables specs, where outer
    key is what analysis is for (i.e. inpatient, must match data_dict) and inner keys must include input_path,
    variable_column, is_root_column, num_to_plot, and results_path_root
    :return: Nothing, generates plots and excel

    """
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
                    subset_data_df = subset_data_df.melt(id_vars=id_col, value_vars=var_cols,
                                                         var_name=f'{variable}_root', value_name=variable)
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


def continuous_base_analysis(data_dict, input_continuous_variables_dict):
    """
    :param data_dict: dictionary of dictionaries with data, where outer key is what analysis is for (i.e. inpatient) and
    inner keys must include df, id_col, and name_for_graph
    :param input_continuous_variables_dict: dictionary of dictionaries with continuous variables specs, where outer key
    is what analysis is for (i.e. inpatient, must match data_dict) and inner keys must include input_path,
    variable_column, and results_path_root
    :return: Nothing, generates plots and excel
    """
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
                plt.ylabel(f'Frequency')

                plt.savefig(f'{results_path_root} for {variable}, n={n}.png', bbox_inches='tight')
                plt.close('all')
