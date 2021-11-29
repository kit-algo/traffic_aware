#!/usr/bin/env python3

import pandas as pd

import json
import glob
import os
import re

from shared import *

base = "exp/"
paths = glob.glob(base + "epsilon/*.json")
data = [json.load(open(path)) for path in paths]

queries = pd.DataFrame.from_records([{
    **algo,
    'epsilon': run['epsilon'],
    'graph': path_to_graph(run['args'][1]),
} for run in data for algo in run['algo_runs']])

table = queries.query("~failed").groupby(['epsilon', 'algo']) \
    .mean()[['length_increase_percent', 'num_iterations', 'num_forbidden_paths', 'total_exploration_time_ms', 'total_ubs_time_ms', 'running_time_ms']] \
    .join(queries.groupby(['epsilon', 'algo']).mean()[['failed']])

table['failed'] *= 100
cols1 = ['total_exploration_time_ms', 'total_ubs_time_ms', 'running_time_ms', 'num_forbidden_paths']
cols2 = ['length_increase_percent', 'num_iterations']
table[cols1] = table[cols1].round(1)
table[cols2] = table[cols2].round(2)
table = table.rename(index={ 'iterative_detour_blocking': 'IDB', 'iterative_path_blocking': 'IPB' })

lines = table.rename(index=lambda x: R"\multirow{2}{*}{" + "{:.2f}".format(x) +R"}", level=0).to_latex(escape=False, column_format='ccrrrrrrr').split("\n")
lines = lines[:2] + [
  R"            & & Increase & Iterations & Blocked & \multicolumn{3}{c}{Running time [ms]} & Failed \\ \cmidrule(lr){6-8}",
  R" $\epsilon$ & &   $[\%]$ &            &   Paths & A* & UBS & Total                      & $[\%]$ \\"
] + lines[4:]
for l in range(6, 16, 2):
    lines[l] += '[2pt]'
output = add_latex_big_number_spaces("\n".join(lines) + "\n")

with open("paper/table/epsilon.tex", 'w') as f:
  f.write(output)
