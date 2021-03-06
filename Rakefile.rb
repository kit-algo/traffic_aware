exp_dir = Dir.pwd + '/exp'
data_dir = Dir.pwd + '/data'

only_public = !ENV['ONLY_PUBLIC'].nil?

file "paper/traffic.pdf" => [
  "paper/traffic.tex",
  "paper/table/epsilon.tex",
  "paper/table/graphs.tex",
  "paper/table/data.tex",
  "paper/fig/ubs_perf.pdf",
  "paper/fig/detailed_perf_profile_time.pdf",
  "paper/fig/detailed_perf_profile_quality.pdf",
  "paper/fig/combined_perf_profile.pdf",
] do
  Dir.chdir "paper" do
    sh "latexmk -pdf traffic.tex"
  end
end

task default: "paper/traffic.pdf"

namespace "fig" do
  directory "paper/fig"

  file "paper/fig/ubs_perf.pdf" => FileList[
    "#{exp_dir}/ubs_perf/*.json",
  ] + ["eval/ubs_perf.py", "paper/fig"] do
    sh "eval/ubs_perf.py"
  end

  ["paper/fig/detailed_perf_profile_time.pdf", "paper/fig/detailed_perf_profile_quality.pdf", "paper/fig/combined_perf_profile.pdf"].each do |fig|
    file fig => FileList["#{exp_dir}/data/*.json"] + ["eval/perf_profiles.py", "paper/fig"] do
      sh "eval/perf_profiles.py"
    end
  end
end

namespace "table" do
  directory "paper/table"

  file "paper/table/graphs.tex" => FileList[
    "#{exp_dir}/preprocessing/*.out",
    "#{exp_dir}/preprocessing/*.json",
  ] + ["eval/graphs.py", "paper/table"] do
    sh "eval/graphs.py"
  end

  file "paper/table/epsilon.tex" => FileList[
    "#{exp_dir}/epsilon/*.json",
  ] + ["eval/epsilon.py", "paper/table"] do
    sh "eval/epsilon.py"
  end

  file "paper/table/data.tex" => FileList[
    "#{exp_dir}/data/*.json",
  ] + ["eval/data.py", "paper/table"] do
    sh "eval/data.py"
  end
end

osm_ger = "#{data_dir}/osm_ger/"
dimacs_eur = "#{data_dir}/europe/"
osm_eur = "#{data_dir}/osm_eur14/"

fake = 'fake_traffic'
lite = 'lite_traffic'
heavy = 'heavy_traffic'

osm_ger_src = 'https://download.geofabrik.de/europe/germany-200101.osm.pbf'
osm_ger_src_file = "#{data_dir}/germany-200101.osm.pbf"
osm_eur_src = 'http://i11www.iti.kit.edu/extra/free_roadgraphs/osm-eur.zip'
osm_eur_src_file = "#{data_dir}/osm-eur.zip"
osm_eur_gr = "#{osm_eur}/osm-eur.gr"
osm_eur_co = "#{osm_eur}/osm-eur.co"

# SMALLER GRAPHS
# osm_ger_src = 'https://download.geofabrik.de/europe/germany/baden-wuerttemberg-200101.osm.pbf'
# osm_ger_src_file = "#{data_dir}/baden-wuerttemberg-200101.osm.pbf"
# osm_eur_src = 'http://i11www.iti.kit.edu/extra/free_roadgraphs/osm-bawu.zip'
# osm_eur_src_file = "#{data_dir}/osm-bawu.zip"
# osm_eur_gr = "#{osm_eur}/osm-bawu.gr"
# osm_eur_co = "#{osm_eur}/osm-bawu.co"

graphs = if only_public
  [[osm_ger, [fake]], [osm_eur, [fake]]]
else
  [[osm_ger, [fake, heavy, lite]], [osm_eur, [fake]], [dimacs_eur, [fake]]]
end

