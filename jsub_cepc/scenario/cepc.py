import os
import subprocess
from jsub.error import JsubError

CEPC_APP_DIR = os.path.dirname(os.path.realpath(__file__))


class CepcScenarioError(JsubError):
	pass

class Cepc(object):
	def __init__(self, param):
		self.scenario_input = param
		self.scenario_param = {}
	

	def build(self, backend):
		job_steps=self.scenario_input.get('job_steps')
		if type(job_steps)!=type([]):
			job_steps=[job_steps]

		#deal with splitter
		splitter=self.scenario_input.get('splitter')
		
		#cepcsoft env
		cepcsoft_version=self.scenario_input.get('cepcsoft_version')

		#initialize input sandbox
		input_sandbox={'common':{}}

		#build workflow
		workflow={}

		#cepc_sim workstep
		if 'sim' in job_steps:
			workflow['cepc_sim']={'type':'cepc_sim','actvar':{},'depend_on':[]}
			sim_input=self.scenario_input.get('sim')		
			#cepc env
			workflow['cepc_sim']['actvar']['cepcsoft_version']=cepcsoft_version
			#output dir
			workflow['cepc_sim']['actvar']['output_dir']=sim_input.get('output_dir','')
			#max event
			workflow['cepc_sim']['actvar']['max_event']=sim_input.get('max_event',-1)
			#simu macro template
			input_sandbox['common']['simu_macro_template']=sim_input.get('simu_macro')
			#input stdhep
			if 'input_stdhep_lfn' in sim_input:
				splitter['jobvar_lists']['sim_input_stdhep_lfn']={'type':'composite_string','param':{'value': sim_input.get('input_stdhep_lfn')}}
			else:
				if 'input_stdhep' not in sim_input:
					raise CepcScenarioError('input_stdhep not defined for cepc_sim.')
				else:
					splitter['jobvar_lists']['sim_input_stdhep']={'type':'composite_string','param':{'value': sim_input.get('input_stdhep')}}
			#seed
			if 'seed' not in sim_input:
				raise CepcScenarioError('seed not defined for cepc_sim.')
			else:
				splitter['jobvar_lists']['sim_seed_jobvar']={'type':'composite_string','param':{'value': sim_input.get('seed')}}
			

		#cepc_rec unit
		if 'rec' in job_steps:
			workflow['cepc_rec']={'type':'cepc_rec','actvar':{},'depend_on':[]}
			rec_input=self.scenario_input.get('rec')		
			#output dir
			workflow['cepc_rec']['actvar']['output_dir']=rec_input.get('output_dir','')
			#cepc env
			workflow['cepc_rec']['actvar']['cepcsoft_version']=cepcsoft_version
			#max event
			workflow['cepc_rec']['actvar']['max_event']=rec_input.get('max_event',-1)
			#seed
			if 'seed' not in rec_input:
				raise CepcScenarioError('seed not defined for cepc_rec.')
			else:
				splitter['jobvar_lists']['rec_seed_jobvar']={'type':'composite_string','param':{'value': rec_input.get('seed')}}
			#gear xml file
			if 'sim' in job_steps:	#connect sim and rec
				workflow['cepc_rec']['depend_on']+=['cepc_sim']
				sim_input=self.scenario_input.get('sim')		
