#!/bin/bash
echo starting job $2
mkdir -p jobs
declare -x SLURM_JOB_NAME="$2"
declare -px > "jobs/$2.sh"
echo "$7" "2>$4" "1>$6" >> "jobs/$2.sh"
chmod u+x "jobs/$2.sh"