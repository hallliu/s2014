from Queue import Queue
import random
import json
import sys
import signal
import datetime
import zmq
from zmq.eventloop import ioloop, zmqstream
import argparse
from copy import copy
ioloop.install()

class Node(object):
    def __init__(self, name, pub_endpoint, router_endpoint, peer_names):
        self.loop = ioloop.ZMQIOLoop.current()
        self.context = zmq.Context()
    
        # SUB socket for receiving messages from the broker
        self.sub_sock = self.context.socket(zmq.SUB)
        self.sub_sock.connect(pub_endpoint)
        # make sure we get messages meant for us!
        self.sub_sock.set(zmq.SUBSCRIBE, name)
        self.sub = zmqstream.ZMQStream(self.sub_sock, self.loop)
        self.sub.on_recv(self.msg_handler)
    
        # REQ socket for sending messages to the broker
        self.req_sock = self.context.socket(zmq.REQ)
        self.req_sock.connect(router_endpoint)
        self.req = zmqstream.ZMQStream(self.req_sock, self.loop)
        self.req.on_recv(self.handle_broker_message)

        self.name = name
        self.peers = peer_names
        self.hello_sent = False
        
        self.message_handlers = {
                'hello': self.helloRespond,
                'RequestVote': self.handle_reqvote
        }

        # Node's Raft state (possibly to be augmented by DHT later?)
        self.raft_peers = copy(self.peers)
        self.raft_state = 'follower'

        self.raft_term = 0
        self.raft_lastvote = None
        self.raft_commitIndex = 0
        self.raft_lastApplied = 0

        self.raft_lastLogIndex = 0
        self.raft_lastLogTerm = 0

        self.raft_nextIndex = None
        self.raft_matchIndex = None

        self.stored_data = {}

    def start(self):
        self.loop.start()
        # Initialize the election timeout
        self.loop.add_timeout(self.loop.time() + datetime.timedelta(milliseconds = random.randint(150, 300)), self.leader_timeout)

    def handle_broker_message(self, frames):
        pass

    def msg_handler(self, frames):
        msg = json.loads(frames[2])
        handler_fn = self.message_handlers.get(msg['type'], self.log_info)
        handler_fn(msg)

    '''
    Here follows the different functions that get triggered
    '''
    def helloRespond(self, msg):
        if not self.hello_sent:
            self.req.send_json({'type': 'helloResponse', 'source': self.name})
            self.hello_sent = True
            self.req.send_json({'type': 'log', 'message': 'hello received'})

    def leader_timeout(self):
        self.log_info('Server {0} hit election timeout'.format(self.name))
        self.raft_state = 'cand'
        self.raft_term += 1
        reqvote_msg = {
                'type': 'RequestVote',
                'term': self.raft_term,
                'lastLogIndex': self.raft_lastLogIndex,
                'raft_lastLogTerm': self.raft_lastLogTerm
        }
        self.req.send_json(reqvote_msg)

    def handle_reqvote(self, msg):

    def log_info(self, s):
        self.req.send_json({'type': 'log', 'info': s})

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
    args = parser.parse_args()
    args.peer_names = args.peer_names.split(',')
    
    # Modify stdout and stderr to use a log file in /tmp
    sys.stdout = open('/tmp/{0}_log'.format(args.node_name), 'w')
    sys.stderr = sys.stdout

    Node(args.node_name, args.pub_endpoint, args.router_endpoint, args.peer_names).start()

