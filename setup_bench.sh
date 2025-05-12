#!/bin/bash

hash=$(git log --pretty=format:'%H' -n 1 | cut -c-7)
echo "Benchmark for hash: $hash"
echo "building"
cd build-release || exit
make -j 18 verifypn-linux64 || exit
cd ..

echo "Creating run file"

run_file_name="run-$1-$hash.sh"
bin_file_name="verifypn-linux64-$1-$hash"

echo "#!/bin/bash" > "run.sh"
echo "./create_jobs.py -v ./staging/$bin_file_name -o \"$1.$hash\" -m /nfs/petrinet/mcc/2024/colour/" "${@:2}" >> "run.sh"
chmod u+x "run.sh"

echo "Uploading files"

scp "build-release/verifypn/bin/verifypn-linux64" "mcc3:staging/$bin_file_name"
scp "run.sh" "mcc3:staging/$run_file_name"
rm run.sh
