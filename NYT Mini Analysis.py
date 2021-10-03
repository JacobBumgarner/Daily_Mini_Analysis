#############################################################

import sqlite3
import re
import os
import os
import csv

from datetime import datetime as dt
from datetime import timedelta as td
import calendar

import numpy as np
import Plotting as plt


# User customized variables
#############################################################
player_ids = {0: "Jacob" ... IDS HERE} # 
results_folder = "RESULTS/DIR/HERE"
chat_name = "Chat Name Here"
#############################################################


print ("----------------------------------------------------")
print ("Welcome to the NYT Mini Time Analysis Program.")
print ("----------------------------------------------------")

# Class to hold scores, player, and datetime of score.
class Score:
    def __init__(self, time, player_id, date, convert=True):
        # Convert time and date here
        if convert:
            time = self.time_conversion(time)
            date = self.date_conversion(date)
            player_id = player_ids[player_id]

        self.time = time
        self.player = player_id
        self.date = date
        
    def time_conversion(self, time):
        try:
            mins = int(time[0])
        except ValueError: # In case someone doesn't put a # before :
            mins = 0    
        secs = int(time[-2:])
        time = mins * 60 + secs
        return time
    
    def date_conversion(self, core_nsecs):
        epoch_secs = core_nsecs / 1000000000 + 978307200
        date = dt.fromtimestamp(epoch_secs)
        return date   
 
 
# Class to hold times and stats for each player
class Player:
    def __init__(self, name):
        self.name = name
        days = (end_date - start_date).days
        
        # Time and placements
        self.solves = [None] * days
        self.placements = np.zeros(len(player_ids))
        self.wins = 0
        self.losses = 0 # Losses may not always equate to last placement, i.e., not everyone plays
        
        # Isolated solve times and tods
        self.solve_times = None
        self.tod = None
        
        # Weekday stats
        self.wday_times = None
        self.wkday_placements = np.zeros((7, len(player_ids)))
        
        # Avg win/lose time stats
        self.avg_wintime = []
        self.avg_losstime = []
        self.avg_wintod = []
        self.avg_losstod = []
        
        self.avg_wintimes = []
        self.avg_losstimes = []
        self.avg_wintods = []
        self.avg_losstods = []
        
        # Fastest/Avg/Slowest
        self.fastest = 0
        self.avg = 0
        self.avg_sem = 0
        self.slowest = 0

# Make a connection with the sqlite3 database.
try:
    sqlite_connection = sqlite3.connect("/Users/jacobbumgarner/Library/Messages/chat.db")
    cursor = sqlite_connection.cursor()
    print ("SQLite3 connection initiated.")
    this_year = dt.today().year
    
    # Find the beginning and end dates in ns for the SQL query. 
    print ("Example: Starting month of 8 and ending month of 9 analyzes the solve times of August.")
    start_date = int(input("Please input the starting month as an int (#): "))
    end_date = int(input("Please input the month to stop finding times (#): "))
    
    if start_date == end_date:
        print ("Please analyze times through at least one entire month.")
        quit()
        
    if start_date < 1 or start_date > 12 or end_date < 1 or end_date > 12:
        print ("Please enter valid dates.")
        quit()
        
    start_date = dt(this_year, start_date, 1)
    start_time = start_date.timestamp()
    start_time = int(start_time - 978307200) * 1000000000 # Convert from epoch to core time.
    end_date = dt(this_year, end_date, 1)
    end_time = end_date.timestamp()
    end_time = int(end_time - 978307200) * 1000000000

    # Send our query to the database
    query = f"""SELECT text, handle_id, date FROM message MSG INNER JOIN chat_message_join CMJ ON CMJ.message_id = MSG.ROWID INNER JOIN chat ON chat.ROWID = CMJ.chat_id WHERE (chat.display_name = {chat_name} AND date > {start_time} AND date < {end_time}) ORDER BY MSG.date ASC;"""
    
    cursor.execute(query)
    texts = cursor.fetchall()
    cursor.close()
    
