exp_dir = Dir.pwd + '/exp'
data_dir = Dir.pwd + '/data'

only_public = !ENV['ONLY_PUBLIC'].nil?

file "paper/traffic.pdf" => [
  "paper/traffic.tex"] do

  Dir.chdir "paper" do
    sh "latexmk -pdf traffic.tex"
  end
end

task default: "paper/traffic.pdf"

namespace "fig" do
end

namespace "table" do
  directory "paper/table"
end

osm_ger_src = 'https://download.geofabrik.de/europe/germany-200101.osm.pbf'
osm_ger_src_file = "#{data_dir}/germany-200101.osm.pbf"
osm_eur_src = 'http://i11www.iti.kit.edu/extra/free_roadgraphs/osm-eur.zip'
osm_eur_src_file = "#{data_dir}/osm-eur.zip"

osm_ger = "#{data_dir}/osm_ger/"
dimacs_eur = "#{data_dir}/europe/"
osm_eur = "#{data_dir}/osm_eur14/"
osm_eur_gr = "#{osm_eur}/osm-eur.gr"
osm_eur_co = "#{osm_eur}/osm-eur.co"

fake = 'fake_traffic'
lite = 'lite_traffic'
heavy = 'heavy_traffic'

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

  file "#{osm_ger}/#{lite}" => osm_ger do
    Dir.chdir "code/rust_road_router" do
      sh "cargo run --release --bin import_mapbox_live -- #{osm_ger} #{lite_live_dir} #{lite}"
    end
  end
  file "#{osm_ger}/#{heavy}" => osm_ger do
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

    file graph + "queries" => graph do
      Dir.chdir "code/rust_road_router" do
        sh "mkdir -p #{graph}/queries/1h"
        sh "mkdir -p #{graph}/queries/4h"
        sh "mkdir -p #{graph}/queries/rank"
        sh "mkdir -p #{graph}/queries/uniform"
        sh "cargo run --release --bin generate_queries -- #{graph}"
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
  task all: [:preprocessing, :epsilon, :data]

  directory "#{exp_dir}/preprocessing"
  directory "#{exp_dir}/epsilon"
  directory "#{exp_dir}/data"

  task preprocessing: ["#{exp_dir}/preprocessing", "code/rust_road_router/lib/InertialFlowCutter/build/console"] do
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
      [0.01, 0.05, 0.1, 0.2, 0.5, 1.0].each do |epsilon|
        sh "cargo run --release --bin cchpot_traffic_aware -- #{osm_eur} #{epsilon} #{fake} queries/1h > #{exp_dir}/epsilon/$(date --iso-8601=seconds).json"
      end
    end
  end

  task data: ["#{exp_dir}/data"] + graphs.map { |g, _| g + 'cch_perm' } + graphs.map { |g, _| g + 'queries' } +  graphs.flat_map { |g, metrics| metrics.map { |m| g + m } } do
    Dir.chdir "code/rust_road_router" do
      graphs.each do |graph, metrics|
        metrics.each do |metric|
          sh "cargo run --release --bin cchpot_traffic_aware -- #{graph} 0.5 #{metric} queries/1h > #{exp_dir}/epsilon/$(date --iso-8601=seconds).json"
          sh "cargo run --release --bin cchpot_traffic_aware -- #{graph} 0.5 #{metric} queries/4h > #{exp_dir}/epsilon/$(date --iso-8601=seconds).json"
          sh "cargo run --release --bin cchpot_traffic_aware -- #{graph} 0.5 #{metric} queries/uniform > #{exp_dir}/epsilon/$(date --iso-8601=seconds).json"
        end
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

