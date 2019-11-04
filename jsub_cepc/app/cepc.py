class Cepc(object):
	def __init__(self, param):
		self.app_input = param
		self.app_param = {}
	

	def build(self, backend):
		job_steps=self.app_input.get('job_step')
		if type(job_steps)!=type([]):
			job_steps=[job_steps]
		#build sequencers
		sequencers={}

		seq_input_files={}
		if 'input_dir' in self.app_input:
			seq_input_files['type']='all_files_in_folder'
			seq_input_files['param']={'path':self.app_input.get('input_dir','.')}
			if 'sim' in job_steps:
				seq_input_files['param']['suffix']='stdhep'
			elif 'rec' in job_steps:
				seq_input_files['param']['suffix']='slcio'
			seq_input_files['name_map']={'value':'input_file'}
		elif 'input_filelist' in self.app_input:
			seq_input_files['type']='iter_file_list'
			seq_input_files['param']={'file_list':self.app_input.get('input_filelist')}
			seq_input_files['name_map']={'value':'input_file'}
		sequencers['input_files']=seq_input_files

		seq_random_seed={'type':'increment'}
		seq_random_seed['param']={'first':self.app_input.get('seed_start',1000),'step':1}
		seq_random_seed['name_map']={'value':'random_seed'}
		sequencers['random_seed']=seq_random_seed

		self.app_param['sequencers']=sequencers	
	
		#build input sandbox
		input_sandbox={'common':{}}
		if 'simu_macro' in self.app_input:
			input_sandbox['common']['simu_macro_template']=self.app_input.get('simu_macro')
		if 'rec_steering_file' in self.app_input:
			input_sandbox['common']['rec_steering_template']=self.app_input.get('rec_steering_file')
		self.app_param['input']=input_sandbox

		#build workflow
		workflow={}
		if 'output_dir' in self.app_input:
			sim_outdir=self.app_input['output_dir'].get('sim')
			rec_outdir=self.app_input['output_dir'].get('rec')
		if 'sim' in job_steps:
			workflow['cepc_sim']={'type':'cepc_sim','actvar':{}}
			workflow['cepc_sim']['actvar']['output_dir']=sim_outdir
			workflow['cepc_sim']['actvar']['cepcsoft_version']=self.app_input.get('cepcsoft_version')
			event_max=self.app_input.get('event_max')	
			if event_max is None:
				workflow['cepc_sim']['actvar']['event_max']=-1
			else:
				workflow['cepc_sim']['actvar']['event_max']=event_max
		if 'rec' in job_steps:
			workflow['cepc_rec']={'type':'cepc_rec','actvar':{}}
			workflow['cepc_rec']['actvar']['output_dir']=rec_outdir
			workflow['cepc_rec']['actvar']['cepcsoft_version']=self.app_input.get('cepcsoft_version')
			event_max=self.app_input.get('event_max')	
			if event_max is None:
				workflow['cepc_rec']['actvar']['event_max']=-1
			else:
				workflow['cepc_rec']['actvar']['event_max']=event_max
			if 'sim' in job_steps:
				#connecting sim and rec
				workflow['cepc_rec']['depend_on']='cepc_sim'
				workflow['cepc_rec']['actvar']['sim_outdir']=sim_outdir
			else: 
				#get GearXMLFile from user input 
				workflow['cepc_rec']['actvar']['gear_xml_file']=self.app_input.get('gear_xml_file')

		self.app_param['workflow']=workflow	


		return self.app_param


	def validate_param(self):
		pass
