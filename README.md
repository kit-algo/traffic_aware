This repository contains the source code for the paper "Fast Computation of Shortest Smooth Paths and Uniformly Bounded Stretch with Lazy RPHAST".
Everything is tied together using `rake`.
The default `rake` tasks builds the paper.
This step also uses the output of the experiments to rebuild figures used in the paper.
The algorithmic code can be found in the `code` directory where several projects are included as submodules.
The main CH-Potentials code actually lives in https://github.com/kit-algo/rust_road_router .
For reproducibility, this repository references the version used to perform the experiments for the paper.
However, if you want to use the code you should probably just use the current master branch as it will include future developments and improvements.

### Requirements

To reproduce our results you need the following:

- A linux environment
- Recent GCC (we use `11.1.0`)
- Rust Nightly (`1.58.0`)
- Ruby (`2.5.9`) and the `rake` (`12.3.3`) Gem
- Python (`3.10.1`) with `matplotlib`, `seaborn` and `pandas`

Newer versions of these tools will likely continue to work, some past versions may do also but we cannot give any guarantees.

### Reproducing

To run experiments with publicly available data run

```bash
git submodule update --init --recursive
export ONLY_PUBLIC=1
rake exp:all
rake
```

This will download all necessary data, run experiments, generate plots and tables and finally regenerate the paper.
THIS WILL TAKE A LONG TIME!
With default parameters probably several days.
Also, processing OSM Europe requires significant amounts of RAM.
You can use the smaller graphs (uncomment the section at `Rakefile.rb:69`) and less queries by adjusting the line in `Rakefile.rb:160`.
