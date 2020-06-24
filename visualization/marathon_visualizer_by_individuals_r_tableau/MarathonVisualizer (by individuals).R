
start_parsing <- function() {
  # Read data from input file that contains marathon (Maraton Eesti Vabariik 100) finish times.
  # Calculate average running time for mens and women.
  # Calculate average running speed for every runner based on distance and time.
  # Calculate passed distance for every runner based on time interval (1 minute).
  # Write data to output file for visualizing in Tableau.
  
  print("Start parsing...")
  
  # Load the libraries
  load_libraries()
  print("Libraries loaded")
  
  # Initialize the parameters
  initialize_parameters()
  print("Parameters initialized")
  
  # Read data from input file
  input_df <- read_file(read_fn)
  print(paste("Reading file '",read_fn,"' done", sep=""))
  
  # Calculate running speed
  output_df <- calculate_running_speed(input_df, "speed")
  print("Running speed calculated")
  
  # Calculate running statistics
  stat_results <- calculate_statistics(input_df)
  print("Statistics calculated")
  
  output_df <- rbind(output_df, stat_results)
  
  # Write data to output file
  write_file(write_fn, output_df)
  print(paste("Writing file '",write_fn,"' done", sep=""))
  
  print("Parsing done")
}

load_libraries <- function(){
  library(data.table)
  library(tidyverse)
}

initialize_parameters <- function(){
  current_competition <- "EV100 Maraton 2018"
  read_fn <- "datasets/EV100_Maraton_2018 (input).csv"
  write_fn <- "datasets/EV100_Maraton_2018 (output).csv"
  running_distance <- 42.2
  animation_interval <- 1 #time in minutes after which new distance is calculated
  world_rec_time <- "2:02:57"
  eur_rec_time <- "2:05:48"
  est_rec_time <- "2:08:53"
}

read_file <- function(file_name){
  results_df <- read.csv(file_name, 
                         stringsAsFactors=FALSE, 
                         fileEncoding = "utf-8", 
                         strip.white = TRUE)
}

write_file <- function(file_name, results_df){
  write.table(results_df, 
              file = file_name, 
              quote = FALSE, 
              sep = "\t", 
              row.names = FALSE)
}

calculate_running_speed <- function(results_df, action){
  # Extract hours, minutes and seconds from 'TULEMUS' HH:MM:SS format
  H_M_S <- data.table(H = hour(as.POSIXct(results_df$TULEMUS, format = "%H:%M:%S")),
                      M = minute(as.POSIXct(results_df$TULEMUS, format = "%H:%M:%S")),
                      S = second(as.POSIXct(results_df$TULEMUS, format = "%H:%M:%S")))
  
  rows_in_results <- nrow(na.omit(results_df))
  SUGU = str_sub(results_df$VKL, 1, 1)
  
  if(action=="stat"){
    SUGU <- rep_len("VGR", rows_in_results)
  }
  
  # Add new columns to results dataframe
  results_df<- results_df%>%
    mutate(SUGU,
           H = H_M_S$H,
           M = H_M_S$M,
           S = H_M_S$S,
           SEK_KOKKU = round(((H*3600)+(M*60)+S), digits = 1),
           SEK_PER_KM = round(SEK_KOKKU / running_distance, digits = 1),
           MIN_PER_KM = paste(SEK_PER_KM%/%60,":",round(SEK_PER_KM%%60, digits = 0), sep=""), #use quotient and mod to extract min/km value
           KM_PER_H = round(1/(SEK_PER_KM/3600), digits = 2),
           #PAIGUTUS = -period_to_seconds(hms(results_df$TULEMUS)),
           PAIGUTUS = -SEK_KOKKU)
  
  slowest_runner_time <- max(results_df$SEK_KOKKU)/60 #slowest time in minutes
  animation_cycles_count <- round(slowest_runner_time / animation_interval, digits = 0)
  km_per_h <- results_df$KM_PER_H
  
  spent_time_min <- seq(from = 0, to = animation_cycles_count*animation_interval, by = animation_interval)
  time_and_dist_matrix <- matrix(nrow = rows_in_results, 
                                 ncol = animation_cycles_count+1, 
                                 byrow = TRUE,
                                 dimnames = list(NULL, c(spent_time_min))) #add column names
  
  for(i in 1:dim(time_and_dist_matrix)[1]) {
    for(j in 1:dim(time_and_dist_matrix)[2]) {
      passed_distance_km <- round(km_per_h[i]*spent_time_min[j]/60, digits = 1)
      if(passed_distance_km > 42.2){
        passed_distance_km <- 42.2
      }
      time_and_dist_matrix[i,j] <- passed_distance_km
    }
  }
  
  # Add new columns to results dataframe
  results_df<- merge(results_df, data.table(time_and_dist_matrix), by="row.names") %>%
    within(results_df, rm(v$Row.names)) %>%
    arrange(KOHT)
  
  # Remove unnecessary column
  results_df$Row.names <- NULL
  # Convert results dataframe from wide to long format
  results_df <- gather(data = results_df, 
                                key = "KULUNUD_AEG_MIN", 
                                value = "LÄBITUD_DISTANTS_KM",
                                names(results_df[(grep("PAIGUTUS", colnames(results_df))+1):ncol(results_df)])) %>% #select columns from 'PAIGUTUS' column till the end of the data frame
                                arrange(NIMI)
}

