#!/usr/bin/python3.7

# Anis Kochlef (akochlef@gmail.com)
# 7/1/2020: Version 1.0 released
# 7/1/2020: Added summary
# 7/1/2020: Version 1.1 released
# 7/8/2020: Added list and tree switches 
# 7/8/2020: Version 1.2 released
# 7/9/2020: Added settings and monitor 
# 7/9/2020: Version 1.3 released

import json
import os
import sys
import getpass
import requests
import time
import syslog
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from datetime import datetime

_VERSION = '1.3'
_PATH = '.rvc'
_FILE = 'session.json'
_SETTINGS_FILE = 'settings.json'
_INVENTORY_FILE = 'inventory.json'
_SESSION = requests.Session()
_SESSION.verify=False
_SESSION_STATUS = 0

def save_log(path,file,log):
	with open(path + '/' + file, "a+") as fout:
		fout.write(log)
		fout.close()

def save_session_parameters(path,file,vc,username,password):
	sp = {'vc': vc,  'username': username, 'password': password}
	if not os.path.exists(path):
		os.makedirs(path)
	with open(path + '/' + file, 'w') as fout:
		json.dump(sp, fout)

def load_json(path,file):
	with open(path + '/' + file,'r') as fin:
		data = json.load(fin)
	return data

def load_session_paramters(path,file):
	with open(path + '/' + file,'r') as fin:
		sp = json.load(fin)
	return sp

def session_get_json(session,url):
	response=session.get(url)
	data=json.loads(response.text)
	json_data=data['value']
	return json_data

def session_post_url(session,url):
	response = session.post(url)
	if(response.status_code==200):
		status = 1
	else:
		status = 0
	return status


def create_session(path,file):
	status = 0
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	username=sp.get('username')
	password=sp.get('password')
	url = f'https://{vc}/rest/com/vmware/cis/session'
	response = _SESSION.post(url,auth=(username,password))
	if(response.status_code==200):
		status = 1
	else:
		print('Error: ' + str(response.status_code))
	return status

def session_parameters_input(path,file):
	vc = input('vCenter IP or FQDN: ')
	username = input('Username: ')
	password = getpass.getpass()
	save_session_parameters(path,file,vc,username,password)

def settings_input(path,file):
	poll_interval = input('Poll interval in seconds: ')
	syslog_switch = input('Syslog (true/false): ')
	console_switch = input('Console (true/false): ')
	settings = {'poll_interval': poll_interval, 'syslog': syslog_switch,  'console': console_switch}
	if not os.path.exists(path):
		os.makedirs(path)
	with open(path + '/' + file, 'w') as fout:
		json.dump(settings, fout)

def get_vms_by_host(vc,host):
	url = f'https://{vc}/rest/vcenter/vm?filter.hosts.1={host}'
	vms = session_get_json(_SESSION,url)
	return vms

def get_hosts_by_cluster(vc,cluster):
	url = f'https://{vc}/rest/vcenter/host?filter.clusters.1={cluster}'
	hosts = session_get_json(_SESSION,url)
	return hosts

def get_clusters_by_datacenter(vc,datacenter):
	url = f'https://{vc}/rest/vcenter/cluster?filter.datacenters.1={datacenter}'
	clusters = session_get_json(_SESSION,url)
	return clusters

def get_vm_by_name(vc,name):
	url = f' https://{vc}/rest/vcenter/vm'
	vms = session_get_json(_SESSION,url)
	vmid=''
	for vm in vms:
		if(vm.get('name').upper()==name.upper()):
			vmid = vm.get('vm')
	return vmid

def print_inventory(path,file,out_format):
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	url = f'https://{vc}/rest/vcenter/datacenter'
	datacenters = session_get_json(_SESSION,url)
	for datacenter in datacenters:
		clusters = get_clusters_by_datacenter(vc,datacenter.get('datacenter'))
		for cluster in clusters:
			hosts = get_hosts_by_cluster(vc,cluster.get('cluster'))
			for host in hosts:
				vms = get_vms_by_host(vc,host.get('host'))
				for vm in vms:
					D=datacenter.get('name')
					C=cluster.get('name')
					H=host.get('name')
					V=vm.get('name')
					POWER=vm.get('power_state')
					CPU=vm.get('cpu_count')
					MEM=vm.get('memory_size_MiB')
					if(out_format=='json'):
						DICT_VM={'datacenter': D, 'cluster': C, 'host': H, 'vm': V, 'power_state': POWER, 'cpu_count': CPU, 'memory_size_MiB': MEM}
						print(json.dumps(DICT_VM))
					else:
						if(out_format=='csv'):
							print(f'{D},{C},{H},{V},{POWER},{CPU},{MEM}')
						else:
							print(f'{D}\t{C}\t{H}\t{V}\t{POWER}\t{CPU}\t{MEM}')

