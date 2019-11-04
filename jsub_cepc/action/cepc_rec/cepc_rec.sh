#!/bin/sh


current_dir=$(pwd)

if [ -n "$JSUB_log_dir" ]; then
    logdir="$JSUB_log_dir"
else
    logdir="$current_dir"
fi

out="$logdir/cepc_rec.out"
err="$logdir/cepc_rec.err"

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
        input_file=$arg	#input file may be stdhep file or slcio file
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



#generate rec steering file from template
rec_steering_template="${JSUB_input_common_dir}/rec_steering_template"
rec_steering_file="${JSUB_run_dir}/reco.xml"

input_filename=${input_file##*/}
subjob_id=${input_filename%.*}
lcio_output_file="$outputdir/${subjob_id}.rec.slcio"
dst_output_file="$outputdir/${subjob_id}.dst.slcio"
inv_mass_output_file="$outputdir/${subjob_id}.ana.root"
lich_output_file="$outputdir/${subjob_id}.lich_output"

if [ -n "$JSUB_sim_outdir" ]; then
	#connecting sim and rec
	slcio_input_file="$JSUB_sim_outdir/${subjob_id}.slcio"
	JSUB_cepc_sim_dir=`echo $JSUB_run_dir| sed 's/cepc_rec/cepc_sim/g'`
	gear_xml_file="$JSUB_cepc_sim_dir/GearOutput.xml"
else
	slcio_input_file=$input_file
	gear_xml_file=$JSUB_gear_xml_file
fi


cp $rec_steering_template $rec_steering_file

#overwrite relevant parameters in rec steering file
sed -i "/LCIOInputFiles/{n;s+.*+$slcio_input_file+}" $rec_steering_file
sed -i "/MyLCIOOutputProcessor/,/\/processor/ {/LCIOOutputFile/{n;s+.*+$lcio_output_file+}}" $rec_steering_file
sed -i "/DSTOutput/,/\/processor/ {/LCIOOutputFile/{n;s+.*+$dst_output_file+}}" $rec_steering_file
sed -i "/MyTotalInvMass/,/\/processor/ {/TreeOutputFile/{n;s+.*+$inv_mass_output_file+}}" $rec_steering_file
sed -i "/MyLICH/,/\/processor/ {/TreeOutputFile/{n;s+.*+$lich_output_file+}}" $rec_steering_file
sed -i "/GearXMLFile/{s+value=\".*\"+value=\"$gear_xml_file\"+}" $rec_steering_file
sed -i "/RandomSeed/{s/value=\".*\"/value=\"$random_seed\"/}" $rec_steering_file


#execution simu macro
(time  Marlin $rec_steering_file) 1>"$out" 2>"$err"

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