heavy_live_dir = "#{data_dir}/mapbox/live-speeds/2019-08-02-15:41/"
lite_live_dir = "#{data_dir}/mapbox/live-speeds/2019-07-16-10:21/"

namespace "prep" do
  file osm_ger_src_file => data_dir do
    sh "wget -O #{osm_ger_src_file} #{osm_ger_src}"
  end

  file osm_eur_src_file => data_dir do
    sh "wget -O #{osm_eur_src_file} #{osm_eur_src}"
  end

  directory osm_ger
  file osm_ger => ["code/osm_import/build/import_osm", osm_ger_src_file] do
    wd = Dir.pwd
    Dir.chdir osm_ger do
      if only_public
        sh "#{wd}/code/osm_import/build/import_osm #{osm_ger_src_file}"
      else
        sh "#{wd}/code/osm_import/build/import_osm #{osm_ger_src_file} #{Dir[lite_live_dir + '*'].join(' ')} #{Dir[heavy_live_dir + '*'].join(' ')}"
      end
    end
    Dir.chdir "code/rust_road_router" do
      sh "cargo run --release --bin write_unit_files -- #{osm_ger} 1000 1"
    end
  end

  file "#{osm_ger}#{lite}" => osm_ger do
    Dir.chdir "code/rust_road_router" do
      sh "cargo run --release --bin import_mapbox_live -- #{osm_ger} #{lite_live_dir} #{lite}"
    end
  end
  file "#{osm_ger}#{heavy}" => osm_ger do
    Dir.chdir "code/rust_road_router" do
      sh "cargo run --release --bin import_mapbox_live -- #{osm_ger} #{heavy_live_dir} #{heavy}"
    end
  end

  directory osm_eur
  file osm_eur => ["code/RoutingKit/bin", osm_eur_src_file] do
    wd = Dir.pwd
    Dir.chdir osm_eur do
      sh "unzip -j #{osm_eur_src_file}"
      sh "#{wd}/code/RoutingKit/bin/convert_road_dimacs_graph #{osm_eur_gr} first_out head travel_time"
      sh "#{wd}/code/RoutingKit/bin/convert_road_dimacs_coordinates #{osm_eur_co} latitude longitude"
    end
    Dir.chdir "code/rust_road_router" do
      sh "cargo run --release --bin write_unit_files -- #{osm_eur} 10 1"
      sh "cargo run --release --bin generate_geo_distances -- #{osm_eur}"
    end
  end

  graphs.each do |graph, _|
    file graph + fake => graph do
      Dir.chdir "code/rust_road_router" do
        sh "cargo run --release --bin generate_fake_traffic -- #{graph} #{fake}"
      end
    end

    file graph + 'lower_bound' => graph do
      sh "ln -s #{graph}travel_time #{graph}lower_bound" unless File.exist? "#{graph}lower_bound"
    end

    file graph + "queries" => graph do
      Dir.chdir "code/rust_road_router" do
        sh "mkdir -p #{graph}/queries/1h"
        sh "mkdir -p #{graph}/queries/4h"
        sh "mkdir -p #{graph}/queries/rank"
        sh "mkdir -p #{graph}/queries/uniform"
        sh "cargo run --release --bin generate_queries -- #{graph} 1000"
      end
    end

    file graph + "cch_perm" => [graph, "code/rust_road_router/lib/InertialFlowCutter/build/console"] do
      Dir.chdir "code/rust_road_router" do
        sh "./flow_cutter_cch_order.sh #{graph} #{Etc.nprocessors}"
      end
    end
  end
end