def pull_inventory(path,file):
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	DICT={}
	i=0
	url = f'https://{vc}/rest/vcenter/datacenter'
	datacenters = session_get_json(_SESSION,url)
	for datacenter in datacenters:
		clusters = get_clusters_by_datacenter(vc,datacenter.get('datacenter'))
		for cluster in clusters:
			hosts = get_hosts_by_cluster(vc,cluster.get('cluster'))
			for host in hosts:
				vms = get_vms_by_host(vc,host.get('host'))
				for vm in vms:
					D=datacenter.get('name')
					C=cluster.get('name')
					H=host.get('name')
					V=vm.get('name')
					ID = vm.get('vm')
					POWER=vm.get('power_state')
					CPU=vm.get('cpu_count')
					MEM=vm.get('memory_size_MiB')
					DICT_VM={'vmid': ID, 'datacenter': D, 'cluster': C, 'host': H, 'vm': V, 'power_state': POWER, 'cpu_count': CPU, 'memory_size_MiB': MEM}
					DICT[i] = DICT_VM
					i+=1
	return DICT

def vm_compare(ts,vm0,vm1):
	# VM compare
	log = ''
	if((vm0['datacenter']!=vm1['datacenter'])or(vm0['cluster']!=vm1['cluster'])or(vm0['host']!=vm1['host'])):
		log += f"{ts} {vm0['vm']} moved from {vm0['datacenter']}:{vm0['cluster']}:{vm0['host']} to {vm1['datacenter']}:{vm1['cluster']}:{vm1['host']}\n"
	if(vm0['power_state']!=vm1['power_state']):
		log += f"{ts} {vm0['vm']} power state changed from {vm0['power_state']} to {vm1['power_state']}\n"
	if(vm0['cpu_count']!=vm1['cpu_count']):
		log += f"{ts} {vm0['vm']} CPU count changed from {vm0['cpu_count']} to {vm1['cpu_count']}\n"
	if(vm0['memory_size_MiB']!=vm1['memory_size_MiB']):
		log += f"{ts} {vm0['vm']} RAM changed from {vm0['memory_size_MiB']} to {vm1['memory_size_MiB']}\n"
	return log

def compare(vcenter,inventory0,inventory1):
	#ts = f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} [{vcenter}]'
	#log = f'{ts} inventory compare.\n'
	ts = f'[{vcenter}]'
	log=''
	for _vm1 in inventory1:
		found = 0
		vm1=inventory1[_vm1]
		for _vm0 in inventory0:
			vm0=inventory0[_vm0]
			if(vm0['vmid']==vm1['vmid']):
				found = 1
				log += vm_compare(ts,vm0,vm1)
		if(found==0):
			log += f"{ts} Added VM {vm1['vm']}: datacenter={vm1['datacenter']}, cluster={vm1['cluster']}, host={vm1['host']}, power state={vm1['power_state']}, cpu={vm1['cpu_count']}, ram={vm1['memory_size_MiB']}\n"
	for _vm0 in inventory0:
		vm0=inventory0[_vm0]
		found = 0
		for _vm1 in inventory1:
			vm1=inventory1[_vm1]
			if(vm0['vmid']==vm1['vmid']):
				found = 1
		if(found==0):
			log += f"{ts} Removed VM {vm0['vm']}: datacenter={vm0['datacenter']}, cluster={vm0['cluster']}, host={vm0['host']}, power state={vm0['power_state']}, cpu={vm0['cpu_count']}, ram={vm0['memory_size_MiB']}\n"	
	return log
	
def monitor(path,file,settings_file):
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	settings = load_json(path,settings_file)
	pi = int(settings.get('poll_interval'))
	syslog_switch = settings.get('syslog')
	console_switch = settings.get('console')
	I0 = pull_inventory(path,file)
	while True:
		time.sleep(pi)
		I1 = pull_inventory(path,file)
		log = compare(vc,I0,I1)
		if(log==''):
			log = f'[{vc}] inventory check.'
		if(console_switch.upper()=='TRUE'):
			print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ' + log)
		if(syslog_switch.upper()=='TRUE'):
			syslog.syslog(log)
		I0 = I1
		
