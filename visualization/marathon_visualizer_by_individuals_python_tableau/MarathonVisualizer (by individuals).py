import dfply as dfp
import numpy as np
import pandas as pd


class MarathonVisualizer:
    """
    Read data from input file that contains marathon (Tallinna Maraton 2018) finish times.
    Calculate average running time for mens and women.
    Calculate average running speed for every runner based on distance and time.
    Calculate passed distance for every runner based on time interval (3 minutes).
    Write data to output file for visualizing in Tableau.
    """

    def __init__(self, competition_name, running_distance, animation_interval):
        self.competition_name = competition_name
        self.running_distance = running_distance
        self.animation_interval = animation_interval

    def read_file(self, read_fn):
        results_df = pd.read_csv(read_fn, index_col=False)
        return results_df

    def write_file(self, write_fn, results_df):
        results_df.to_csv(write_fn, sep='\t', encoding='utf-8')

    def calculate_running_speed(self, input_df):
        # Convert input datafile to dataframe, leave only rows where result and name is available
        output_df = pd.DataFrame(input_df).dropna(subset=['TULEMUS'])

        # Extract hours, minutes and seconds from 'TULEMUS' HH:MM:SS format
        hour_fld = list(map(lambda next_item: pd.to_datetime(next_item).hour, output_df['TULEMUS']))
        min_fld = list(map(lambda next_item: pd.to_datetime(next_item).minute, output_df['TULEMUS']))
        sec_fld = list(map(lambda next_item: pd.to_datetime(next_item).second, output_df['TULEMUS']))

        gender_fld = output_df['VKL'].str.slice(0, 1)
        sec_total_fld = (np.array(hour_fld) * 3600) + (np.array(min_fld) * 60) + np.array(sec_fld)
        rows_in_output_df = output_df['TULEMUS'].count()

        sek_per_km_fld = np.array(sec_total_fld / self.running_distance).round(1)
        km_per_h_fld = np.array(1 / (sek_per_km_fld / 3600)).round(2)

        # Use quotient and mod in lambda function to extract min/km value
        min_per_km_fld = list(map(lambda x, y:
                                  str(round(x, 0)) + ":" + str(round(y, 0)),
                                  list(np.array(sek_per_km_fld // 60).astype(int)),
                                  list(np.array(sek_per_km_fld % 60).astype(int))))

        output_df = (output_df >>
                     dfp.mutate(SUGU=gender_fld,
                                HOUR=hour_fld,
                                MINUTE=min_fld,
                                SECOND=sec_fld,
                                SEK_KOKKU=sec_total_fld,
                                SEK_PER_KM=sek_per_km_fld,
                                MIN_PER_KM=min_per_km_fld,
                                KM_PER_H=km_per_h_fld,
                                PAIGUTUS=-sec_total_fld))

        df_column_names = output_df.columns.values
        slowest_runner_time = round((output_df.loc()[:, 'SEK_KOKKU']).max() / 60, 0)  # Slowest time in minutes
        animation_cycles_count = int(slowest_runner_time / self.animation_interval)
        spent_time_min = list(np.arange(start=0, stop=(animation_cycles_count * self.animation_interval) + 1,
                                        step=self.animation_interval))
        time_and_dist_matrix = np.zeros(shape=(rows_in_output_df, animation_cycles_count + 1))

        # Calculate running distance matrix (s=v*t formula in physics)
        for i in range(time_and_dist_matrix.shape[0]):
            for j in range(time_and_dist_matrix.shape[1]):
                passed_distance_km = round(list(km_per_h_fld)[i] * spent_time_min[j] / 60, 1)
                if passed_distance_km > 42.2:
                    passed_distance_km = 42.2
                time_and_dist_matrix[i, j] = passed_distance_km

        # Add new columns to output dataframe
        output_df = pd.concat([output_df, pd.DataFrame(data=time_and_dist_matrix, columns=spent_time_min)], axis=1)

        # Convert output dataframe from wide to long format and arrange it by name field
        output_df = ((output_df.melt(id_vars=df_column_names,
                                     value_vars=spent_time_min,
                                     var_name='KULUNUD_AEG_MIN',
                                     value_name='LÄBITUD_DISTANTS_KM')) >>
                     dfp.arrange(dfp.X.NIMI, ascending=True))

        return output_df

    def calculate_statistics(self, input_df):
        gender_fld = input_df['VKL'].str.slice(0, 1)

        df_res_gen = (input_df >>
                      dfp.select(dfp.X.TULEMUS) >>
                      dfp.mutate(SUGU=gender_fld))

        mens_median = self.datetime_median(df_res_gen, "M")
        womens_median = self.datetime_median(df_res_gen, "N")

        # Add marathon median data to the current competition
        rec_data = {'KOHT': ['', ''],
                    'NR': ['', ''],
                    'NIMI': ['VÕRDLUSGRUPP (M, MEDIAAN)', 'VÕRDLUSGRUPP (N, MEDIAAN)'],
                    'SÜND': ['', ''],
                    'RIIK': ['M_MED', 'N_MED'],
                    'ELUKOHT': ['', ''],
                    'KLUBI': ['', ''],
                    'TULEMUS': [mens_median, womens_median],
                    'KAOTUS': ['', ''],
                    'VKL': ['VGR', 'VGR']}

        rec_columns = np.array(['KOHT', 'NR', 'NIMI', 'SÜND', 'RIIK', 'ELUKOHT', 'KLUBI', 'TULEMUS', 'KAOTUS', 'VKL'])
        stat_df = pd.DataFrame(rec_data, columns=rec_columns)

        # Add statistics data to the end of input file
        output_df = input_df.append(stat_df, ignore_index=True)
        return output_df

    def datetime_median(self, input_df, gender):
        df_gender = input_df >> dfp.mask(dfp.X.SUGU == gender)

        df_datetime_format = np.array(pd.to_datetime(df_gender['TULEMUS']), dtype=np.datetime64)
        df_numeric_format = pd.to_numeric(df_datetime_format)
        median_numeric_format = np.median(df_numeric_format)
        median_datetime_format = pd.to_datetime(median_numeric_format).strftime('%H:%M:%S')

        return median_datetime_format


def main():
    # Data source address: http://www.championchip.ee/results/1175
    competition_name = "Tallinna Maraton 2018"
    read_fn = "datasets/Tallinna_Maraton_2018 (input).csv"
    write_fn = "datasets/Tallinna_Maraton_2018 (output).csv"
    running_distance = 42.2
    animation_interval = 3  # time in minutes after which new distance is calculated

    # Initialize MarathonVisualizer object
    mw = MarathonVisualizer(competition_name, running_distance, animation_interval)
    print("Start parsing...")

    # Read data from input file
    input_df = mw.read_file(read_fn)
    print("Reading file '" + read_fn + "' done")

    # Calculate average median running time for mens and women
    input_by_stat_df = mw.calculate_statistics(input_df)
    print("Statistics calculated")

    # Calculate running speed for every time interval
    output_df = mw.calculate_running_speed(input_by_stat_df)
    print("Running speed calculated")

    # Write data to output file
    mw.write_file(write_fn, output_df)
    print("Writing file  '" + write_fn + "' done")


main()
