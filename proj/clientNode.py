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

'''
A special node not part of Raft that's designed to interface with the broker's limited
client capabilities. It's here because Raft has unstable leaders in the case of failures, so
we need to be able to dynamically redirect messages. All get/set messages from the broker
go through this node. There is only one of this node.
'''
class ClientNode(object):
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
                'get': self.handle_get,
                'set': self.handle_set,
                'redirect': self.handle_redirect,
                'set_success': self.handle_set_success,
                'get_success': self.handle_get_success
        }

        self.max_retries = 4
        self.msg_timeout = datetime.timedelta(milliseconds = 300)
        # Randomly pick a leader to interface with. If we're wrong, oh well.
        self.raft_leader = self.peers[0] 

        # Record of broker's requests associated with request id. Each entry is
        # a dict with fields type, key, val, timeout, num_retries. Assert error if 3 retries.
        self.broker_requests = {}

        # IDs for use in Raft. Incremented once every time a request is sent off (unless
        # it's a redirect.
        self.id_for_raft = 0
        # Contains a mapping of raft ids to broker ids. 
        self.raft_broker_map = {}

    def start(self):
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

    def handle_get(self, msg):
        timeout = self.loop.add_timeout(self.loop.time() + self.msg_timeout, lambda: self.timeout_fn(msg['id']))
        self.broker_requests[msg['id']] = {
                'type': 'get',
                'key': msg['key'],
                'timeout': timeout,
                'num_retries': 0
        }

        self.raft_broker_map[self.id_for_raft] = msg['id']
        get_msg = {
                'type': 'GET',
                'destination': [self.raft_leader],
                'source': self.name,
                'key': msg['key'],
                'id': self.id_for_raft
        }
        self.req.send_json(get_msg)
        self.id_for_raft += 1

    def handle_set(self, msg):
        timeout = self.loop.add_timeout(self.loop.time() + self.msg_timeout, lambda: self.timeout_fn(msg['id']))
        self.broker_requests[msg['id']] = {
                'type': 'set',
                'key': msg['key'],
                'value': msg['value'],
                'timeout': timeout,
                'num_retries': 0
        }

        self.raft_broker_map[self.id_for_raft] = msg['id']
        set_msg = {
                'type': 'SET',
                'destination': [self.raft_leader],
                'source': self.name,
                'key': msg['key'],
                'value': msg['value'],
                'id': self.id_for_raft
        }
        self.req.send_json(set_msg)
        self.id_for_raft += 1

    def handle_redirect(self, msg):
        # Just update who we think the leader is, then resend. If too many redirects, fail.
        self.raft_leader = msg['redir_target']
        retry_info = self.broker_requests[self.raft_broker_map[msg['id']]]
        self.retry_message(retry_info, msg['id'])

    '''
    Called as a closure by the timeout utility. Retries the message if num_retries is low.
    '''
    def timeout_on_req(self, brokerId):



    def retry_message(self, retry_info, retry_id):
        if retry_info['num_retries'] > self.max_retries:
            self.fail_request(retry_info)
            return
        retry_info['num_retries'] += 1

        retry_msg = {
                'type': retry_info['type'].upper(),
                'destination': [self.raft_leader],
                'source': self.name,
                'key': retry_info['key'],
                'value': retry_info.get('value'),
                'id': retry_id
        }
        self.req.send_json(retry_msg)