#				workflow['cepc_rec']['actvar']['sim_outdir']=sim_input.get('output_dir','../cepc_sim')
				workflow['cepc_rec']['actvar']['sim_outdir']=sim_input.get('output_dir','./')
			else:	#rec directly	
				#rec steering file			
				if 'rec_steering_file' in rec_input:
					input_sandbox['common']['rec_steering_template']=rec_input.get('rec_steering_file')
				# get GearXMLFile from user input
				if 'gear_xml_file' in rec_input:
					input_sandbox['common']['gear_xml_file']=rec_input.get('gear_xml_file') 
				else:
					raise CepcScenarioError('gear_xml_file not defined for cepc_rec.')
				# slcio from user input
				if 'input_slcio' not in rec_input:
					raise CepcScenarioError('input_slcio not defined for cepc_rec.')
				else:
					splitter['jobvar_lists']['rec_input_slcio']={'type':'composite_string','param':{'value': sim_input.get('input_slcio')}}



		#user analysis
		if 'user_alg' in job_steps:
			workflow['cepc_alg']={'type':'cepc_alg','actvar':{},'depend_on':[]}
			alg_input=self.scenario_input.get('user_alg')
			#alg name
			workflow['cepc_alg']['actvar']['algName']=alg_input.get('algName','')
			#so file
			workflow['cepc_alg']['actvar']['soFile']=alg_input.get('soFile','')
			if 'soFile' in alg_input:
				input_sandbox['common']['soFile']=alg_input.get('soFile')
			else:
				raise CepcScenarioError('soFile not defined for cepc_alg.')
			#GearXMLFile template
			if 'GearXMLFile' in alg_input:
				input_sandbox['common']['GearXMLFile']=alg_input.get('GearXMLFile').get('template')
				workflow['cepc_alg']['actvar']['GearXMLReplace']=alg_input.get('GearXMLFile').get('replace')
			else:
				raise CepcScenarioError('GearXMLFile not defined for cepc_alg.')
			#output dir
			workflow['cepc_alg']['actvar']['outputDir']=alg_input.get('outputDir','')
			#output files
			workflow['cepc_alg']['actvar']['outputFiles']=alg_input.get('outputFiles','')
			#input data
			if 'inputData' in alg_input:
				if type(alg_input['inputData']) == type({}): 
					for key,value in alg_input['inputData'].items():
						splitter['jobvar_lists']['algInput_'+str(key)]={'type':'composite_string','param':{'value': value}}
						if backend['name']=='dirac':	
							#create a dirac_download action for each data
							workflow['dirac_download_alg_'+str(key)]={'type':'dirac_download','actvar':{},'depend_on':[]}
							workflow['cepc_alg']['depend_on']+=['dirac_download_alg_'+str(key)]	
							workflow['dirac_download_alg_'+str(key)]['actvar']['input_lfn_jobvar_name']='algInput_'+str(key)
#							workflow['dirac_download_alg_'+str(key)]['actvar']['destination']=os.path.join('../cepc_alg/',key)
							workflow['dirac_download_alg_'+str(key)]['actvar']['destination']=os.path.join('./',key)
			#upload output	
			if backend['name']=='dirac':
				workflow['dirac_upload_alg_output']={'type':'dirac_upload','actvar':{},'depend_on':['cepc_alg']}
				workflow['dirac_upload_alg_output']['actvar']['overwrite']='True'	
				workflow['dirac_upload_alg_output']['actvar']['files_to_upload']=alg_input.get('outputFiles')	
				workflow['dirac_upload_alg_output']['actvar']['destination_dir']=alg_input.get('outputDir')	
						


		#deal with dirac backend
		if backend['name']=='dirac':	
			if 'sim' in job_steps:
				#if runnning on remote, the input/output would be redirected to ./

				#download input of cepc_sim
				workflow['dirac_download_sim_input']={'type':'dirac_download','actvar':{},'depend_on':[]}
				workflow['cepc_sim']['depend_on']+=['dirac_download_sim_input']	
				if splitter['jobvar_lists'].get('sim_input_stdhep_lfn') is not None:
					workflow['dirac_download_sim_input']['actvar']['input_lfn_jobvar_name']='sim_input_stdhep_lfn'
				if splitter['jobvar_lists'].get('sim_input_stdhep') is not None:
					workflow['dirac_download_sim_input']['actvar']['input_file_jobvar_name']='sim_input_stdhep'

				#upload output of cepc_sim
				if 'rec' not in job_steps:
					workflow['dirac_upload_sim_output']={'type':'dirac_upload','actvar':{},'depend_on':['cepc_sim']}
					workflow['dirac_upload_sim_output']['actvar']['overwrite']='True'	
					workflow['dirac_upload_sim_output']['actvar']['files_to_upload']='*.slcio,GearOutput.xml'	
					#todo : output_dir

			if 'rec' in job_steps:
				#download input of cepc_rec
				if 'sim' not in job_steps:
					workflow['dirac_download_rec_input']={'type':'dirac_download','actvar':{},'depend_on':[]}
					workflow['cepc_rec']['depend_on']+=['dirac_download_rec_input']	
					workflow['dirac_download_rec_input']['actvar']['input_file_jobvar_name']='rec_input_slcio'

				#upload output of cepc_rec
				workflow['dirac_upload_rec_output']={'type':'dirac_upload','actvar':{},'depend_on':['cepc_rec']}
				workflow['dirac_upload_rec_output']['actvar']['overwrite']='True'	
				workflow['dirac_upload_rec_output']['actvar']['files_to_upload']='*\.*'	
				#todo : output_dir



		#build scenario
		self.scenario_param['input']=input_sandbox	
		self.scenario_param['splitter']=splitter
		self.scenario_param['workflow']=workflow	

		return self.scenario_param


	def validate_param(self):
		pass
