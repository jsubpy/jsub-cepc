import os
import subprocess
from jsub.error import JsubError
from copy import copy,deepcopy
from random import randint

CEPC_APP_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_SOFT_VERSION='0.1.1'

class CepcScenarioError(JsubError):
	pass

class Cepc(object):
	def __init__(self, param):
		self.scenario_input = param
		self.scenario_param = {}
		self.output_name_from_input=False
		self.index_jobvar=None

	def registerStepJobvar(self,step_name,attribute,step_setting,value):
		'''
			register jobvar for the attribute in step.
			Example:
				myCepcSim:
					type: cepcSim
					seed: '$(seed)'
			  	==>
				myCepcSim_seed_jobvar='$(seed)' in splitter.jobvar
				stepSetting.actvar.seed_jobvar = 'myCepcSim_seed_jobvar'

			if splitter mode is not splitByJobvars: 
				stepSetting.actvar.attribute = value
		'''
		result=step_setting


		splitterMode=self.splitter.get('mode')
		if splitterMode in ['splitByJobvars']:
			self.splitter['jobvar_lists'].update({step_name+'_'+attribute+'_jobvar':{'type':'composite_string','param':{'value':str(value)},'priority':0}})
			result['actvar'][attribute+'_jobvar']=step_name+'_'+attribute+'_jobvar'
		else:
			result['actvar'][attribute]=value
		return result



	def build_common_step_setting(self,step_name,step_desc,backend):
		'''
		  function used by build(), to generate common settings for a workflow step
		'''
		p_steps=copy(self.previous_steps)
		result={'actvar':{},'depend_on':p_steps}
		# evtmax should come from general setting, or overwritten by step setting
		s_evtMax = step_desc.get('evtMax',self.evtMax)
		s_evtMax = step_desc.get('maxEvent',s_evtMax)
		s_evtMax = step_desc.get('evtMaxPerJob',s_evtMax)
		result['actvar']['evtMax'] = s_evtMax
		# step_type
		result['type']=step_desc.get('type')
		# redirect output in step to ./ on WN
		if backend['name']=='dirac':
	   		result['actvar']['dirac_backend']='True'

		# every step may use a random seed; either from yaml setting or as an auto-generated one
		seed = randint(0,20000000)  #use rand to assure unique seed
		seed = step_desc.get('seed',seed)
		result=self.registerStepJobvar(step_name,'seed',result,seed)

		# start event number
		start_event_num = step_desc.get('startEventNumber',None)
		if start_event_num:
			result=self.registerStepJobvar(step_name,'start_event_number',result,start_event_num)
		# input
		myinput = step_desc.get('input',None)
		if myinput:
			result=self.registerStepJobvar(step_name,'input',result,myinput)
			self.output_name_from_input=True

		# inputLFN
		inputLFN = step_desc.get('inputLFN',None)
		if inputLFN:
			result=self.registerStepJobvar(step_name,'inputLFN',result,inputLFN)
			self.output_name_from_input=True
			self.dirac_download_dict.update({step_name+'_input':step_name+'_inputLFN_jobvar'})

		# output
		output = step_desc.get('output',None)
		if output:
			result=self.registerStepJobvar(step_name,'output',result,output)
		# outputLFN
		outputLFN = step_desc.get('outputLFN',None)
		if outputLFN:
			result=self.registerStepJobvar(step_name,'output_lfn',result,outputLFN)

		return result

	def build(self, backend):
		job_steps=self.scenario_input.get('job_steps')
		if type(job_steps)!=type([]):
			job_steps=[job_steps]

		#cepc env
		use_cepcsoft=False
		use_cepcsw=False
		softVersion=None
		if 'softVersion' not in self.scenario_input:
			# use default version.
			softVersion=DEFAULT_SOFT_VERSION
			use_cepcsoft=True
		else:
			# distringuish CEPCSOFT and CEPCSW through softVersion
			softVersionRaw=self.scenario_input.get('softVersion')
			if type(softVersionRaw)==str:
				if 'CEPCSW' not in softVersionRaw.upper():
					use_cepcsoft=True
				else:
					use_cepcsw=True
				softVersion=softVersionRaw
			elif type(softVersionRaw)==dict:
				toolkit=softVersionRaw.get('toolkit','cepcsoft')	
				if 'CEPCSW' in toolkit.upper():
					use_cepcsoft=True
				elif 'CEPCSOFT' in toolkit.upper():
					use_cepcsw=True
				softVersion=softVersionRaw.get('release')
			
			if (not (use_cepcsoft or use_cepcsw)) or (not softVersion):
				raise CepcScenarioError('Invalid CEPC environment setting.')
			
		# build input sandbox
		yaml_input = self.scenario_input.get('input')
		input_sandbox={'common':{}}
		if type(yaml_input) is dict:
			input_sandbox['common'].update(yaml_input)

		# deal with splitter
		self.splitter=self.scenario_input.get('splitter')
		splitterMode=self.splitter.get('mode','splitByEvent')
		if splitterMode in ['splitByEvent','spliteByEvent','spliteByEvents','spliteByEvent']:
			splitterMode='splitByEvent'
			jobvarsToSeq={}
			jobvars={}
			index0=0
		elif splitterMode in ['splitByJobvars','splitByJobvar','spliteByJobvar','spliteByJobvars']:
			splitterMode='splitByJobvars'
			if 'jobvarLists' in self.splitter:
				self.splitter['jobvar_lists']=self.splitter['jobvarLists']
			if not self.splitter.get('jobvar_lists'):
				raise CepcScenarioError('Jobvar lists not defined in the splitter.')
		else:
			raise CepcScenarioError('Invalid splitter mode: %s'%splitterMode)



		# general setting
		outputSubDir= self.scenario_input.get('outputSubDir','')
		outputDir= self.scenario_input.get('outputDir','')

		# univ_index, for consistent file name number across sim/rec/ana
		if splitterMode in ['splitByJobvars']:
			self.splitter['jobvar_lists']['univ_index']={'type':'range','param':{'first':0}}
			self.index_jobvar='univ_index'	# can be seed instead.
		# users may define evtmax in splitter for their conveniences, or in general setting
		evtMax=self.splitter.get('evtMax',10)
		evtMax=self.splitter.get('maxEvent',10)
		evtMax=self.splitter.get('evtMaxPerJob',evtMax)
		evtMax=self.scenario_input.get('evtMax',evtMax)
		evtMax=self.scenario_input.get('evtMaxPerJob',evtMax)
		self.evtMax=evtMax

		# build workflow
		workflow={}
		workflow_input=self.scenario_input.get('workflow',{})
		input_map={'cepc_rec':'cepc_sim'}
		self.dirac_download_dict={} #{key:fname_jobvar}
		self.dirac_upload_dict={} #{file_to_upload:dir}, can use wildcard

		job_steps=workflow_input.get('steps',[])
		job_steps=workflow_input.get('step',job_steps)
		job_steps=workflow_input.get('jobSteps',job_steps)
		# translate job_steps to standard list
		if type(job_steps)==str:
			job_steps.replace('[','')
			job_steps.replace(']','')
			job_steps=job_steps.split(',')
		elif type(job_steps)==list:
			pass

		sim_in_workflow=False
		cepcSim_counter=0	# idx for text replacement in steering file of cepcSim
		cepcRec_counter=0	# idx for text replacement in steering file of cepcRec
		cepcAna_counter=0	# idx for text replacement in steering file of cepcAna
		self.previous_steps=[]
		for step in job_steps:
