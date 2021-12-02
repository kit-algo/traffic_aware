#!/usr/bin/env python3

import pandas as pd

import json
import glob
import os
import re

from shared import *

base = "exp/"
paths = glob.glob(base + "data/*.json")
data = [json.load(open(path)) for path in paths]

queries = pd.DataFrame.from_records([{
    **algo,
    'graph': path_to_graph(run['args'][1]),
    'metric': run['live_weight_file'],
    'queries': run['queries'],
    'epsilon': run['epsilon'],
} for run in data for algo in run['algo_runs']])

queries['instance'] = queries['graph'].map({'OSM Europe': 'OSM Eur ', 'DIMACS Europe': 'DIMACS Eur ', 'OSM Germany': 'OSM Ger '}) + queries['metric'].map({'fake_traffic': 'Syn', 'heavy_traffic': 'Fri', 'lite_traffic': 'Tue'})

queries_sub = queries.query("~(graph == 'OSM Germany' & metric == 'fake_traffic') & epsilon == 0.2")
table = queries_sub.groupby(['queries', 'instance', 'algo']) \
    .mean()[['length_increase_percent', 'num_iterations', 'num_forbidden_paths', 'running_time_ms', 'failed']] \
    .unstack()

table['failed'] *= 100
table = table.round(1)
table = table.rename(columns={ 'iterative_detour_blocking': 'IDB', 'iterative_path_blocking': 'IPB' })

output = table.to_latex()
output = output.replace('queries/1h', R"\multirow{4}{*}{\rotatebox[origin=c]{90}{1h}}")
output = output.replace('queries/4h', R"\addlinespace \multirow{4}{*}{\rotatebox[origin=c]{90}{4h}}")
output = output.replace('queries/uniform', R"\addlinespace \multirow{4}{*}{\rotatebox[origin=c]{90}{Random}}")
lines = output.split("\n")
lines = [R'\setlength{\tabcolsep}{4pt}'] + lines[:2] + [
    R" & & \multicolumn{2}{c}{Increase $[\%]$} & \multicolumn{2}{c}{Iterations} & \multicolumn{2}{c}{Blocked Paths} & \multicolumn{2}{c}{Time [ms]} & \multicolumn{2}{c}{Failed $[\%]$} \\",
    R"\cmidrule(l{3pt}r{3pt}){3-4} \cmidrule(l{3pt}r{3pt}){5-6} \cmidrule(l{3pt}r{3pt}){7-8} \cmidrule(l{3pt}r{3pt}){9-10} \cmidrule(l{3pt}r{3pt}){11-12}",
    R" & & IDB & IPB & IDB & IPB & IDB & IPB & IDB & IPB & IDB & IPB \\"
] + lines[5:]
output = add_latex_big_number_spaces("\n".join(lines) + "\n")

with open("paper/table/data.tex", 'w') as f:
  f.write(output)
