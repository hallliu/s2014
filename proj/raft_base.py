import random
import json
import datetime
import zmq
from zmq.eventloop import ioloop, zmqstream
from copy import copy
from collections import defaultdict
ioloop.install()

class RaftBaseNode(object):
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
                'VoteReply': self.handle_votereply,
                'AppendEntry': self.handle_appendentry,
                'AppendEntryReply': self.handle_appendentry_reply
        }

        # Node's Raft state (possibly to be augmented by DHT later?)
        self.raft_peers = copy(self.peers) 
        self.raft_majority_num = len(self.raft_peers) / 2 # include ourself
        self.raft_state = 'follower'
        self.raft_leader = None

        '''
        The format of each log entry is a dict. The 'term' value is constant among all of them, and
        all the other entries are to be used by any derived subclasses to adjust their own state.
        '''
        self.raft_log = []

        self.raft_term = 0
        self.raft_lastvote = None
        self.raft_commitIndex = -1
        self.raft_lastApplied = 0

        self.raft_timeout = None

        '''
        These two variables are only relevant when self is a leader. In that case,
        they are initialized to defaultdicts which use each server's name as a key.
        '''
        self.raft_nextIndex = None
        self.raft_matchIndex = None

        # This is a dict of pending GET requests. We need to wait on
        # a majority of heartbeat messages to get sent out and come back.
        self.pending_getReq_count = defaultdict(int)

    def start(self):
        # Initialize the election timeout
        self.raft_timeout = self.loop.add_timeout(self.loop.time() + random.randint(150, 300)/1000., self.leader_timeout)
        self.loop.start()

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
        self.raft_leader = None
        self.raft_state = 'candidate'
        self.raft_term += 1
        reqvote_msg = {
                'type': 'RequestVote',
                'source': self.name,
                'term': self.raft_term,
                'lastLogIndex': len(self.raft_log) - 1,
                'lastLogTerm': self.raft_log[-1]['term']
        }
        self.req.send_json(reqvote_msg)
        self.raft_lastvote = self.name
        self.raft_numVotes = 1 # Ourselves
        self.reset_timeout()

    # A periodic heartbeat message that gets registered for leaders. 
    # The heartbeat will consult nextIndex and send along entries as well, if
    # there are any to be sent.
    def leader_heartbeat(self):
        if self.raft_state != 'leader':
            return
        
        for peer in self.raft_peers:
            lastLogIndex = self.raft_nextIndex[peer] - 1
            lastLogTerm = self.raft_log[lastLogIndex]['term']
            leader_heartbeat = {
                    'type': 'AppendEntries',
                    'destination': [peer],
                    'source': self.name,
                    'term': self.raft_term,
                    'lastLogIndex': lastLogIndex,
                    'lastLogTerm': lastLogTerm,
                    'entries': self.raft_log[lastLogIndex + 1:],
                    'leaderCommit': self.raft_commitIndex
            }
            self.req.send_json(leader_heartbeat)

    def handle_reqvote(self, msg):
        # If term is less, simply reject
        if msg['term'] < self.raft_term:
            reject_msg = {
                    'type': 'VoteReply',
                    'destination': [msg['source']],
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
        cand_uptodate = self.raft_log[-1]['term'] <= msg['lastLogTerm'] and len(self.raft_log) - 1 <= msg['raft_lastLogIndex']
        if hasNotVoted and cand_uptodate:
            vote_msg = {
                    'type': 'VoteReply',
                    'destination': [msg['source']],
                    'term': self.raft_term,
                    'voteGranted': True
            }
            self.req.send_json(vote_msg)
            self.raft_lastvote = msg['source']
            self.log_info('Granted vote to {0} at term {1}'.format(msg['source'], msg['term']))
        else:
            reject_msg = {
                    'type': 'VoteReply',
                    'destination': [msg['source']],
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
            self.log_info('Vote received, {0} total'.format(self.raft_numVotes))
            if self.raft_numVotes >= len(self.raft_peers) + 1:
                self.become_leader()

    def handle_appendentry(self, msg):
        # Check terms before doing anything else. Note that if the terms are equal and self is
        # in follower mode, revert_state does absolutely nothing.
        if self.raft_term <= msg['term']:
            revert_state(self, msg['term'])

        reject_msg = {
                'type': 'AppendEntryReply',
                'destination': [msg['source']],
                'term': self.raft_term,
                'source': self.name,
                'success': False
        }

        if self.raft_term > msg['term']:
            self.req.send_json(reject_msg)
            return



        self.reset_timeout()
        self.raft_leader = msg['source']

        # Check log for the lastLogIndex and see if it matches up with the one from the message
        # First case is for is when self's log is too short
        if len(self.raft_log) <= msg['lastLogIndex']:
            self.log_info('Self\'s log too short, failing')
            self.req.send_json(reject_msg)
            return
        
        # Next case is if the existing preventry doesn't match up
        supposed_lastLogIndex = msg['lastLogIndex']
        prev_entry_term = self.raft_log[supposed_lastLogIndex]['term']
        if prev_entry_term != msg['lastLogTerm']:
            self.log_info('Term mismatch at index {0}'.format(supposed_lastLogIndex))
            self.raft_log = self.raft_log[:supposed_lastLogIndex]
            self.req.send_json(reject_msg)
            return

        # Now, walk through the entries and check if everything matches up until the
        # end of our log. When there's a mismatch, delete everything at and after the
        # mismatch, and stick the rest of the entries from the message onto the
        # end of the remnants.
        rcvd_entries = msg['entries']
        if len(rcvd_entries) == 0:
            return

        for logIndex in range(supposed_lastLogIndex + 1, len(self.raft_log)):
            newEntry_index = logIndex - supposed_lastLogIndex + 1
            if newEntry_index >= len(rcvd_entries):
                break
            if self.raft_log[logIndex]['term'] != rcvd_entries[newEntry_index]['term']:
                self.raft_log = self.raft_log[:logIndex]
                break
            rcvd_entries.pop(0) # inefficient, but these usually aren't that big...

        self.raft_log.extend(rcvd_entries)
        self.log_info('Successfully appended {0} entries to own log'.format(len(rcvd_entries)))

        # Take care of updating commitIndex and actually commiting the commands that we got sent.
        if msg['leaderCommit'] > self.raft_commitIndex:
            new_commitIndex = min(msg['leaderCommit'], len(raft_log) - 1)
            for entry in self.raft_log[self.raft_commitIndex + 1:new_commitIndex + 1]:
                self.commit_entry(entry)
            self.raft_commitIndex = new_commitIndex
        
        # Send a message back to the leader informing of success.
        # Keep all the info that the leader sent over because it's needed
        # to keep track of our state on the leader's side.
        success_msg = msg.copy()
        success_msg.update({
                'type': 'AppendEntryReply',
                'destination': [msg['source']],
                'term': self.raft_term,
                'source': self.name,
                'success': True
        })
        self.req.send_json(success_msg)

    def handle_appendentry_reply(self, msg):
        # Check terms (like always...)
        if msg['term'] > self.term:
            self.revert_state(msg['term'])
        # If the follower is a term behind, just proceed as usual. We'll figure out what happened as we're processing
        # the returned information.

        # If we're not a leader for some reason, just drop the message.
        if self.raft_state != 'leader':
            return
        
        # Some special handling for GET requests.
        if msg.get('id') is not None:
            self.pending_getReq_count[msg['id']] += 1
            if self.pending_getReq_count[msg['id']] >= self.raft_majority_num:
                self.respond_to_getReq(msg['id'])

        # If the AppendEntries was unsuccessful, decrement nextIndex for the receiver
        # and try again
        if not msg['success']:
            self.raft_nextIndex[msg['source']] -= 1
            lastLogIndex = self.raft_nextIndex[msg['source']] - 1
            lastLogTerm = self.raft_log[lastLogIndex]
            retry_appendentry = {
                    'type': 'AppendEntries',
                    'destination': [msg['source']],
                    'source': self.name,
                    'term': self.raft_term,
                    'lastLogIndex': lastLogIndex,
                    'lastLogTerm': lastLogTerm,
                    'entries': self.raft_log[lastLogIndex + 1:],
                    'leaderCommit': self.raft_commitIndex
            }
            self.req.send_json(retry_appendentry)
            return
        
        # If AppendEntries was successful, then calculate the index of the last logentry
        # that the follower has.
        follower_hasUntil = msg['lastLogIndex'] + len(msg['entries'])
        self.raft_matchIndex[msg['source']] = max(self.raft_matchIndex[msg['source']], follower_hasUntil)
        self.raft_nextIndex[msg['source']] = self.raft_matchIndex[msg['source']] + 1

        # Check if we can increase commitIndex
        matched_indices = sorted(self.raft_matchIndex.values())
        tentative_commit = matched_indices[len(self.raft_peers) - self.raft_majority_num]
        if tentative_commit > self.raft_commitIndex:
            if self.raft_log[tentative_commit]['term'] == self.raft_term:
                for i in range(self.raft_commitIndex + 1, tentative_commit + 1):
                    self.commit_entry(self.raft_log[i])
                self.raft_commitIndex = tentative_commit
        
    '''
    A bunch of helper functions that take care of common raft state transitions
    '''
    # Resets self back to follower state upon receiving a message with a higher term
    def revert_state(self, term):
        self.raft_state = 'follower'
        self.raft_term = term
        self.raft_lastvote = None
        self.pending_getReq_count = {}
        try:
            self.loop.remove_timeout(self.leader_refresh)
        except:
            pass
    
    # Upon receiving a sufficient number of votes, become leader using this function
    def become_leader(self):
        # Remove the timeout. Leaders don't need timeouts, because they're cool.
        if self.raft_timeout is not None:
            self.loop.remove_timeout(self.raft_timeout)

        # Adjust own state.
        self.raft_state = 'leader'
        self.raft_nextIndex = defaultdict(lambda: len(self.raft_log) + 1)
        self.raft_matchIndex = defaultdict(int)
        self.raft_leader = self.name 

        # Send out a heartbeat AppendEntries to all peers, while adding a noop.
        self.raft_log.append({'term': self.raft_term, 'action': None})
        self.leader_heartbeat()
        
        self.leader_refresh = self.loop.add_timeout(self.loop.time() + 0.02, self.leader_heartbeat)
        self.log_info('Election won, becoming leader')
    
    # Reset the timeout to another 150-300ms interval from now.
    def reset_timeout(self):
        if self.raft_timeout is not None:
            self.loop.remove_timeout(self.raft_timeout)

        self.raft_timeout = self.loop.add_timeout(self.loop.time() + random.randint(150, 300)/1000., self.leader_timeout)

    # The function that applies the log entry to whatever internal state we're using.
    # This is the function that should be overriden by any derived subclasses.
    def commit_entry(self, log_entry):
        pass

    # Same here, should be implemented in derived subclass.
    def respond_to_getReq(self, getId):
        pass

    def log_info(self, s):
        self.req.send_json({'type': 'log', 'info': s})
