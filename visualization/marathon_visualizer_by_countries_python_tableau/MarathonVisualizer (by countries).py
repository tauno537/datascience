import dfply as dfp
import numpy as np
import pandas as pd
import pycountry_convert as pycc


class MarathonVisualizer:
    """
    Read data from input file (based on Wikipedia) that contains national marathon records by country.
    Calculate average running time based on every country's records.
    Calculate average running speed for every country based on distance and time.
    Calculate passed distance for every country based on time interval (1 minute).
    Write data to output file for visualizing in Tableau.
    """

    def __init__(self, running_distance, animation_interval):
        self.running_distance = running_distance
        self.animation_interval = animation_interval

    def read_file(self, read_fn):
        results_df = pd.read_csv(read_fn, index_col=False)
        return results_df

    def write_file(self, write_fn, results_df):
        results_df.to_csv(write_fn, sep='\t', encoding='utf-8')

    def get_continents(self, country_name):
        continents_table = {
            "AS": "Asia",
            "EU": "Europe",
            "NA": "North-America",
            "SA": "South-America",
            "AF": "Africa",
            "OC": "Oceania"
        }
        countries_not_found_table = {
            "England": "Europe",
            "Wales": "Europe",
            "Scotland": "Europe",
            "Northern Ireland": "Europe",
            "Kosovo": "Europe",
            "Chinese Taipei": "Asia",
            "Palestinian territories": "Asia",
            "East Timor": "Asia",
            "Netherlands Antilles": "South-America",
            "Saint Helena": "Africa"
        }
        try:
            iso2_cname = pycc.country_name_to_country_alpha2(country_name)
            continent_code = pycc.country_alpha2_to_continent_code(iso2_cname)
            return continents_table.get(continent_code)
        except KeyError:
            return countries_not_found_table.get(country_name)

    def calculate_running_speed(self, input_df):
        # Convert input datafile to dataframe, leave only rows where result and name is available
        output_df = pd.DataFrame(input_df).dropna(subset=['RESULT'])

        # Extract hours, minutes and seconds from 'RESULT' HH:MM:SS format
        hour_fld = list(map(lambda next_item: pd.to_datetime(next_item).hour, output_df['RESULT']))
        min_fld = list(map(lambda next_item: pd.to_datetime(next_item).minute, output_df['RESULT']))
        sec_fld = list(map(lambda next_item: pd.to_datetime(next_item).second, output_df['RESULT']))

        rows_in_output_df = output_df['RESULT'].count()
        sec_total_fld = (np.array(hour_fld) * 3600) + (np.array(min_fld) * 60) + np.array(sec_fld)
        sec_per_km_fld = np.array(sec_total_fld / self.running_distance).round(1)
        km_per_h_fld = np.array(1 / (sec_per_km_fld / 3600)).round(2)

        # Use quotient and mod in lambda function to extract min/km value
        min_per_km_fld = list(map(lambda x, y:
                                  str(round(x, 0)) + ":" + str(round(y, 0)),
                                  list(np.array(sec_per_km_fld // 60).astype(int)),
                                  list(np.array(sec_per_km_fld % 60).astype(int))))

        output_df = (output_df >>
                     dfp.mutate(HOUR=hour_fld,
                                MINUTE=min_fld,
                                SECOND=sec_fld,
                                SEC_TOTAL=sec_total_fld,
                                SEC_PER_KM=sec_per_km_fld,
                                MIN_PER_KM=min_per_km_fld,
                                KM_PER_H=km_per_h_fld,
                                POSITION=-sec_total_fld))

        df_column_names = output_df.columns.values
        slowest_runner_time = round((output_df.loc()[:, 'SEC_TOTAL']).max() / 60, 0)  # Slowest time in minutes
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
        output_df = pd.concat([output_df,
                              pd.DataFrame(data=time_and_dist_matrix, columns=spent_time_min)],
                              axis=1,
                              sort=False)

        # Convert output dataframe from wide to long format and arrange it by name field
        output_df = ((output_df.melt(id_vars=df_column_names,
                                     value_vars=spent_time_min,
                                     var_name='SPENT_TIME_MIN',
                                     value_name='PASSED_DISTANCE_KM')) >>
                     dfp.arrange(dfp.X.NAME, ascending=True))

        return output_df

    def calculate_statistics(self, input_df):
        countries_median = self.datetime_median(input_df['RESULT'])

        # Add marathon median data to the current competition
        rec_data = {'CONTINENT': ['Continents median value'],
                    'COUNTRY': ['Median value'],
                    'RESULT': [countries_median],
                    'NAME': [''],
                    'DATE': [''],
                    'PLACE': ['']
                    }

        rec_columns = np.array(['CONTINENT', 'COUNTRY', 'RESULT', 'NAME', 'DATE', 'PLACE'])
        stat_df = pd.DataFrame(rec_data, columns=rec_columns)

        # Add statistics data to the end of input file
        output_df = input_df.append(stat_df, ignore_index=True)
        return output_df

    def datetime_median(self, input_df):
        df_datetime_format = np.array(pd.to_datetime(input_df), dtype=np.datetime64)
        df_numeric_format = pd.to_numeric(df_datetime_format)
        median_numeric_format = np.median(df_numeric_format)
        median_datetime_format = pd.to_datetime(median_numeric_format).strftime('%H:%M:%S')
        return median_datetime_format


def main():
    # Data source address: https://en.wikipedia.org/wiki/National_records_in_the_marathon
    read_fn = "datasets/Marathon_results_by_countries (input).csv"
    write_fn = "datasets/Marathon_results_by_countries (output).csv"
    running_distance = 42.2
    animation_interval = 1  # time in minutes after which new distance is calculated

    # Initialize MarathonVisualizer object
    mw = MarathonVisualizer(running_distance, animation_interval)
    print("Start parsing...")

    # Read data from input file
    input_df = mw.read_file(read_fn)
    print("Reading file '" + read_fn + "' done")

    # Map continents to countries
    continents_list = list(map(lambda next_item: mw.get_continents(next_item), input_df['COUNTRY']))
    modified_input_df = pd.concat([pd.DataFrame({'CONTINENT': continents_list}), input_df], axis=1, sort=False)

    # Calculate average median running time based on every country's records
    input_by_stat_df = mw.calculate_statistics(modified_input_df)
    print("Statistics calculated")

    # Calculate running speed for every time interval
    output_df = mw.calculate_running_speed(input_by_stat_df)
    print("Running speed calculated")

    # Write data to output file
    mw.write_file(write_fn, output_df)
    print("Writing file  '" + write_fn + "' done")


main()