#			step=step.lower()
			p_steps=copy(self.previous_steps)
			self.previous_steps+=[step]

			# apply default settings:
			step_desc=workflow_input.get(step,{})
			step_setting=self.build_common_step_setting(step,step_desc,backend)
			step_type = step_desc.get('type','')
			step_setting['depend_on']=p_steps

			# handling outputLFN
			if 'outputLFN' in step_desc:
				self.splitter['jobvar_lists'][step+'_outputLFN_jobvar']={'type':'composite_string','param':{'value':step_desc.get('outputLFN')},'priority':0}
				self.dirac_upload_dict.update({step+'_outputLFN_jobvar':'COMPSTR'})  # composite string handled by DIRAC_UPLOAD module
				# should override output, relocating to ./
				step_desc['output']=os.path.basename(step_desc['outputLFN'])


			# cepcSim 
			if step in ['cepcSim','cepc_sim','cepcswSim','cepcsw_sim']:
				sim_in_workflow=step
				self.index_jobvar=step+'_seed_jobvar'
				if use_cepcsoft:
					step_setting['type']='cepc_sim'
					#cepcenv version
					step_setting['actvar']['cepcsoft_version']=softVersion
					#simMacro=steerFile, put into input sandbox
					simMacro = step_desc.get('simMacro',None)
					simMacro = step_desc.get('steerFile',simMacro)
					if not simMacro:
						raise CepcScenarioError('Missing "simMacro" or "steerFile" attribute in step %s.'%step)
					else:
						input_sandbox['common']['simu_macro']=simMacro
					# different stdhep files, accessing the LFN.
					stdhepFile = step_desc.get('stdhepFile',None)
					if not stdhepFile:
						raise CepcScenarioError('Missing "stdhepFile" attribute in step %s.'%step)
					step_setting=self.registerStepJobvar(step,'stdhepFile',step_setting,stdhepFile)

					self.dirac_download_dict.update({'cepcSim':step+'_stdhepFile_jobvar'})

				
					# text replacement:	in action module, $JSUB_cepcsim_rtext_{idx} -> $JSUB_cepcsim_textr_{idx} ...
					textReplace=step_desc.get('textReplace',{})
					if type(textReplace) is not dict:
						raise CepcScenarioError('The value of textReplace should be a dict. (in step %s)'%step)
					if splitterMode in ['splitByJobvars']:	  # mapping rtext -> textr in alg action module
						for k,v in textReplace.items():
							step_setting=self.registerStepJobvar('cepcSim','rtext_'+str(cepcSim_counter),step_setting,k)
							step_setting=self.registerStepJobvar('cepcSim','textr_'+str(cepcSim_counter),step_setting,v)
							cepcSim_counter+=1  


					# gear output file:
					gearOutput = step_desc.get('gearOutput','gearOutput.xml')
					if gearOutput:
						step_setting['actvar']['gear_output']=gearOutput

					# default output
					LCIOOutput= step_desc.get('output',None)
					LCIOOutput= step_desc.get('LCIOOutput',LCIOOutput)
					LCIOOutput= step_desc.get('lcioOutput',LCIOOutput)
					LCIOOutput= step_setting.get('output',LCIOOutput)
					if (splitterMode in ['splitByJobvars']):
						if LCIOOutput is None:
							LCIOOutput='%s-$(%s)'%(step,self.index_jobvar)
						step_setting=self.registerStepJobvar(step,'output',step_setting,LCIOOutput)



					# setting files to Dirac upload
					default_upload=True
					outputUpload = step_desc.get('outputUpload',None)
					outputUpload = step_desc.get('uploadOutput',outputUpload)
					if type(outputUpload) is str:
						outputUpload=[outputUpload]
					elif (type(outputUpload) is not list) and (outputUpload is not None):
						raise JunoScenarioError('The value of outputUpload should be a string or a list. (in step %s)'%step)
					if outputUpload is not None:
						default_upload=False
						for upload_item in outputUpload:
							self.dirac_upload_dict.update({upload_item:'DIRACTOPDIR/'+step})

					# outputSlcio  <- output
					if default_upload:
						self.dirac_upload_dict.update({'*slcio':'DIRACTOPDIR/'+step})

				elif use_cepcsw:
