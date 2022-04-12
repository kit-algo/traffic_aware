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
queries['queries'] = queries['queries'].map({ 'queries/1h': '1h', 'queries/4h': '4h', 'queries/uniform': 'Random' })
queries['algo'] = queries['algo'].map(algo_names)

instance_order = ['DIMACS Eur Syn', 'OSM Eur Syn', 'OSM Ger Fri', 'OSM Ger Tue']
query_order = ['1h', '4h', 'Random']
algo_order = algo_selection

queries_time = queries.loc[lambda x: x['algo'].isin(algo_selection)]

per_query_grouper = ['queries', 'instance', 'epsilon', 'from', 'to']
fastest = queries_time.query('~failed & algo != "OPT_w"').groupby(per_query_grouper)[['running_time_ms']].min()
queries_time = queries_time.join(fastest, on=per_query_grouper, rsuffix='_min')
best_result = queries.query('~failed').groupby(per_query_grouper)[['length_increase_percent']].min()
queries = queries.join(best_result, on=per_query_grouper, rsuffix='_min')

queries_time['time_perf'] = queries_time.query('~failed')['running_time_ms'] / queries_time.query('~failed')['running_time_ms_min']
queries_time['time_perf'] = queries_time['time_perf'].fillna(np.inf)
queries['len_perf'] = (queries.query('~failed')['length_increase_percent'] + 100) / (queries.query('~failed')['length_increase_percent_min'] + 100)
queries['len_perf'] = queries['len_perf'].fillna(np.inf)

sub_time = queries_time.query("~(graph == 'OSM Germany' & metric == 'fake_traffic') & epsilon == 0.2")
sub_time['time_ratio'] = sub_time.groupby('algo')['time_perf'].transform(lambda group: np.sum(np.subtract.outer(group.values,group.values)>=0, axis=1) / group.count())
sub_len = queries.query("~(graph == 'OSM Germany' & metric == 'fake_traffic') & epsilon == 0.2")
sub_len['len_ratio'] = sub_len.groupby('algo')['len_perf'].transform(lambda group: np.sum(np.subtract.outer(group.values,group.values)>=0, axis=1) / group.count())

fig, axs = plt.subplots(1, 2, figsize=(11,4), sharey=True)

g = sns.lineplot(data=sub_time, x='time_perf', y='time_ratio', hue='algo', hue_order=algo_order, drawstyle='steps-post', ax=axs[0], legend=False)
g.set(xscale="log")
g.set_xlabel('Slowdown over fastest')
g.set_ylabel('Fraction of queries')
g.xaxis.set_major_formatter(mpl.ticker.LogFormatter())
g.grid(True, which="minor", linewidth=0.6)
max_x = g.get_xlim()[1]
g.set_xlim(0.95, max_x)
for line in g.get_lines()[:3]:
    (x, y) = line.get_data()
    line.set_data(np.append(x, [max_x]), np.append(y, [y[-1]]))
    
g = sns.lineplot(data=sub_len, x='len_perf', y='len_ratio', hue='algo', hue_order=extended_algo_selection, drawstyle='steps-post', ax=axs[1])
g.set_xlabel('Length increase factor over best found')
g.set_ylabel('Fraction of queries')
g.legend(title='Algorithm', loc='lower right')
max_x = g.get_xlim()[1]
g.set_xlim(0.99, max_x)
#g.set_ylim(-0.05, 1.05)
for line in g.get_lines()[:4]:
    (x, y) = line.get_data()
    line.set_data(np.append(x, [max_x]), np.append(y, [y[-1]]))
    
plt.tight_layout()
g.get_figure().savefig('paper/fig/combined_perf_profile.pdf')



sub_time['time_ratio'] = sub_time.groupby(['algo', 'instance', 'queries', 'epsilon'])['time_perf'].transform(lambda group: np.sum(np.subtract.outer(group.values,group.values)>=0, axis=1) / group.count())
sub_len['len_ratio'] = sub_len.groupby(['algo', 'instance', 'queries', 'epsilon'])['len_perf'].transform(lambda group: np.sum(np.subtract.outer(group.values,group.values)>=0, axis=1) / group.count())

g = sns.FacetGrid(sub_time, margin_titles=True, legend_out=False,
                  row='queries', col='instance', hue='algo', row_order=query_order, col_order=instance_order, hue_order=algo_order)
g.map_dataframe(sns.lineplot, x='time_perf', y='time_ratio', drawstyle='steps-post')
g.set(xscale="log")
g.set_xlabels('Slowdown over fastest')
g.set_ylabels('Fraction of queries')
g.set_titles(col_template="{col_name}", row_template="{row_name}")
g.axes[2][3].legend(title='Algorithm', loc='lower right')
for axs in g.axes:
    for ax in axs:
        ax.xaxis.set_major_formatter(mpl.ticker.LogFormatter())
        ax.grid(True, which="minor", linewidth=0.6)
        max_x = ax.get_xlim()[1]
        ax.set_xlim(0.9, max_x)
        lines = ax.get_lines()
        for line in lines:
            (x, y) = line.get_data()
            line.set_data(np.append(x, [max_x]), np.append(y, [y[-1]]))

plt.tight_layout()
g.savefig('paper/fig/detailed_perf_profile_time.pdf')


g = sns.FacetGrid(sub_len, margin_titles=True, ylim=(-0.05,1.05), legend_out=False,
                 row='queries', col='instance', hue='algo', row_order=query_order, col_order=instance_order, hue_order=extended_algo_selection)
g.map_dataframe(sns.lineplot, x='len_perf', y='len_ratio', drawstyle='steps-post')
g.set_titles(col_template="{col_name}", row_template="{row_name}")
g.set_xlabels('Length increase factor over best')
g.set_ylabels('Fraction of queries')
g.axes[2][3].legend(title='Algorithm', loc='lower right')
for axs in g.axes:
    for ax in axs:
        max_x = ax.get_xlim()[1]
        ax.set_xlim(0.98, max_x)
        lines = ax.get_lines()
        for line in lines:
            (x, y) = line.get_data()
            line.set_data(np.append(x, [max_x]), np.append(y, [y[-1]]))

plt.tight_layout()
g.savefig('paper/fig/detailed_perf_profile_quality.pdf')