def save_inventory(path,file,inventory_file):
	with open(path + '/' + inventory_file, 'w') as fout:
		inventory = pull_inventory(path,file)
		json.dump(inventory, fout)
		
def load_inventory(path,inventory_file):
	with open(path + '/' + inventory_file,'r') as fin:
		inventory = json.load(fin)
	return inventory			

def get_vm_ID(path,file):
	name = input('VM Name: ')
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	vm=get_vm_by_name(vc,name)
	print(vm)

def start_vm(path,file,name):
	sp = load_session_paramters(path,file)
	vc = sp.get('vc')
	vmid = get_vm_by_name(vc,name)
	url = f'https://{vc}/rest/vcenter/vm/{vmid}/power/start'
	if(len(vmid)>0): 
		if (session_post_url(_SESSION,url)==1):
			print(f'The request to start {name} was submitted successfully.')
		else:
			print(f'Unable to start {name}.')
	else:
		print(f'Unable to find {name}.')

def stop_vm(path,file,name):
	sp = load_session_paramters(path,file)
	vc = sp.get('vc')
	vmid = get_vm_by_name(vc,name)
	url = f'https://{vc}/rest/vcenter/vm/{vmid}/power/stop'
	if(len(vmid)>0): 
		if (session_post_url(_SESSION,url)==1):
			print(f'The request to stop {name} was submitted successfully.')
		else:
			print(f'Unable to stop {name}.')
	else:
		print(f'Unable to find {name}.')

def get_summary(path,file):
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	url = f'https://{vc}/rest/vcenter/vm'
	vms = session_get_json(_SESSION,url)
	
	url = f'https://{vc}/rest/vcenter/datacenter'
	datacenters = session_get_json(_SESSION,url)
	
	url = f'https://{vc}/rest/vcenter/cluster'
	clusters = session_get_json(_SESSION,url)
	
	url = f'https://{vc}/rest/vcenter/host'
	hosts = session_get_json(_SESSION,url)
	
	VMS = len(vms)
	DATACENTERS = len(datacenters)
	CLUSTERS = len(clusters)
	HOSTS = len(hosts)
	POWERED_ON = 0
	TOTAL_MEM = 0
	TOTAL_CPU = 0
	
	for vm in vms:
		if(vm.get('power_state')=='POWERED_ON'):
			POWERED_ON += 1
			TOTAL_MEM += vm.get('memory_size_MiB')
			TOTAL_CPU += vm.get('cpu_count')
	print(f'\nSummary {datetime.now()}:')
	print(f'---------------------------')
	print(f'Number of Datacenters: \t\t{DATACENTERS}')
	print(f'Number of Clusters: \t\t{CLUSTERS}')
	print(f'Number of Hosts: \t\t{HOSTS}')
	print(f'Number of VMs: \t\t\t{VMS}, ON: {POWERED_ON}, OFF: {VMS-POWERED_ON}')
	print(f'Total Allocated CPUs: \t\t{TOTAL_CPU}')
	print(f'Total Allocated RAM: \t\t{TOTAL_MEM} MiB\n')
		
def get_vm_list(path,file):
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	url = f'https://{vc}/rest/vcenter/vm'
	vms = session_get_json(_SESSION,url)
	for vm in vms:
		print(vm.get('name'))

def get_datacenter_list(path,file):
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	url = f'https://{vc}/rest/vcenter/datacenter'
	datacenters = session_get_json(_SESSION,url)
	for datacenter in datacenters:
		print(datacenter.get('name'))

def get_host_list(path,file):
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	url = f'https://{vc}/rest/vcenter/host'
	hosts = session_get_json(_SESSION,url)
	for host in hosts:
		print(host.get('name'))

def get_cluster_list(path,file):
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	url = f'https://{vc}/rest/vcenter/cluster'
	clusters = session_get_json(_SESSION,url)
	for cluster in clusters:
		print(cluster.get('name'))

