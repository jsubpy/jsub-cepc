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


stdhep_file=$JSUB_sim_input_stdhep
random_seed=$JSUB_sim_seed_jobvar

#generate simu.macro and event macro
simu_macro_template="${JSUB_input_common_dir}/simu_macro_template"
event_macro_file="${JSUB_run_dir}/event.macro"
simu_macro_file="${JSUB_run_dir}/simu.macro"

stdhep_basename=${stdhep_file##*/}
subjob_id=${stdhep_basename%.*}
lcio_output_file="$outputdir/${subjob_id}.slcio"

#if running on remote backend, the path of input/output dir is overwritten to ../
if [ "$JSUB_backend" == 'dirac'  ]; then
    stdhep_file="../${stdhep_basename}"
    lcio_output_file="../${subjob_id}.slcio"
fi

#create simu.macro from template
cp $simu_macro_template $simu_macro_file

#create event.macro from scratch
/bin/cat << END_EVENT_MACRO > $event_macro_file
/generator/generator $stdhep_file
/run/beamOn $JSUB_max_event
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

#if running on remote backend, put GearOutput.xml to ../
if [ "$JSUB_backend" == 'dirac'  ]; then
	cp "${JSUB_run_dir}/GearOutput.xml" ../
fi