#					workflow['cepc_sim']={'type':'cepcsw_sim','actvar':{},'depend_on':p_steps}
					pass

			# cepcRec
			elif step in ['cepcRec','cepc_rec','cepcsw_rec','cepcswRec']:
				default_upload=True # if True, uploading *root and *slcio
				if use_cepcsoft:
					step_setting['type']='cepc_rec'
					# cepcenv version
					step_setting['actvar']['cepcsoft_version']=softVersion
					# same steerFile for each subjob, shall be put into sandbox
					steerFile = step_desc.get('steerFile',None)
					if not steerFile:
						raise CepcScenarioError('Missing "steerFile" attribute in step %s.'%step)
					if not os.path.isfile(steerFile):
						raise CepcScenarioError('Steer file does not exist at %s'%steerFile)
					input_sandbox['common']['rec_steer_file']=steerFile
					# same gearFile for each subjob, may come from simulation, or in input sandbox
					if sim_in_workflow==False:
						#gearFile
						gearFile = step_desc.get('gearFile',None)
						gearFile = step_desc.get('gearInput',gearFile)
						if not gearFile:
							raise CepcScenarioError('Missing "gearFile" attribute in step %s.'%step)
						if not os.path.isfile(gearFile):
							raise CepcScenarioError('GEAR file does not exist at %s'%gearFile)
						input_sandbox['common']['gear_file']=gearFile

						# lcioInput <-- input/inputLFN from build_common_step_setting() or LCIOInput
						LCIOinput= step_desc.get('input',None)
						LCIOinput= step_desc.get('inputLFN',LCIOInput)
						LCIOinput= step_desc.get('LCIOInput',LCIOInput)
						LCIOinput= step_desc.get('lcioInput',LCIOInput)
						if not LCIOinput:
							raise CepcScenarioError('Missing "input/LCIOInput" attribute in step %s.'%step)
						result=self.registerStepJobvar(step,'input',result,LCIOinput)
						self.dirac_download_dict.update({'cepcRec':step+'_input_jobvar'})
					else:				
						gearFile=workflow[sim_in_workflow]['actvar'].get('gear_output',None)
						if not gearFile:
							raise CepcScenarioError('Failed to get gearFile input from previous Simulation steps.')
