import os
import re

def path_to_graph(path):
    return {
        'ger06': 'TDGer06',
        'ptv17': 'TDEur17',
        'ptv20': 'TDEur20',
        'osm_eur14': 'OSM Europe',
        'osm_ger': 'OSM Germany',
        'osm_ger_td': 'OSM Germany',
        'europe': 'DIMACS Europe',
    }[[x for x in path.split('/') if x != ''][-1]]

def maybe_add_line_space(line, graphs):
  for graph in graphs[1:]:
    if line.startswith(graph_name_map[graph]):
      return "\\addlinespace\n" + line
  return line

def add_latex_big_number_spaces(src):
  return re.sub(re.compile('([0-9]{3}(?=[0-9]))'), '\\g<0>,\\\\', src[::-1])[::-1]

graph_selection = ['DIMACS Europe', 'OSM Europe', 'OSM Germany']
algo_names = { 'iterative_detour_blocking': 'IPB-H', 'iterative_path_blocking': 'IPB-E', 'iterative_path_fixing': 'IPF', 'smooth_path_baseline': 'OPT_w' }
algo_selection = ['IPB-E', 'IPB-H', 'IPF']
extended_algo_selection = algo_selection + ['OPT_w']