def get_tree_architecture(path,file):
	sp = load_session_paramters(path,file)
	vc=sp.get('vc')
	url = f'https://{vc}/rest/vcenter/datacenter'
	datacenters = session_get_json(_SESSION,url)
	d = 1
	print('.')
	for datacenter in datacenters:
		D=datacenter.get('name')
		if(d==len(datacenters)):
			SD  = '└── '
			SDC = '    '
		else:
			SD  = '├── '
			SDC = '│   '
		print(SD+D)
		clusters = get_clusters_by_datacenter(vc,datacenter.get('datacenter'))
		c = 1
		for cluster in clusters:
			C=cluster.get('name')
			if(c==len(clusters)):
				SC  = '└── '
				SCH = '    '
			else:
				SC  = '├── '
				SCH = '│   '
			print(SDC+SC+C)
			hosts = get_hosts_by_cluster(vc,cluster.get('cluster'))
			h = 1
			for host in hosts:
				H=host.get('name')
				if(h==len(hosts)):
					SH =  '└── '
				else:
					SH  = '├── '
				print(SDC+SCH+SH+H)
				#vms = get_vms_by_host(vc,host.get('host'))
				#for vm in vms:
				#	V=vm.get('name')
				#	POWER=vm.get('power_state')
				#	CPU=vm.get('cpu_count')
				#	MEM=vm.get('memory_size_MiB')
				h += 1
			c += 1
		d += 1		

def print_help(command):
	print('===========================================================')
	print(f'Remote vCenter Ver {_VERSION}')
	print('Created by: Anis Kochlef')
	print('Email: akochlef@gmail.com')
	print('!!! Use at your own risk, no warranty provided !!!')
	print('Usage:')
	print(f'{command} session : Saves your vCenter connection parameters.')
	print(f'{command} summary : Resource allocation summary report.')
	print(f'{command} start <VM Name> : Starts the virtual machine.')
	print(f'{command} stop <VM Name> : Stops the virtual machine.')
	print(f'{command} inventory <text|csv|json> : Prints the full vCenter virtual machines inventory.')
	print(f'{command} tree : Prints the virtual environment architecture in a tree format.')
	print(f'{command} <datacenter|cluster|host|vm> list: Prints all the objects in the list.')
	print(f'{command} monitor: Logs changes in the virtual environment, the settings need to created and saved first.')
	print(f'{command} settings: Saves rVcenter settings.')
	print(f'{command} help : Prints this help.')
	print('===========================================================')

##########################################################################
if __name__ == "__main__":
	if (len(sys.argv)==2 and sys.argv[1]=='monitor'):
		if(create_session(_PATH,_FILE)):
			monitor(_PATH,_FILE,_SETTINGS_FILE)
			
	if (len(sys.argv)==2 and sys.argv[1]=='session'):
		session_parameters_input(_PATH,_FILE)
	
	if (len(sys.argv)==2 and sys.argv[1]=='settings'):
		settings_input(_PATH,_SETTINGS_FILE)
	
	if (len(sys.argv)==3 and sys.argv[1]=='inventory'):
		if(create_session(_PATH,_FILE)):
			print_inventory(_PATH,_FILE,sys.argv[2])

	if (len(sys.argv)==3 and sys.argv[1]=='start'):
		if(create_session(_PATH,_FILE)):
			start_vm(_PATH,_FILE,sys.argv[2])
	
	if (len(sys.argv)==3 and sys.argv[1]=='stop'):
		if(create_session(_PATH,_FILE)):
			stop_vm(_PATH,_FILE,sys.argv[2])
	
	if ((len(sys.argv)==2 and sys.argv[1]=='help') or (len(sys.argv)==1)):
		print_help(sys.argv[0])

	if (len(sys.argv)==2 and sys.argv[1]=='summary'):
		if(create_session(_PATH,_FILE)):
			get_summary(_PATH,_FILE)
	
	if (len(sys.argv)==3 and sys.argv[1]=='vm' and sys.argv[2]=='list'):
		if(create_session(_PATH,_FILE)):
			get_vm_list(_PATH,_FILE)
	
	if (len(sys.argv)==3 and sys.argv[1]=='datacenter' and sys.argv[2]=='list'):
		if(create_session(_PATH,_FILE)):
			get_datacenter_list(_PATH,_FILE)
	
	if (len(sys.argv)==3 and sys.argv[1]=='host' and sys.argv[2]=='list'):
		if(create_session(_PATH,_FILE)):
			get_host_list(_PATH,_FILE)
	
	if (len(sys.argv)==3 and sys.argv[1]=='cluster' and sys.argv[2]=='list'):
		if(create_session(_PATH,_FILE)):
			get_cluster_list(_PATH,_FILE)
	
	if (len(sys.argv)==2 and sys.argv[1]=='tree'):
		if(create_session(_PATH,_FILE)):
			get_tree_architecture(_PATH,_FILE)
##########################################################################


