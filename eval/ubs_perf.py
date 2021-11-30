#!/usr/bin/env python3

import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt
import seaborn as sns
sns.set()

import pandas as pd

import json
import glob
import os
import re

from shared import *

base = "exp/"
paths = glob.glob(base + "ubs_perf/*.json")
data = [json.load(open(path)) for path in paths]

ubs_checks = pd.DataFrame.from_records([{
    **algo,
    'graph': path_to_graph(run['args'][1]),
    'metric': run['live_weight_file'],
    'epsilon': run['epsilon'],
} for run in data for algo in run['algo_runs']])
ubs_checks['rank_exp'] = ubs_checks['rank'].apply(lambda val: f"$2^{{{val}}}$")

def pretty(val, pos):
    if val < 1.0:
        return f"{val}ms"
    elif val >= 1000:
        return f"{int(val/1000.0)}s"
    else: 
        return f"{int(val)}ms"
    
plt.figure(figsize=(11,5))
g = sns.boxplot(data=ubs_checks.query('rank > 9 & epsilon == 0.2'), x='rank_exp', y='running_time_ms', hue='algo', 
                hue_order=['sse_rphast', 'lazy_rphast_naive', 'dijkstra_tree', 'lazy_rphast_tree'], 
                showmeans=False, linewidth=0.8, flierprops=dict(marker='o', markerfacecolor='none', markeredgewidth=0.3))
g.set_yscale('log')
handles, labels = g.get_legend_handles_labels()
g.legend(handles=handles, labels=['SSE RPHAST', 'Lazy RPHAST Naive', 'UBS Trees Dijkstra', 'UBS Trees Lazy RPHAST'])
g.set_ylabel('Running Time')
g.set_xlabel('Rank')
g.yaxis.set_major_locator(mpl.ticker.LogLocator(base=10,numticks=10))
g.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(pretty))
plt.tight_layout()
g.get_figure().savefig('paper/fig/ubs_perf.pdf')
