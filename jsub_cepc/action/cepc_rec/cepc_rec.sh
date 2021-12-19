#!/bin/sh

echo Start executing cepc_rec.sh.

evtmax=$JSUB_evtmax

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


eval input='$JSUB_'$JSUB_input_jobvar
eval lciooutput='$JSUB_'$JSUB_output_jobvar
eval rootoutput='$JSUB_'$JSUB_rootfile_jobvar
echo rootoutput=$rootoutput
eval seed='$JSUB_'$JSUB_seed_jobvar
echo seed=$seed
eval gear_input_from_sim='$JSUB_'$JSUB_gear_file_jobvar
input_file=$input #input file should be slcio file, if rec without sim
if [[ ! $input_file =~ .*slcio  ]]; then
    input_file=$input_file'.slcio'
fi
if [ -n "$JSUB_sim_outdir" ]; then #otherwise use the input file of sim for basename
	input_file=$JSUB_sim_input_stdhep
fi

#generate rec steering file from template
rec_steering_template="${JSUB_input_common_dir}/rec_steer_file"
rec_steering_file="${JSUB_run_dir}/reco.xml"

input_filename=${input_file##*/}
subjob_id=${input_filename%.*}
# would overwrite default lcio_output name with setting
if [ -n "$lciooutput" ]; then
#	lcio_output_file=$lciooutput
	subjob_id=${lciooutput%.*.*}
	if [ "$subjob_id" == $lciooutput ]; then
		subjob_id=${lciooutput%.*}
	fi
fi
lcio_output_file="$outputdir/${subjob_id}.rec.slcio"
dst_output_file="$outputdir/${subjob_id}.dst.slcio"
inv_mass_output_file="$outputdir/${subjob_id}.inv_mass.root"
lich_output_file="$outputdir/${subjob_id}.lich.root"


slcio_input_file=$input_file
gear_xml_file="${JSUB_input_common_dir}/gear_file"

if [ -n "$gear_input_from_sim" ]; then
	gear_xml_file=$gear_input_from_sim
fi

#if running on remote backend, the path of input/output dir is overwritten to ./
if [ "$JSUB_backend" == 'dirac'  ]; then
	slcio_input_file=${slcio_input_file##*/}
	lcio_output_file=${lcio_output_file##*/}
	dst_output_file=${dst_output_file##*/}
	inv_mass_output_file=${inv_mass_output_file##*/}
	lich_output_file=${lich_output_file##*/}
fi


# create rec steering file from template
cp $rec_steering_template $rec_steering_file

# text replacement in rec steering file
for idx in `seq 0 30`; do
    eval rtext='$JSUB_cepcRec_rtext_'$idx
    eval textr='$JSUB_cepcRec_textr_'$idx
    if [  ${#rtext} -gt 0 ]; then
        # text replacement
        echo $rtext| sed 's/\//\\\//g' > rtext0
        rtext=`cat rtext0`
        rm rtext0
        echo $textr| sed 's/\//\\\//g' > textr0
        textr=`cat textr0`
        rm textr0
        sed -i 's/'$rtext'/'$textr'/g' $rec_steering_file
    fi  
done


#overwrite relevant parameters in rec steering file
sed -i "/LCIOInputFiles/{n;s+.*+$slcio_input_file+}" $rec_steering_file

sed -i "/MyLCIOOutputProcessor.*type/,/\/processor/ {/LCIOOutputFile/{n;s+.*+$lcio_output_file+}}" $rec_steering_file
#sed -i "/DSTOutput.*type/,/\/processor/ {/LCIOOutputFile/{n;s+.*+$dst_output_file+}}" $rec_steering_file
#sed -i "/MyTotalInvMass.*type/,/\/processor/ {/TreeOutputFile/{n;s+.*+$inv_mass_output_file+}}" $rec_steering_file
#sed -i "/MyLICH/,/\/processor/ {/TreeOutputFile/{n;s+.*+$lich_output_file+}}" $rec_steering_file
sed -i "/GearXMLFile/{s+value.*=\".*\"+value=\"$gear_xml_file\"+}" $rec_steering_file
if [ -n "$rootoutput" ]; then 
	sed -i "/rootFileName/{s+value.*=\".*\"+value=\"$rootoutput\"+}" $rec_steering_file
fi
sed -i "/RandomSeed/{s/value=\".*\"/value=\"$seed\"/}" $rec_steering_file


mkdir -p "$(dirname "$lcio_output_file")"
mkdir -p "$(dirname "$lich_output_file")"
mkdir -p "$(dirname "$dst_output_file")"
mkdir -p "$(dirname "$inv_mass_output_file")"
if [ -n "rootoutput" ]; then
	mkdir -p "$(dirname "$rootoutput")"
fi
#cat $rec_steering_file

#execution simu macro
echo Command: Marlin $rec_steering_file
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

