"""Resolve VM Multus attachments against live NADs and optionally change one stopped VM attachment."""
import argparse
from decimal import Decimal
import json
import sys
import subprocess
from datetime import datetime, timezone
from oc_client import Client, VM, VMI, MIG, SNAP, quantity, age_hours, condition, require_name, stopped, escape, migration


def execute(client,args):
    vm = client.get(VM, require_name(args))
    networks = vm['spec']['template']['spec'].get('networks', [])
    if args.nad:
        if not args.network: raise ValueError('--network is required with --nad')
        stopped(client, args.name)
        namespace, name = args.nad.split('/',1) if '/' in args.nad else (args.namespace,args.nad)
        Client(args.context,namespace).get('network-attachment-definitions.k8s.cni.cncf.io',name)
        index = next((index for index,item in enumerate(networks) if item['name'] == args.network and 'multus' in item), None)
        if index is None: raise ValueError('Named Multus network is absent from this VM')
        return client.patch(VM,vm,[{'op':'replace','path':f'/spec/template/spec/networks/{index}/multus/networkName','value':args.nad}],args.apply)
    rows = []
    for network in networks:
        if 'multus' not in network: continue
        reference = network['multus']['networkName']
        namespace,name = reference.split('/',1) if '/' in reference else (args.namespace,reference)
        nad = Client(args.context,namespace).get('network-attachment-definitions.k8s.cni.cncf.io',name,missing_ok=True)
        rows.append({'network':network['name'],'nad':namespace+'/'+name,'exists':bool(nad)})
    return rows


def main():
    parser = argparse.ArgumentParser(description='Resolve VM Multus attachments against live NADs and optionally change one stopped VM attachment.')
    parser.add_argument('--context',required=True,help='Explicit existing oc kubeconfig context')
    parser.add_argument('--namespace',required=True,help='Namespace for workload operations')
    parser.add_argument('--name',help='Exact workload/resource name where required')
    parser.add_argument('--apply',action='store_true',help='Execute the requested change; default is preview')
    parser.add_argument('--network', help='VM network alias to change')
    parser.add_argument('--nad', help='Existing namespace/name NetworkAttachmentDefinition')
    args = parser.parse_args()
    try:
        result = execute(Client(args.context,args.namespace),args)
        print(json.dumps({'context':args.context,'namespace':args.namespace,'collected_at':datetime.now(timezone.utc).isoformat(),'result':result},indent=2))
    except (RuntimeError,ValueError,KeyError,OSError,TimeoutError,subprocess.SubprocessError) as error:
        print(str(error),file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__': raise SystemExit(main())
