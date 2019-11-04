#!/bin/sh

current_dir=$(pwd)

if [ -n "$JSUB_log_dir" ]; then
    logdir="$JSUB_log_dir"
else
    logdir="$current_dir"
fi

out="$logdir/cepc_sim.out"
err="$logdir/cepc_sim.err"

if [ -n "$JSUB_output_dir" ]; then
    outputdir="$JSUB_output_dir"
else
    outputdir="$JSUB_run_dir"
fi


#initialize cepc environment
source /cvmfs/cepc.ihep.ac.cn/software/cepcenv/setup.sh
cepcenv use --default $JSUB_cepcsoft_version	



# pass accepted arguments to the exe
save_value=0
for arg in "$@"
do
    if [ "$save_value" == 1 ]; then
        stdhep_file=$arg
        save_value=0
        continue
    fi  

    if [ "--input_file" == "$arg" ]; then
        job_args="${job_args} \"$arg\""
        save_value=1
        continue
    fi 
 
    if [ "$save_value" == 2 ]; then
        random_seed=$arg
        save_value=0
        continue
    fi 
 
    if [ "--random_seed" == "$arg" ]; then
        job_args="${job_args} \"$arg\""
        save_value=2
        continue
    fi  
done


#generate simu.macro and event macro
simu_macro_template="${JSUB_input_common_dir}/simu_macro_template"
event_macro_file="${JSUB_run_dir}/event.macro"
simu_macro_file="${JSUB_run_dir}/simu.macro"

stdhep_filename=${stdhep_file##*/}
subjob_id=${stdhep_filename%.*}
lcio_output_file="$outputdir/${subjob_id}.slcio"

#create simu.macro from template
cp $simu_macro_template $simu_macro_file

#create event.macro from scratch
/bin/cat << END_EVENT_MACRO > $event_macro_file
/generator/generator $stdhep_file
/run/beamOn $JSUB_event_max
END_EVENT_MACRO


#overwrite relevant parameters in simu.macro that are defined in the task profile
sed -i "/initialMacroFile/d" $simu_macro_file
echo "/Mokka/init/initialMacroFile " $event_macro_file 	>> $simu_macro_file
sed -i "/lcioFilename/d" $simu_macro_file
echo "/Mokka/init/lcioFilename " $lcio_output_file	>> $simu_macro_file
sed -i "/randomSeed/d" $simu_macro_file
echo "/Mokka/init/randomSeed " $random_seed	>> $simu_macro_file


#execution simu macro
(time  Mokka $simu_macro_file) 1>"$out" 2>"$err"

sync
cat $out

# save the exit code
result=$?

if [ $result = 0 ]; then
    echo "JSUB_FINAL_EXECUTION_STATUS = Successful"
    exit 0
else
    echo "JSUB_FINAL_EXECUTION_STATUS = Failed ($result)"
    exit $result
fi

