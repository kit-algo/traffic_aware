#!/usr/bin/env python3

import pandas as pd

import json
import glob
import os
import re

from shared import *

base = "exp/"
paths = glob.glob(base + "preprocessing/*.json")
data = [json.load(open(path)) for path in paths]

graphs = pd.DataFrame.from_records([{
    **run,
    'graph': path_to_graph(run['args'][1]),
    'num_nodes': run['graph']['num_nodes'],
    'num_edges': run['graph']['num_arcs'],
} for run in data if 'graph' in run])

runtime_pattern = re.compile(".*running time : (\\d+)musec.*")

def parse_flowcutter_partition_output(path):
  stats = { 'cch_ordering_running_time_s': 0.0 }

  with open(path, 'r') as f:
    for line in f:
      if not 'graph' in stats:
        stats['graph'] = path_to_graph(line.strip())
      else:
        match = runtime_pattern.match(line)
        if match:
          stats['cch_ordering_running_time_s'] += int(match[1]) / 1000000

  return stats

cch_ordering = pd.DataFrame.from_records([parse_flowcutter_partition_output(path) for path in glob.glob(base + "preprocessing/*.out")])

table = graphs.groupby(['graph'])[['basic_customization_running_time_ms', 'contraction_running_time_ms', 'graph_build_running_time_ms',
    'perfect_customization_running_time_ms', 'respecting_running_time_ms', 'num_nodes', 'num_edges']].mean()

table = table.reindex(graph_selection)

table = table.join(cch_ordering.groupby('graph').mean())
table['num_nodes'] = table['num_nodes'] / 1000000.0
table['num_edges'] = table['num_edges'] / 1000000.0
table['cch_phase1_s'] = table['cch_ordering_running_time_s'] + (table['contraction_running_time_ms'] / 1000)
table['cch_phase2_s'] = (table['respecting_running_time_ms'] + table['basic_customization_running_time_ms'] + table['perfect_customization_running_time_ms'] + table['graph_build_running_time_ms']) / 1000
table = table.reindex(columns=['num_nodes', 'num_edges', 'cch_phase1_s', 'cch_phase2_s'])
table = table.round(1)

lines = table.to_latex(escape=False).split("\n")

lines = lines[:2] + [
  R" & Nodes          & Edges          & \multicolumn{2}{c}{Preprocessing [s]} \\ \cmidrule(lr){4-5}"
  R" & $[\cdot 10^6]$ & $[\cdot 10^6]$ & Phase 1 & Phase 2 \\"
] + lines[4:]

output = add_latex_big_number_spaces("\n".join(lines) + "\n")

with open("paper/table/graphs.tex", 'w') as f:
  f.write(output)
