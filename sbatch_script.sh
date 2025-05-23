#!/bin/bash
#SBATCH --mail-type=FAIL  # Type of email notification: BEGIN,END,FAIL,ALL
#SBATCH --mail-user=jhajri20@student.aau.dk
#SBATCH --partition=naples  # If you need run-times to be consistent across tests, you may need to restrict to one partition.
#SBATCH --mem=16G  # Memory limit that slurm allocates
#SBATCH --time=0:17:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2

let "m=1024*1024*15"
ulimit -v $m
for QUERY_INDEX in $(seq $QUERY_COUNT) ;
do
    line="\n###### RUNNING $SLURM_JOB_NAME X $QUERY_INDEX ######"
    echo -e "$line"
    echo -e "$line" >&2
    /usr/bin/time --format="TOTAL_TIME: %es\nMAX_MEMORY: %MkB" timeout 60 $VERIFYPN_PATH -x $QUERY_INDEX $MODEL_FILE_PATH $QUERY_FILE_PATH $VERIFYPN_OPTIONS
    EXECUTION_RESULT=$?
    if [ $EXECUTION_RESULT = 124 ]; then
        echo "TIMEOUT"
    elif [ $EXECUTION_RESULT = 130 ]; then
        exit 130
    elif [ "$EXECUTION_RESULT" -gt "2" ]; then
        echo "ERROR"
    fi
done
