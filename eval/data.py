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
table = queries_sub.query('~failed').groupby(['queries', 'instance', 'algo']).mean()[['length_increase_percent']].join( \
    queries_sub.groupby(['queries', 'instance', 'algo']) \
    .mean()[['running_time_ms', 'failed']]) \
    .unstack()

table['failed'] *= 100
table = table.round(1)
table = table.rename(columns=algo_names)
table = table.reindex(columns=algo_selection, level=1)

output = table.to_latex(column_format=R'llr@{\hskip8pt}r@{\hskip8pt}rr@{\hskip8pt}r@{\hskip8pt}rr@{\hskip8pt}r@{\hskip8pt}r')
output = output.replace('queries/1h', R"\multirow{4}{*}{\rotatebox[origin=c]{90}{1h}}")
output = output.replace('queries/4h', R"\addlinespace \multirow{4}{*}{\rotatebox[origin=c]{90}{4h}}")
output = output.replace('queries/uniform', R"\addlinespace \multirow{4}{*}{\rotatebox[origin=c]{90}{Random}}")
lines = output.split("\n")
lines = lines[:2] + [
    R" & & \multicolumn{3}{c}{Increase $[\%]$} & \multicolumn{3}{c}{Running time [ms]} & \multicolumn{3}{c}{Failed $[\%]$} \\",
    R"\cmidrule(lr){3-5} \cmidrule(lr){6-8} \cmidrule(lr){9-11}",
    R" & & IPB-E & IPB-H & IPF & IPB-E & IPB-H & IPF & IPB-E & IPB-H & IPF \\"
] + lines[5:]
output = add_latex_big_number_spaces("\n".join(lines) + "\n")

with open("paper/table/data.tex", 'w') as f:
  f.write(output)