except sqlite3.Error as error:
    print ("Error in connecting to SQLite3 Server", error)
    
finally: 
    if sqlite_connection:
        sqlite_connection.close()
        print ("SQlite3 connection closed.")
        
print (len(texts), "texts identified.")

## Process our texts
# Exlude banter to prune our texts to only puzzle solve times.
candidate_times = []
for i, text in enumerate(texts):
    if text[0]:
        if ":" in text[0]:
            candidate_times.append(text)
            
# Isolate our true times.
solves = []
for cand in candidate_times:
    results = re.findall("\d:\d\d", cand[0])
    if results:
        time = Score(results[-1], cand[1], cand[2])
        solves.append(time)
    else:
        results = re.findall(":\d\d", cand[0])
        if results:
            time = Score(results[-1], cand[1], cand[2])
            solves.append(time)

print ("Removed", len(texts) - len(solves), "banter texts to identify", len(solves),"solves.")
del (texts)


## Now that we've extracted times, set up player classes, populate those classes with the times. 
players = {}
for i in player_ids:
    players[player_ids[i]] = Player(player_ids[i])
    
# Populate our player classes with their times. Iterate over times, add to player class if name matches.
for i, solve in enumerate(solves):
    new = True
    day = (solve.date - start_date).days
    name = solve.player
    # Check to see if there is a double score for this date
    # If there is, then we keep the new one and get rid of the old.
    if players[name].solves[day]:
        old_date = players[name].solves[day].date
        if old_date > solve.date:
            new = False
    if new:
        if solve.time > 5:
            players[name].solves[day] = solve

### Time for stats
date_range = (end_date - start_date).days
# Individual player weekday timings
for name in players:
    solves = players[name].solves
    wdaytimes = [[] for i in range(7)]
    for solve in solves:
        if solve:
            weekday = solve.date.weekday()
            wdaytimes[weekday].append(solve.time)

    players[name].wday_times = wdaytimes
    
# XY plot of times, days, and TODs.
daily_results = []
for id in players:
    solves = players[id].solves
    solve_times = [None] * date_range
    tod = [None] * date_range
    for i, solve in enumerate(solves):
        if solve:
            solve_times[i] = solve.time
            
            hr = solve.date.hour
            mins = solve.date.minute / 60
            solve_tod = hr + mins
            tod[i] = solve_tod
                
    avg_solve = 0
    solves = 0
    filtered = []
    for solve in solve_times:
        if solve:
            filtered.append(solve)
    filtered = np.array(filtered)
            
    players[id].fastest = np.max(filtered)
    players[id].avg = np.average(filtered)
    players[id].avg_sem = np.std(filtered, ddof=1) / np.sqrt(filtered.shape[0])
    players[id].slowest = np.min(filtered)
    
    players[id].solve_times = solve_times
    players[id].tod = tod

    
# Win tallies for each player, correlate with days
def win_stat(solve, weekday):
    name = solve.player
    players[name].placements[0] += 1
    players[name].wkday_placements[weekday][0] += 1
    players[name].wins += 1
    players[name].avg_wintimes.append(solve.time)
    
    # Time of win
    hr = solve.date.hour
    mins = solve.date.minute / 60
    tod = hr + mins
    
    players[name].avg_wintods.append(tod)

# Sort through times for placements
for i in range(date_range):
    day_times = []
    for id in players:
        if players[id].solves[i]:
            day_times.append(players[id].solves[i]) # Populate list of times

    day_times = sorted(day_times, key=lambda x: x.time) # Sort list of times based on time...
    
    if not day_times: # Skip if list is empty
        continue 
    
    weekday = day_times[0].date.weekday()
    
    for i, time in enumerate(day_times):
        place = i
        while True:
            if i == 0:
                win_stat(time, weekday) # Add win to first time place       
                break
            else:
                # Now look through times to see if 
                if place == 0:
                    win_stat(time, weekday) # Add win to tied first 
                    break
                elif time.time == day_times[place - 1].time: # Knock place down if tied to previous score
                    place -= 1
                else:
                    # If not first or tied, add placement
                    players[time.player].placements[place] += 1 
                    players[time.player].wkday_placements[weekday][place] += 1
                    break
                
    # Register the loss if there is one
    if day_times[0].time != day_times[-1]:
        name = day_times[-1].player
        players[name].losses += 1
        players[name].avg_losstimes.append(day_times[-1].time)
        
        # Time of loss
        hr = day_times[-1].date.hour
        mins = day_times[-1].date.minute / 60
        tod = hr + mins      
        players[name].avg_losstods.append(tod)
            
