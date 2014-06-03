from raft_base import RaftBaseNode

'''
A derived class of the base node -- this just implements a k-v store on top of Raft.
This handles the client interaction with the custom client node (in another file)
'''
class RaftNode(RaftBaseNode):
    def __init__(self, name, pub_endpoint, router_endpoint, peer_names, **kwargs):
        RaftBaseNode.__init__(self, name, pub_endpoint, router_endpoint, peer_names, **kwargs)
        self.data_store = {}

        # Add message handlers for the client-facing get/set commands. Note that
        # these are not raw messages from the broker -- the client process will put them
        # into a better format. Names are in caps so the broker doesn't mess with them.

        self.message_handlers.update({
            'GET': self.handle_clientget,
            'SET': self.handle_clientset
        })

        # A dict of GET requests
        self.getReq_info = {}

    def handle_clientget(self, msg):
        # If we're not the leader, send a redirect message
        if self.raft_state != 'leader':
            redirect_msg = {
                    'type': 'redirect',
                    'destination': [msg['source']],
                    'redir_target': self.raft_leader,
                    'id': msg['id']
            }
            self.req.send_json(redirect_msg)
            return
        
        # Send out a heartbeat to make sure we're still the leader.
        # If everything else comes back okay, reply with the value.
        for peer in self.raft_peers:
            lastLogIndex = self.raft_nextIndex[peer] - 1
            lastLogTerm = self.raft_log[lastLogIndex]['term']
            poke_msg = {
                    'type': 'AppendEntries',
                    'destination': [peer],
                    'source': self.name,
                    'term': self.raft_term,
                    'lastLogIndex': lastLogIndex,
                    'lastLogTerm': lastLogTerm,
                    'entries': self.raft_log[lastLogIndex + 1:],
                    'leaderCommit': self.raft_commitIndex,
                    'id': msg['id']
            }
            self.req.send_json(poke_msg)

        # Register the get request in our dict of pending ones
        self.getReq_info[msg['id']] = {
                'source': msg['source'],
                'key': msg['key']
        }

    def handle_clientset(self, msg):
        if self.raft_state != 'leader':
            redirect_msg = {
                    'type': 'redirect',
                    'destination': [msg['source']],
                    'redir_target': self.raft_leader,
                    'id': msg['id']
            }
            self.req.send_json(redirect_msg)
            return
        
        # Insert the set request into our log and immediately trigger a heartbeat
        # which conveniently contains all unsent log entries..
        self.raft_log.append({
            'term': self.raft_term,
            'action': 'set',
            'key': msg['key'],
            'value': msg['value'],
            'source': msg['source'],
            'id': msg['id']
        })
        self.leader_heartbeat()

    def commit_entry(self, log_entry):
        if log_entry['action'] is None:
            return
        # Only thing I've defined in pure-raft is set
        self.data_store[log_entry['key']] = log_entry['value']

        # Doesn't matter if we're the leader or not anymore -- if this thing
        # got committed, it got committed, so reply back to the client 
        # with a success
        
        success_msg = {
                'type': 'set_success',
                'destination': [log_entry['source']],
                'id': log_entry['id']
        }
        self.req.send_json(success_msg)

    def respond_to_getReq(self, getId):
        # If we've gotten here, it means that we're still leader. Check anyway...
        if self.raft_state != 'leader':
            self.log_info('Something has gone wrong -- respond_to_getReq not called as leader')
            return

        req_info = self.getReq_info[getId]
        response = {
                'type': 'get_success',
                'destination': [req_info['source']],
                'key': req_info['key'],
                'value': self.data_store.get(req_info['key']),
                'id': getId
        }
        self.req.send_json(response)

    '''
    For good measure, override revert_state so we can clear getReq_info.
    '''
    def revert_state(self, term):
        RaftBaseNode.revert_state(self, term)
        self.getReq_info.clear()
