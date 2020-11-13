#!/usr/bin/env python

import os
import sys
import ast
import re

def main():
	algName=os.environ.get('JSUB_algName')	
	output_dir=os.environ.get('JSUB_outputDir')	
	output_files=os.environ.get('JSUB_outputFiles')	

	run_dir=os.environ.get('JSUB_run_dir')
	input_dir=os.environ.get('JSUB_input_common_dir')

	soFile=os.path.join(input_dir,'soFile')
	GearXMLFile=os.path.join(input_dir,'GearXMLFile')
	GearXMLReplace=os.environ.get('JSUB_GearXMLReplace')
	

	#initialize cepc environment
	os.system('source /cvmfs/cepc.ihep.ac.cn/software/cepcenv/setup.sh')
	os.system('cepcenv use --default {}'.format(os.environ.get('JSUB_cepcsoft_version')))

	#include so file to marlin dll
	os.system('export MARLIN_DLL={}:$MARLIN_DLL'.format(soFile))

	#cp steering file to current dir
	os.system('cp {} .'.format(GearXMLFile))	
	#replace texts in GearXMLFile
	#	- replace $(jobvar) to actual values
	regex='\$\(([^)]+)'
	regex2='\$\{([^}]+)'
	while re.search(regex,GearXMLReplace):
		match=re.search(regex,GearXMLReplace)
		var_name=match.group(0)[2:]
		s=GearXMLReplace.replace('$('+var_name+')',os.environ.get('JSUB_'+var_name,''))
		GearXMLReplace=s	
#	while re.search(regex,GearXMLReplace):
#		match=re.search(regex,GearXMLReplace)
#		var_name=match.group(0)[2:]
#		s=GearXMLReplace.replace('${'+var_name+'}',os.environ.get('JSUB_'+var_name,''))
#		GearXMLReplace=s	
	#	- str to dict
	GearXMLReplace=ast.literal_eval(GearXMLReplace)  
	#	- run sed
	for key,value in GearXMLReplace.items():
		os.system('sed -i s/{}/{}/g ./GearXMLFile'.format(key,value)}

	#run Marlin
	os.system('Marlin GearXMLFile')
	
	

	return 0

if __name__ == '__main__':
    exit(main())