#						step_setting['actvar']['gear_file']=gearFile
						step_setting=self.registerStepJobvar(step,'gear_file',step_setting,gearFile)
						
						LCIOinput=workflow[sim_in_workflow]['actvar'].get('output_jobvar',None)
						if not LCIOinput:
							raise CepcScenarioError('Failed to get input of %s from previous Simulation steps.'%step)
						step_setting['actvar']['input_jobvar']=sim_in_workflow+'_output_jobvar'


					# output/outputLFN/LCIOOutput
					# default output files
					LCIOOutput= step_desc.get('output',None)
					LCIOOutput= step_desc.get('LCIOOutput',LCIOOutput)
					LCIOOutput= step_desc.get('lcioOutput',LCIOOutput)
					LCIOOutput= step_setting.get('output',LCIOOutput)
					if (splitterMode in ['splitByJobvars']):
						if LCIOOutput is None:
							LCIOOutput='%s-$(%s)'%(step,self.index_jobvar)
					step_setting=self.registerStepJobvar(step,'output',step_setting,LCIOOutput)
					# rootfiles
					ROOTFile = step_desc.get("ROOTFile",None)
					ROOTFile = step_desc.get("rootfile",ROOTFile)
					if ROOTFile:
						step_setting=self.registerStepJobvar(step,'rootfile',step_setting,ROOTFile)	


					# setting files to upload
					outputUpload = step_desc.get('outputUpload',None)
					outputUpload = step_desc.get('uploadOutput',outputUpload)
					if type(outputUpload) is str:
						outputUpload=[outputUpload]
					elif (type(outputUpload) is not list) and (outputUpload is not None):
						raise JunoScenarioError('The value of outputUpload should be a string or a list. (in step %s)'%step)
					if outputUpload is not None:
						default_upload=False
						for upload_item in outputUpload:
							self.dirac_upload_dict.update({upload_item:'DIRACTOPDIR/'+step})

					# text replacement:	in action module, $JSUB_cepcRec_rtext_{idx} -> $JSUB_cepcRec_textr_{idx} ...
					textReplace=step_desc.get('textReplace',{})
					if type(textReplace) is not dict:
						raise CepcScenarioError('The value of textReplace should be a dict. (in step %s)'%step)
					if splitterMode in ['splitByJobvars']:	  # mapping rtext -> textr in alg action module
						for k,v in textReplace.items():
							step_setting=self.registerStepJobvar('cepcRec','rtext_'+str(cepcRec_counter),step_setting,k)
							step_setting=self.registerStepJobvar('cepcRec','textr_'+str(cepcRec_counter),step_setting,v)
							cepcRec_counter+=1  


					# default upload:
					if default_upload:
						self.dirac_upload_dict.update({'*slcio':'DIRACTOPDIR/'+step})
						self.dirac_upload_dict.update({'*root':'DIRACTOPDIR/'+step})
						self.dirac_upload_dict.update({'*xml':'DIRACTOPDIR/'})




				elif use_cepcsw:
					pass

			# cepc ana.
			# to do

	
			elif step_type.lower() in ['cmd']:
				step_setting['actvar']['cmd']=step_desc.get('cmd')
			elif step_type.lower() in ['dirac_upload']:
				step_setting['actvar']=step_desc

			else:   # invalid step type
				raise CepcScenarioError('Invalid step type (%s) for step %s in workflow'%(step_type,step))

			workflow[step]=copy(step_setting)
		# ends iterating workflow steps


		if splitterMode in ['splitByEvent']:
			self.splitCepc['jobvars']=jobvars
			self.splitter['jobvarsToSeq']=jobvarsToSeq
			if 'index0' not in self.splitter:	# top priority if index0 specified by user
				self.splitter['index0']=index0


		## condor backend
		## to do

		# Dirac backend
		if backend['name']=='dirac':
			dirac_setting=self.scenario_input.get('backend',{})
			taskName=self.scenario_input.get('taskName','')
			if isinstance(dirac_setting, str):
				dirac_setting={'type':dirac_setting}
			elif not isinstance(dirac_setting,dict):
				dirac_setting={}

			# start setting up upload module
			do_upload=dirac_setting.get('upload','TRUE')
			if do_upload.upper()=='TRUE':
				# a dirac-upload action in the end, to upload files in dirac_upload_dict:
				workflow['dirac_upload']={'type':'dirac_upload','actvar':{},'depend_on':job_steps}
				workflow['dirac_upload']['actvar']['overwrite']=dirac_setting.get('overwrite','True')
				workflow['dirac_upload']['actvar']['SE']=dirac_setting.get('SE')

				# outputDir for dir of full path; outputSubDir for subdir in user home.
				dirac_outputSubDir=dirac_setting.get('outputSubDir',outputSubDir)
				dirac_outputDir=dirac_setting.get('outputDir',outputDir)



				dirac_topdir=''
				if dirac_outputDir:
					dirac_topdir=dirac_outputDir
				elif dirac_outputSubDir:
					dirac_topdir=os.path.join(dirac_outputSubDir,taskName)

				keys=self.dirac_upload_dict.keys()
				for key in keys:
					if 'DIRACTOPDIR' in self.dirac_upload_dict[key]:
						self.dirac_upload_dict[key]=self.dirac_upload_dict[key].replace('DIRACTOPDIR',dirac_topdir)

				workflow['dirac_upload']['actvar']['upload_dict']=self.dirac_upload_dict
				workflow['dirac_upload']['actvar']['failable_file']=['*.xml']
			# finish setting up upload module


			# setting up dirac download modules
			for step in workflow:
			   	workflow[step]['depend_on'].append('dirac_finish_download')
			workflow['dirac_finish_download']={'type':'cmd','actvar':{'cmd':'echo Finished Downloading'},'depend_on':[]}
			
			for key in self.dirac_download_dict:
				fname_jobvar=self.dirac_download_dict[key]
				workflow['dirac_download_'+key]={'type':'dirac_download','actvar':{},'depend_on':[]}
				workflow['dirac_download_'+key]['actvar']['input_lfn_jobvar_name']=fname_jobvar

				workflow['dirac_finish_download']['depend_on'].append('dirac_download_'+key)


			'''
-------------------------------------

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
			'''						

		#build scenario
		self.scenario_param['input']=input_sandbox	
		self.scenario_param['splitter']=self.splitter
		self.scenario_param['workflow']=workflow	

		return self.scenario_param


	def validate_param(self):
		pass