namespace "exp" do
  desc "Run all experiments"
  task all: [:ubs_perf, :epsilon, :data, :preprocessing]

  directory "#{exp_dir}/preprocessing"
  directory "#{exp_dir}/epsilon"
  directory "#{exp_dir}/data"
  directory "#{exp_dir}/ubs_perf"

  task preprocessing: ["#{exp_dir}/preprocessing", "code/rust_road_router/lib/InertialFlowCutter/build/console"] +
                       graphs.map { |g, _| g + 'lower_bound' } +
                       graphs.flat_map { |g, metrics| metrics.map { |m| g + m } } do
    graphs.each do |graph, _|
      10.times do
        Dir.chdir "code/rust_road_router" do
          filename = "#{exp_dir}/preprocessing/" + `date --iso-8601=seconds`.strip + '.out'
          sh "echo '#{graph}' >> #{filename}"
          sh "./flow_cutter_cch_order.sh #{graph} 1 >> #{filename}"
          filename = "#{exp_dir}/preprocessing/" + `date --iso-8601=seconds`.strip + '.json'
          sh "cargo run --release --features cch-disable-par --bin cch_preprocessing -- #{graph} >> #{filename}"
        end
      end
    end
  end

  task epsilon: ["#{exp_dir}/epsilon", osm_eur + "cch_perm", osm_eur + "queries", osm_eur + fake] do
    Dir.chdir "code/rust_road_router" do
      [1.0, 0.5, 0.2, 0.1, 0.05, 0.01].each do |epsilon|
        sh "cargo run --release --bin cchpot_traffic_aware -- #{osm_eur} #{epsilon} #{fake} queries/1h > #{exp_dir}/epsilon/$(date --iso-8601=seconds).json"
      end
    end
  end

  task data: ["#{exp_dir}/data"] + graphs.map { |g, _| g + 'cch_perm' } + graphs.map { |g, _| g + 'queries' } +  graphs.flat_map { |g, metrics| metrics.map { |m| g + m } } do
    Dir.chdir "code/rust_road_router" do
      graphs.each do |graph, metrics|
        metrics.each do |metric|
          [0.2, 0.5].each do |epsilon|
            ['1h', '4h', 'uniform'].each do |queries|
              sh "cargo run --release --bin cchpot_traffic_aware -- #{graph} #{epsilon} #{metric} queries/#{queries} > #{exp_dir}/data/$(date --iso-8601=seconds).json"
              sh "cargo run --release --bin cchpot_traffic_aware_baseline -- #{graph} #{epsilon} #{metric} queries/#{queries} > #{exp_dir}/data/$(date --iso-8601=seconds).json"
            end
          end
        end
      end
    end
  end

  task ubs_perf: ["#{exp_dir}/ubs_perf", osm_eur + "cch_perm", osm_eur + "queries", osm_eur + fake] do
    Dir.chdir "code/rust_road_router" do
      [0.2, 0.5].each do |epsilon|
        sh "cargo run --release --bin ubs_performance -- #{osm_eur} #{epsilon} #{fake} > #{exp_dir}/ubs_perf/$(date --iso-8601=seconds).json"
      end
    end
  end
end

namespace 'build' do
  task :osm_import => "code/osm_import/build/import_osm"

  directory "code/osm_import/build"

  file "code/osm_import/build/import_osm" => ["code/osm_import/build", "code/osm_import/src/bin/import_osm.cpp"] do
    Dir.chdir "code/osm_import/build/" do
      sh "cmake -DCMAKE_BUILD_TYPE=Release .. && make"
    end
  end

  task routingkit: "code/RoutingKit/bin"
  file "code/RoutingKit/bin" do
    Dir.chdir "code/RoutingKit/" do
      sh "./generate_make_file"
      sh "make"
    end
  end

  task :inertialflowcutter => "code/rust_road_router/lib/InertialFlowCutter/build/console"

  directory "code/rust_road_router/lib/InertialFlowCutter/build"
  desc "Building Flow Cutter Accelerated"
  file "code/rust_road_router/lib/InertialFlowCutter/build/console" => "code/rust_road_router/lib/InertialFlowCutter/build" do
    Dir.chdir "code/rust_road_router/lib/InertialFlowCutter/build" do
      sh "cmake -DCMAKE_BUILD_TYPE=Release .. && make console"
    end
  end
end