calculate_statistics <- function(results_df){
  df_res_gen <- results_df%>%
    select(TULEMUS) %>%
    mutate(SUGU = c(str_sub(results_df$VKL, 1, 1)))
  
  df_res_gen$TULEMUS <- as.POSIXct(df_res_gen$TULEMUS, format = "%H:%M:%S")
  time_group_by_gender <- split(df_res_gen$TULEMUS, df_res_gen$SUGU)
  time_median <- lapply(lapply(time_group_by_gender, median), format, "%H:%M:%S")
  mens_median <- time_median$M
  womens_median <- time_median$N
  
  # Add marathon records data to the current competition
  world_rec_df <- data.frame(KOHT="", NR="", NIMI="VÕRDLUSGRUPP (MAAILMAREKORD)", SÜND="", RIIK="VGR(MR)", ELUKOHT="", KLUBI="", TULEMUS=world_rec_time, KAOTUS="", VKL="VGR(MR)", stringsAsFactors=FALSE)
  eur_rec_df <- data.frame(KOHT="", NR="", NIMI="VÕRDLUSGRUPP (EUROOPA REKORD)", SÜND="", RIIK="VGR(ER)", ELUKOHT="", KLUBI="", TULEMUS=eur_rec_time, KAOTUS="", VKL="VGR(ER)", stringsAsFactors=FALSE)
  est_rec_df <- data.frame(KOHT="", NR="", NIMI="VÕRDLUSGRUPP (EESTI REKORD)", SÜND="", RIIK="VGR(RR)", ELUKOHT="", KLUBI="", TULEMUS=est_rec_time, KAOTUS="", VKL="VGR(RR)", stringsAsFactors=FALSE)
  curr_mens_median_df <- data.frame(KOHT="", NR="", NIMI=toupper(paste("VÕRDLUSGRUPP (",current_competition, ", M, MEDIAAN)", sep="")), SÜND="", RIIK="VGR(M_MED)", ELUKOHT="", KLUBI="", TULEMUS=mens_median, KAOTUS="", VKL="VGR(M_MED)", stringsAsFactors=FALSE)
  curr_womens_median_df <- data.frame(KOHT="", NR="", NIMI=toupper(paste("VÕRDLUSGRUPP (",current_competition, ", N, MEDIAAN)", sep="")), SÜND="", RIIK="VGR(N_MED)", ELUKOHT="", KLUBI="", TULEMUS=womens_median, KAOTUS="", VKL="VGR(N_MED)", stringsAsFactors=FALSE)
  
  # Bind all dataframes together
  all_stat_df <- rbind(world_rec_df, eur_rec_df, est_rec_df, curr_mens_median_df, curr_womens_median_df)
  # Calculate running speed for statistics data
  all_stat_df <- calculate_running_speed(all_stat_df, "stat")
}

