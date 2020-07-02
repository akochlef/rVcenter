#!/usr/bin/python3

# Anis Kochlef (akochlef@gmail.com)
# 7/1/2020: Version 1.0 released
# 7/1/2020: Added summary
# 7/1/2020: Version 1.1 released

import json
import os
import sys
import getpass
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from datetime import datetime

_VERSION = '1.1'
_PATH = '.rvc'
_FILE = 'session.json'
_SESSION = requests.Session()
_SESSION.verify=False
_SESSION_STATUS = 0

def save_session_parameters(path,file,vc,username,password):
	sp = {'vc': vc,  'username': username, 'password': password}
	if not os.path.exists(path):
		os.makedirs(path)
	with open(path + '/' + file, 'w') as fout:
		json.dump(sp, fout)

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
	#url = f' https://{vc}/rest/vcenter/vm?filter.names.1={name.upper()}'
	url = f' https://{vc}/rest/vcenter/vm'
	vms = session_get_json(_SESSION,url)
	vmid=''
	for vm in vms:
		if(vm.get('name').upper()==name.upper()):
			vmid = vm.get('vm')
	return vmid

def get_inventory(path,file,out_format):
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
	print(f'{command} help : Prints this help.')
	print('===========================================================')

##########################################################################
if __name__ == "__main__":
	if (len(sys.argv)==2 and sys.argv[1]=='session'):
		session_parameters_input(_PATH,_FILE)
	
	if (len(sys.argv)==3 and sys.argv[1]=='inventory'):
		if(create_session(_PATH,_FILE)):
			get_inventory(_PATH,_FILE,sys.argv[2])

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
##########################################################################

