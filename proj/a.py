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
from collections import defaultdict
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
                'RequestVote': self.handle_reqvote,
                'VoteReply': self.handle_votereply
        }

        # Node's Raft state (possibly to be augmented by DHT later?)
        self.raft_peers = copy(self.peers)
        self.raft_state = 'follower'

        '''
        The format of each log entry is a dict. The 'term' value is constant among all of them, and
        all the other entries are to be used by any derived subclasses to adjust their own state.
        '''
        self.raft_log = []

        self.raft_term = 0
        self.raft_lastvote = None
        self.raft_commitIndex = 0
        self.raft_lastApplied = 0

        self.raft_timeout = None

        '''
        These two variables are only relevant when self is a leader. In that case,
        they are initialized to defaultdicts which use each server's name as a key.
        '''
        self.raft_nextIndex = None
        self.raft_matchIndex = None

    def start(self):
        self.loop.start()
        # Initialize the election timeout
        self.raft_timeout = self.loop.add_timeout(self.loop.time() + datetime.timedelta(milliseconds = random.randint(150, 300)), self.leader_timeout)

    def handle_broker_message(self, frames):
        pass

    def msg_handler(self, frames):
        msg = json.loads(frames[2])
        handler_fn = self.message_handlers.get(msg['type'], self.log_info)
        handler_fn(msg)

    '''
    Here follows the message handler functions that interface directly with the broker.
    '''
    def helloRespond(self, msg):
        if not self.hello_sent:
            self.req.send_json({'type': 'helloResponse', 'source': self.name})
            self.hello_sent = True
            self.req.send_json({'type': 'log', 'message': 'hello received'})

    # Not strictly a handler, but it responds directly to loop events, so I'm putting it here.
    def leader_timeout(self):
        self.log_info('Server {0} hit election timeout'.format(self.name))
        self.raft_state = 'candidate'
        self.raft_term += 1
        reqvote_msg = {
                'type': 'RequestVote',
                'source': self.name,
                'term': self.raft_term,
                'lastLogIndex': len(self.raft_log),
                'lastLogTerm': self.raft_log[-1]['term']
        }
        self.req.send_json(reqvote_msg)
        self.raft_lastvote = self.name
        self.raft_numVotes = 1 # Ourselves
        self.reset_timeout()

    def handle_reqvote(self, msg):
        # If term is less, simply reject
        elif msg['term'] < self.raft_term:
            reject_msg = {
                    'type': 'VoteReply',
                    'destination': msg['source'],
                    'term': self.raft_term,
                    'voteGranted': False
            }
            self.req.send_json(reject_msg)
            self.log_info('Rejected vote req from {0} due to lagging term (self: {1}, peer: {2})'.format(msg['source'], self.raft_term, msg['term']))
            return

        # If this message came from a candidate at least as up-to-date as us, no sense in
        # going for candidacy again soon. Thus, reset the timeout.
        self.reset_timeout()

        # Check if term is larger and change own status as appropriate
        if msg['term'] > self.raft_term:
            self.revert_state(msg['term'])

        # Decide whether to grant the vote
        hasNotVoted = self.raft_lastvote is None
        cand_uptodate = self.raft_log[-1]['term'] <= msg['lastLogTerm'] and len(self.raft_log) <= msg['raft_lastLogIndex']
        if hasNotVoted and cand_uptodate:
            vote_msg = {
                    'type': 'VoteReply',
                    'destination': msg['source']
                    'term': self.raft_term,
                    'voteGranted': True
            }
            self.req.send_json(vote_msg)
            self.raft_lastvote = msg['source']
            self.log_info('Granted vote to {0} at term {1}'.format(msg['source'], msg['term']))
        else:
            reject_msg = {
                    'type': 'VoteReply',
                    'destination': msg['source'],
                    'term': self.raft_term,
                    'voteGranted': False
            }
            self.req.send_json(vote_msg)
            log_msg = 'Rejected vote req from {0} due to hasNotVoted={1} and uptodate={2}'.format(msg['source'], hasNotVoted, cand_uptodate)
            self.log_info(log_msg)
        
    def handle_votereply(self, msg):
        # If term leads ours, fall back to follower and exit
        if msg['term'] > self.raft_term:
            self.revert_state(msg['term'])
            return
        # If term is lagging or no longer a candidate, just ignore the message.
        if msg['term'] < self.raft_term or not self.raft_state == 'candidate':
            return

        # If vote granted, increment our vote count by one, then become leader if majority
        if msg['voteGranted']:
            self.raft_numVotes += 1
            if self.raft_numVotes >= len(self.raft_peers) + 1:
                self.become_leader()


    '''
    A bunch of helper functions that take care of common raft state transitions
    '''
    # Resets self back to follower state upon receiving a message with a higher term
    def revert_state(self, term):
        self.raft_state = 'follower'
        self.raft_term = term
        self.raft_lastvote = None
    
    # Upon receiving a sufficient number of votes, become leader using this function
    def become_leader(self):
        # Remove the timeout. Leaders don't need timeouts, because they're cool.
        if self.raft_timeout is not None:
            self.loop.remove_timeout(self.raft_timeout)

        # Adjust own state.
        self.raft_state = 'leader'
        self.raft_nextIndex = defaultdict(lambda: len(self.raft_log) + 1)
        self.raft_matchIndex = defaultdict(int)

        # Send out a heartbeat AppendEntries to all peers
        leader_heartbeat = {
                'type': 'AppendEntries',
                'destination': self.raft_peers,
                'source': self.name,
                'term': self.raft_term,
                'lastLogIndex': len(self.raft_log),
                'lastLogTerm': self.raft_log[-1]['term'],
                'entries': [],
                'leaderCommit': self.raft_commitIndex
        }
        self.req.send_json(leader_heartbeat)
    
    # Reset the timeout to another 150-300ms interval from now.
    def reset_timeout(self):
        if self.raft_timeout is not None:
            self.loop.remove_timeout(self.raft_timeout)
        self.raft_timeout = self.loop.add_timeout(self.loop.time() + datetime.timedelta(milliseconds = random.randint(150, 300)), self.leader_timeout)

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

