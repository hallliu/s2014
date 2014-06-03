import argparse
from raftNode import RaftNode
from clientNode import ClientNode
import sys

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pub-endpoint',
        dest='pub_endpoint', type=str,
        default='tcp://127.0.0.1:23310')
    parser.add_argument('--router-endpoint',
        dest='router_endpoint', type=str,
        default='tcp://127.0.0.1:23311')
    parser.add_argument('--node-name',
        dest='node_name', type=str,
        default='test_node')
    parser.add_argument('--peer-names',
        dest='peer_names', type=str,
        default='')
    parser.add_argument('--client',
        dest='client', type=bool,
        default=False)

    args = parser.parse_args()
    args.peer_names = args.peer_names.split(',')
    
    # Modify stdout and stderr to use a log file in /tmp
    sys.stdout = open('/tmp/{0}_log'.format(args.node_name), 'w')
    sys.stderr = sys.stdout

    if parser.client:
        ClientNode(args.node_name, args.pub_endpoint, args.router_endpoint, args.peer_names).start()
    else:
        RaftNode(args.node_name, args.pub_endpoint, args.router_endpoint, args.peer_names).start()
