#!/bin/sh

echo Start executing cepc_sim.sh.

evtmax=$JSUB_evtmax
gearOutput=$JSUB_gear_output

eval seed='$JSUB_'$JSUB_seed_jobvar
eval output='$JSUB_'$JSUB_output_jobvar
eval outputLFN='$JSUB_'$JSUB_outputLFN_jobvar
eval inputLFN='$JSUB_'$JSUB_inputLFN_jobvar
eval input='$JSUB_'$JSUB_input_jobvar
eval stdhep_file='$JSUB_'$JSUB_stdhepFile_jobvar
eval start_event_number='$JSUB_'$JSUB_start_event_number_jobvar

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



#generate simu.macro and event macro
simu_macro_template="${JSUB_input_common_dir}/simu_macro"
event_macro_file="${JSUB_run_dir}/event.macro"
simu_macro_file="${JSUB_run_dir}/simu.macro"

stdhep_basename=${stdhep_file##*/}
subjob_id=${stdhep_basename%.*}
lcio_output_file="$outputdir/${output}"

#if running on remote backend, the path of input/output dir is overwritten to ./
if [ "$JSUB_backend" == 'dirac'  ]; then
    stdhep_file="`pwd`/${stdhep_basename}"
    lcio_output_file="`pwd`/${output}"
#    stdhep_file="./${stdhep_basename}"
#    lcio_output_file="./${output}"

	# add file type to lcio_output_file
	if [[ ! $lcio_output_file =~ .*slcio  ]]; then
	    lcio_output_file=$lcio_output_file'.slcio'
	fi

fi

#create simu.macro from template
cp $simu_macro_template $simu_macro_file

#create event.macro from scratch
/bin/cat << END_EVENT_MACRO > $event_macro_file
/generator/generator $stdhep_file
/run/beamOn $JSUB_evtMax
/run/verbose 0
/event/verbose 0
/tracking/verbose 0
END_EVENT_MACRO

cat $event_macro_file ###

#text replacement in simu.macro
for idx in `seq 0 30`; do
    eval rtext='$JSUB_cepcSim_rtext_'$idx
    eval textr='$JSUB_cepcSim_textr_'$idx
    if [  ${#rtext} -gt 0 ]; then
        # text replacement
        echo $rtext| sed 's/\//\\\//g' > rtext0
        rtext=`cat rtext0`
        rm rtext0
        echo $textr| sed 's/\//\\\//g' > textr0
        textr=`cat textr0`
        rm textr0
        sed -i 's/'$rtext'/'$textr'/g' $simu_macro_file
    fi  
done


#overwrite relevant parameters in simu.macro that are defined in the task profile
sed -i "/initialMacroFile/d" $simu_macro_file
echo "/Mokka/init/initialMacroFile " $event_macro_file 	>> $simu_macro_file
sed -i "/lcioFilename/d" $simu_macro_file
echo "/Mokka/init/lcioFilename " $lcio_output_file	>> $simu_macro_file
sed -i "/randomSeed/d" $simu_macro_file
echo "/Mokka/init/randomSeed " $seed	>> $simu_macro_file
sed -i "/startEventNumber/d" $simu_macro_file
echo "/Mokka/init/startEventNumber " $start_event_number    >> $simu_macro_file
sed -i "/MokkaGearFileName/d" $simu_macro_file
echo "/Mokka/init/MokkaGearFileName " $JSUB_gear_output    >> $simu_macro_file

mkdir -p "$(dirname "$lcio_output_file")"
mkdir -p "$(dirname "$JSUB_gear_output")"

# replace exit to the end of the simu.macro file
sed -i "/exit/d" $simu_macro_file
echo "exit "  >> $simu_macro_file
cat $simu_macro_file

#execution simu macro
echo Command =  Mokka $JSUB_additional_args $simu_macro_file
which Mokka
echo out=$out, err=$err
(time  Mokka $JSUB_additional_args $simu_macro_file) 1>"$out" 2>"$err"

sync
cat $out ###


echo ls:		###
ls -l
echo pwd:
pwd

# save the exit code
result=$?

if [ $result = 0 ]; then
    echo "JSUB_FINAL_EXECUTION_STATUS = Successful"
    exit 0
else
    echo "JSUB_FINAL_EXECUTION_STATUS = Failed ($result)"
    exit $result
fi


