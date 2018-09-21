#!/usr/bin/env python

# Copyright 2018 Francis Y. Yan, Jestin Ma
# Copyright 2018 Huawei Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.


import os
import sys
import time
import signal
import argparse
import context
from os import path
from subprocess import Popen, call


def run(args):
    # run worker.py on ps and worker hosts
    for job_name in ['ps', 'worker']:
        host_list = args[job_name + '_list']
        procs = args[job_name + '_procs']

        for i in xrange(len(host_list)):
            ssh_cmd = ['ssh', host_list[i]]

            cmd = ['python', args['worker_src'],
                   '--ps-hosts', args['ps_hosts'],
                   '--worker-hosts', args['worker_hosts'],
                   '--job-name', job_name,
                   '--task-index', str(i)]

            cmd = ssh_cmd + cmd

            sys.stderr.write('$ %s\n' % ' '.join(cmd))
            procs.append(Popen(cmd, preexec_fn=os.setsid))

    # ps will block forever
    for ps_proc in args['ps_procs']:
        ps_proc.communicate()


def cleanup(args):
    all_procs = args['ps_procs'] + args['worker_procs']
    for proc in all_procs:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except OSError as e:
            sys.stderr.write('%s\n' % e)

    host_set = set(args['ps_list'] + args['worker_list'])
    pkill_script = path.join(args['indigo_dir'], 'tools', 'pkill.py')

    procs = []

    for host in set(args['worker_list']):
        kill_cmd = ['ssh', host, 'python', pkill_script, args['indigo_dir']]
        sys.stderr.write('$ %s\n' % ' '.join(kill_cmd))
        procs.append(Popen(kill_cmd))

    for host in set(args['ps_list']):
        kill_cmd = ['ssh', host, 'pkill', '-f', args['indigo_dir']]
        sys.stderr.write('$ %s\n' % ' '.join(kill_cmd))
        procs.append(Popen(kill_cmd))

    for proc in procs:
        proc.communicate()

    sys.stderr.write('\nAll cleaned up.\n')


def construct_args(prog_args):
    # construct a dictionary of arguments
    args = {}

    # file paths
    args['indigo_dir'] = prog_args.indigo_dir
    args['worker_src'] = path.join(args['indigo_dir'], 'dagger', 'worker.py')

    # hostnames and processes
    args['ps_hosts'] = prog_args.ps_hosts
    args['worker_hosts'] = prog_args.worker_hosts

    args['ps_list'] = prog_args.ps_hosts.split(',')
    args['worker_list'] = prog_args.worker_hosts.split(',')
    args['user'] = prog_args.user

    for i, host in enumerate(args['ps_list']):
        args['ps_list'][i] = args['user'] + '@' + host.split(':')[0]

    for i, host in enumerate(args['worker_list']):
        args['worker_list'][i] = args['user'] + '@' + host.split(':')[0]

    args['ps_procs'] = []
    args['worker_procs'] = []

    return args


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ps-hosts', required=True, metavar='[HOSTNAME:PORT, ...]',
        help='comma-separated list of hostname:port of parameter servers')
    parser.add_argument(
        '--worker-hosts', required=True, metavar='[HOSTNAME:PORT, ...]',
        help='comma-separated list of hostname:port of workers')
    parser.add_argument('--user', required=True, metavar='NAME',
                        help='username used in ssh connection')
    parser.add_argument('--indigo-dir', required=True, metavar='base_dir',
                        help='absolute path to indigo')
    prog_args = parser.parse_args()
    args = construct_args(prog_args)

    # run worker.py on ps and worker hosts
    try:
        run(args)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup(args)


if __name__ == '__main__':
    main()
