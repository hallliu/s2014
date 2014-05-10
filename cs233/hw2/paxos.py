import sys

class Msg():
    def __init__(self, src, dst, mtype, data):
        self.src = src
        self.dst = dst
        self.mtype = mtype
        # data is going to be a dict that is accessed differently depending on mtype
        self.data = data

class Event():
    def __init__(self, t):
        self.t = t
        self.fails = []
        self.recs = []
        self.prop = None
        self.val = None

    def run(self, net_queue, computers):
        # Take care of the failures and recoveries
        for c in self.fails:
            computers[c].failed = True
            print '{0: 3d}: ** {1} FAILS **'.format(self.t, c)
        for c in self.recs:
            computers[c].failed = False
            print '{0: 3d}: ** {1} RECOVERS **'.format(self.t, c)

        # Check for proposals and run them if present
        if self.prop is not None and self.val is not None:
            msg = Msg(None, computers[self.prop], 'PROPOSE', {'val': self.val})
            computers[self.prop].recv_message(msg, self.t)
            return True

        return False


class Computer():

    def __init__(self, cid, **kwargs):
        # Common attributes
        self.cid = cid
        self.other_computers = kwargs.pop('computers')
        self.failed = False

        # Proposer attributes
        if self.cid[0] == 'P':
            self.majority_count = kwargs.pop('acceptor_count') / 2 + 1
            self.state = ('IDLE', {})
        
        # Acceptor attributes
        if self.cid[0] == 'A':
            self.highest_promised = 0
            self.highest_accepted = (0, None)

        self.__dict__.update(kwargs)

        self.msg_dispatch = {
                'PROPOSE': Computer.propose,
                'PREPARE': Computer.prepare,
                'PROMISE': Computer.promise,
                'ACCEPT': Computer.accept,
                'ACCEPTED': Computer.accepted,
                'REJECTED': Computer.rejected
        }
    
    def recv_message(self, msg, t):
        self.msg_dispatch[msg.mtype](self, msg, t)

    def propose(self, msg, t):
        print '{0: 3d}: {1} -> {2}  PROPOSE v={3}'.format(t, '  ', self.cid, msg.data['val'])
        self._make_proposal(msg.data['val'])


    def _make_proposal(self, val):
        this_prop_no = self.prop_ctr[0]
        self.prop_ctr[0] += 1

        msg_data = {'prop_no': this_prop_no}
        for c in sorted(self.other_computers[1].keys()):
            new_msg = Msg(self, self.other_computers[1][c], 'PREPARE', {'prop_no': this_prop_no})
            self.mq.append(new_msg)


        self.state = ('PROMISE_WAIT', {'proms': set(), 
                                       'rejs': set(), 
                                       'prop_no': this_prop_no, 
                                       'prop_val': val,
                                       'lprom_pn': 0
                                       })
        self.init_prop_val = val

    def prepare(self, msg, t):
        print '{0: 3d}: {1} -> {2}  PREPARE n={3}'.format(t, msg.src.cid, self.cid, msg.data['prop_no'])
        pn = msg.data['prop_no']
        if pn < self.highest_promised:
            return
        
        self.highest_promised = pn
        
        prom_msg = Msg(self, msg.src, 'PROMISE', {'prop_no': pn, 'prior': self.highest_accepted})
        self.mq.append(prom_msg)
        return

    def promise(self, msg, t):
        out_str = '{0: 3d}: {1} -> {2}  PROMISE n={3}'.format(t, msg.src.cid, self.cid, msg.data['prop_no'])
        if msg.data['prior'][1] is not None:
            print out_str + ' (Prior: n={0}, v={1})'.format(*msg.data['prior'])
        else:
            print out_str + ' (Prior: None)'

        if self.state[0] != 'PROMISE_WAIT':
            return

        self.state[1]['proms'].add(msg.src.cid)
        # Take care of the prior acceptance values
        if msg.data['prior'] is not None:
            if self.state[1]['lprom_pn'] < msg.data['prior'][0]:
                self.state[1]['prop_val'] = msg.data['prior'][1]


        if len(self.state[1]['proms']) >= self.majority_count:
            for c in sorted(self.other_computers[1].keys()):
                new_msg = Msg(self, self.other_computers[1][c], 'ACCEPT', {'prop_no': self.state[1]['prop_no'], 'prop_val': self.state[1]['prop_val']})
                self.mq.append(new_msg)

            self.state = ('ACCEPT_WAIT', {'accs': set(),
                                          'rejs': set(), 
                                          'prop_no': self.state[1]['prop_no'], 
                                          'prop_val': self.state[1]['prop_val']
                                         })

    def accept(self, msg, t):
        print '{0: 3d}: {1} -> {2}  ACCEPT n={3} v={4}'.format(t, msg.src.cid, self.cid, msg.data['prop_no'], msg.data['prop_val'])

        pn = msg.data['prop_no']
        pv = msg.data['prop_val']
        if pn < self.highest_promised:
            reject_msg = Msg(self, msg.src, 'REJECTED', {'prop_no': pn})
            self.mq.append(reject_msg)
            return

        if pn > self.highest_accepted[0]:
            self.highest_accepted = (pn, pv)

        accept_msg = Msg(self, msg.src, 'ACCEPTED', {'prop_no': pn, 'prop_val': pv})
        self.mq.append(accept_msg)

    def accepted(self, msg, t):
        print '{0: 3d}: {1} -> {2}  ACCEPTED n={3} v={4}'.format(t, msg.src.cid, self.cid, msg.data['prop_no'], msg.data['prop_val'])

        if self.state[0] != 'ACCEPT_WAIT':
            return

        self.state[1]['accs'].add(msg.src.cid)
        if len(self.state[1]['accs']) >= self.majority_count:
            self.state = ('CONSENSUS', {'init_val': self.init_prop_val, 'acc_val': self.state[1]['prop_val']})

    def rejected(self, msg, t):
        print '{0: 3d}: {1} -> {2}  REJECTED n={3}'.format(t, msg.src.cid, self.cid, msg.data['prop_no'])

        if self.state[0] == 'CONSENSUS':
            return

        self.state[1]['rejs'].add(msg.src.cid)
        if len(self.state[1]['rejs']) >= self.majority_count:
            self._make_proposal(self.state[1]['prop_val'])
        return