# Avg out the avgwin/avgloss
for id in players:
    if players[id].avg_wintime:
        players[id].avg_wintime = np.average(players[id].avg_wintimes)
        players[id].avg_wintod = np.average(players[id].avg_wintods)
    if players[id].avg_losstime:
        players[id].avg_losstime = np.average(players[id].avg_losstimes)
        players[id].avg_losstod = np.average(players[id].avg_losstods)

### Export the results to separate .csv files for R plotting
print ("Exporting Results")

if os.path.isdir(results_folder) == False: # Make sure the results directory exists
    os.mkdir(results_folder)

player_names = []
for id in players:
    player_names.append(id)
# Single-stat player results
stats_list = []
header = ["","Average", "Average SEM", "Fasest","Slowest","Avg_Wintime","Avg_Losstime","Avg_WinTOD","Avg_LossTOD", "Wins", "Losses"]

for i in range(len(players)):
    header.append(i)

stats_list.append(header)
for id in players:
    stat = []
    a = players[id]
    stat.append(id)
    stat.append(a.avg)
    stat.append(a.avg_sem)
    stat.append(a.fastest)
    stat.append(a.slowest)

    stat.append(a.avg_wintime)
    stat.append(a.avg_losstime)
    stat.append(a.avg_wintod)
    stat.append(a.avg_losstod)
    
    stat.append(a.wins)
    stat.append(a.losses)
    
    for place in a.placements:
        stat.append(place)
    
    stats_list.append(stat)

short_results = results_folder + "/Summary Results.csv"
with open(short_results, "w") as f:
    writer = csv.writer(f)
    for row in stats_list:
        writer.writerow(row)

# Times plot
stats = ["",""]
days = (end_date - start_date).days + 1
for i in range(1, days):
    stats.append(i)
stats = [stats]
for id in players:
    times = []
    times.append(id)
    times.append("Solve Speed (s)")
    for solve in players[id].solve_times:
        times.append(solve)
    
    tods = []
    tods.append(id)
    tods.append("Time of Day (24-h)")
    for tod in players[id].tod:
        tods.append(tod)
        
    stats.append(times)
    stats.append(tods)
    
    
long_results = results_folder + "/Individual Times.csv"
with open(long_results, "w") as f:
    writer = csv.writer(f)
    for row in stats:
        writer.writerow(row)
        

## Weekday results
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
header = ["Day", "Player", "Times"]
weekday_results = results_folder + "/Weekday Times.csv"
with open(weekday_results, "w") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for i in range(7):
        for id in players:
            row = [days[i], id]
            row.extend(players[id].wday_times[i])
            writer.writerow(row)
            
### Win loss/TODs
header = ["Player", "Win/Loss", "Speeds/TOD"]
win_tod_results = results_folder + "/Win-Loss TOD Results.csv"
with open(win_tod_results, "w") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for id in players:
        row = [id, "Win Speeds"]
        row.extend(players[id].avg_wintimes)
        writer.writerow(row)
        row = [id, "Win TOD"]
        row.extend(players[id].avg_wintods)
        writer.writerow(row)
        
    for id in players:
        row = [id, "Loss Speeds"]
        row.extend(players[id].avg_losstimes)
        writer.writerow(row)
        row = [id, "Loss TOD"]
        row.extend(players[id].avg_losstods)
        writer.writerow(row)
