import sys
import yaml
import pandas as pd
from statsmodels.stats.proportion import proportions_ztest, proportion_confint
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter, CoxPHFitter

original_stdout = sys.stdout  # Save a reference to the original standard output

# get params from config
stream = open("config.yaml", 'r')
config = yaml.safe_load(stream)['default']

data_path = config['cci']['results_path']
matching_path = config['matching']['results_path']
group_column = config['generate_groups']['group_column']
group_1_name = config['generate_groups']['group1']['name']
group_2_name = config['generate_groups']['group2']['name']

proportion_outcomes_input_path = config['proportion_outcomes']['input_path']
proportion_outcomes_variable_column = config['proportion_outcomes']['variable_column']
proportion_results_path_root = config['proportion_outcomes']['results_path_root']

cph_model_input_path = config['cph_model']['input_path']
cph_model_time_variable_column = config['cph_model']['time_variable_column']
cph_model_event_variable_column = config['cph_model']['event_variable_column']
cph_model_plot_type_column = config['cph_model']['plot_type_column']
cph_model_exclude_variable_column = config['cph_model']['exclude_variable_column']
cph_model_exclude_value_column = config['cph_model']['exclude_value_column']
cph_results_path_root = config['cph_model']['results_path_root']

inpatient_id_col = 'key_nis'

all_data_df = pd.read_csv(data_path)
matching_df = pd.read_csv(matching_path)

proportion_variables_df = pd.read_csv(proportion_outcomes_input_path)
proportion_variables = proportion_variables_df[proportion_outcomes_variable_column].to_list()

cph_variables_df = pd.read_csv(cph_model_input_path)

group_1_inpatient = matching_df['control'].to_list()
group_2_inpatient = matching_df['treatment'].to_list()

# include discharged for those who did not die
all_data_df['discharged'] = 1 - all_data_df['died']

matched_data_df = all_data_df[all_data_df[inpatient_id_col].isin(group_1_inpatient + group_2_inpatient)]\
    .reset_index(drop=True)

data_dict = {
    'All': all_data_df,
    'Matched': matched_data_df,
}

# proportion analysis
for data_name, df in data_dict.items():
    for var in proportion_variables:
        # filter out without var
        inpatients_without_var = df.loc[pd.isna(df[var]), inpatient_id_col].to_list()

        if data_name == 'Matched':
            inpatients_to_remove_df = matching_df[
                matching_df['treatment'].isin(inpatients_without_var) |
                matching_df['control'].isin(inpatients_without_var)
                ]
            inpatients_to_remove = \
                inpatients_to_remove_df['treatment'].to_list() + inpatients_to_remove_df['control'].to_list()
        else:
            inpatients_to_remove = inpatients_without_var

        analysis_df = df[~df[inpatient_id_col].isin(inpatients_to_remove)].reset_index(drop=True)
        n = analysis_df[inpatient_id_col].nunique()

        df_agg = analysis_df.groupby([group_column, 'z']).agg({inpatient_id_col: 'count', var: 'sum'}).reset_index()\
            .sort_values(by='z', ascending=True, ignore_index=True)\
            .rename(columns={inpatient_id_col: 'nobs', var: 'count'})
        nobs = df_agg['nobs']
        count = df_agg['count']
        props = count / nobs
        stat, pval = proportions_ztest(count, nobs)
        lower, upper = proportion_confint(count, nobs)
        lower_y_err = props - lower
        upper_y_err = upper - props
        plt.bar(x=df_agg[group_column].to_list(), height=props.to_list(), yerr=[lower_y_err, upper_y_err])
        plt.title(f'Proportion for {var}--{data_name}, n={n}, p={pval:.2e}')
        plt.xlabel('Group')
        plt.ylabel(f'Proportion for {var}')
        plt.xticks(rotation=30, horizontalalignment='right')
        plt.savefig(f'{proportion_results_path_root} for {var}--{data_name}, n={n}, p={pval:.2e}.png',
                    bbox_inches='tight')
        plt.close('all')

# cph analysis
for data_name, df in data_dict.items():
    for index, row in cph_variables_df.iterrows():
        time_variable = row[cph_model_time_variable_column]
        event_variable = row[cph_model_event_variable_column]
        plot_type = row[cph_model_plot_type_column]
        exclude_variable = row[cph_model_exclude_variable_column]
        exclude_value = row[cph_model_exclude_value_column]

        if plot_type not in ['cumulative_density', 'survival_function']:
            print('Plot type must be either cumulative_density or survival_function')
            continue

        # filter out without var and exclude
        inpatients_without_var = df.loc[pd.isna(df[time_variable]) | pd.isna(df[event_variable]),
                                        inpatient_id_col].to_list()
        if exclude_variable is not None and pd.notna(exclude_variable):
            inpatients_to_exclude = df.loc[df[exclude_variable] == exclude_value, inpatient_id_col].to_list()
            inpatients_without_var += inpatients_to_exclude

        # remove matched patients as well
        if data_name == 'Matched':
            inpatients_to_remove_df = matching_df[
                matching_df['treatment'].isin(inpatients_without_var) |
                matching_df['control'].isin(inpatients_without_var)
                ]
            inpatients_to_remove = \
                inpatients_to_remove_df['treatment'].to_list() + inpatients_to_remove_df['control'].to_list()
        else:
            inpatients_to_remove = inpatients_without_var

        analysis_df = df[~df[inpatient_id_col].isin(inpatients_to_remove)].reset_index(drop=True)
        n = analysis_df[inpatient_id_col].nunique()

        if plot_type == 'cumulative_density':
            title = f'Cumulative Density Plot for {event_variable} over {time_variable}--{data_name}, n={n}'
        else:
            title = f'Survival Plot for {event_variable} over {time_variable}--{data_name}, n={n}'

        kmf = KaplanMeierFitter()
        kmf_ax = None
        for z in [0, 1]:
            analysis_group_df = analysis_df[analysis_df['z'] == z].reset_index(drop=0)
            n_group = analysis_group_df[inpatient_id_col].nunique()
            kmf.fit(durations=analysis_group_df[time_variable], event_observed=analysis_group_df[event_variable],
                    label=f'{analysis_group_df[group_column].values[0]}, n={n_group}')
            if plot_type == 'cumulative_density':
                kmf_ax = kmf.plot_cumulative_density()
            else:
                kmf_ax = kmf.plot_survival_function()

        kmf_ax.set_xlabel(time_variable)
        kmf_ax.set_ylabel(event_variable)
        kmf_ax.set_title(title)
        kmf_fig = kmf_ax.get_figure()

        # cph
        cph = CoxPHFitter()
        cph.fit(analysis_df[[time_variable, event_variable, 'z']], duration_col=time_variable, event_col=event_variable)
        # print to file
        file_path = f'{cph_results_path_root}CPH Summary for {event_variable} over {time_variable}--{data_name}, ' \
                    f'n={n}.txt'
        with open(file_path, 'w') as f:
            sys.stdout = f  # Change the standard output to the file we created.
            cph.print_summary()
            sys.stdout = original_stdout  # Reset the standard output to its original value

        kmf_fig.savefig(f'{cph_results_path_root} {title}', bbox_inches='tight')
        plt.close('all')