def parse_input(infile=sys.stdin):
    events = []
    for line in infile:
        if len(line) < 3:
            continue
        if line[0] == '#':
            continue
        parts = line.split()
        if len(parts) == 3:
            n_prop = int(parts[0])
            n_acc = int(parts[1])
            tmax = int(parts[2])
            continue
        if len(parts) == 2:
            break
        
        t = int(parts[0])
        action = parts[1]

        if len(events) == 0 or t > events[-1].t:
            e = Event(t)
            events.append(e)
        else:
            e = events[-1]

        if action == 'PROPOSE':
            e.prop = 'P' + parts[2]
            e.val = int(parts[3])
        else:
            action_list = e.fails if action == 'FAIL' else e.recs
            action_list.append(parts[2][0]+parts[3])
    
    return n_prop, n_acc, tmax, events

def extract_message(net_queue):
    if len(net_queue) == 0:
        return None

    for m in net_queue:
        if m.src.failed == False and m.dst.failed == False:
            net_queue.remove(m)
            return m

    return None

def run_paxos(n_prop, n_acc, tmax, events):
    net_queue = []
    proposers = {}
    acceptors = {}
    prop_number = [1]
    for i in range(1, n_prop + 1):
        cid = 'P' + str(i)
        proposers[cid] = Computer(cid, computers=(proposers, acceptors), mq=net_queue, prop_ctr=prop_number, acceptor_count=n_acc)
    for i in range(1, n_acc + 1):
        cid = 'A' + str(i)
        acceptors[cid] = Computer(cid, computers=(proposers, acceptors), mq=net_queue)

    computers = proposers.copy()
    computers.update(acceptors)

    for tick in range(tmax + 1):
        work_done = False
        event_done = False
        if len(events) == 0 and len(net_queue) == 0:
            break

        # See if there's an event to be processed
        if len(events) > 0:
            e = events[0]
            if e.t == tick:
                event_done = True
                events.pop(0)
                work_done = e.run(net_queue, computers)
        
        # If event contained a proposal, then we do no more work this tick.
        if work_done:
            continue

        msg = extract_message(net_queue)
        if msg is None:
            if not event_done:
                print '{0: 3d}:'.format(tick)
            continue

        msg.dst.recv_message(msg, tick)

    print 

    for (cid, c) in sorted(proposers.iteritems()):
        if c.state[0] == 'CONSENSUS':
            print '{0} has reached consensus (proposed {1}, accepted {2})'.format(cid, c.state[1]['init_val'], c.state[1]['acc_val'])
        else:
            print '{0} did not reach consensus'.format(cid)

def main():
    x = parse_input()
    run_paxos(*x)

if __name__ == '__main__':
    main()
