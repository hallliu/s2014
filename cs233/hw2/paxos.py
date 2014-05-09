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

    def run(self, net_queue, computers, prop_number):
        # Take care of the failures and recoveries
        for c in self.fails:
            computers[c].failed = True
        for c in self.recs:
            computers[c].failed = False

        # Check for proposals and run them if present
        if self.prop is not None and self.val is not None:
            msg = Msg(None, computers[self.prop], 'PROPOSE', {'val': self.val})
            computers[self.prop].recv_message(msg, self.t)
            return True

        return False


class Computer():
    msg_dispatch = {
            'PROPOSE': Computer.propose,
            'PREPARE': Computer.prepare,
            'PROMISE': Computer.promise,
            'ACCEPT': Computer.accept,
            'ACCEPTED': Computer.accepted,
            'REJECTED': Computer.rejected
    }

    def __init__(self, cid, **kwargs):
        self.cid = cid
        self.other_computers = kwargs.pop('computers')
        acceptor_count = len(self.other_computers[1])
        self.majority_count = acceptor_count / 2 + 1

        self.failed = False
        self.highest_promised = 0
        self.highest_accepted = None
        self.__dict__.update(kwargs)

        self.state = ('IDLE', {})
    
    def recv_message(self, msg, t):
        msg_dispatch[msg.mtype](self, msg, t)

    def propose(self, msg, t):
        prop_ctr = self.prop_ctr
        this_prop_no = prop_ctr[0]
        prop_ctr[0] += 1

        msg_data = {'prop_no': this_prop_no}
        for c in self.other_computers[1]:
            new_msg = Msg(self, c, 'PREPARE', msg_data)
            self.mq.append(new_msg)

        print '{0}: {1} -> {2} PROPOSE v={3}'.format(t, '  ', computers[self.prop].cid, msg.data['val'])

        self.state = ('PROMISE_WAIT', {'n_proms': 0, 'n_rejs': 0, 'prop_val': msg.data['val']})

    def prepare(self, msg, t):
        print '{0}: {1} -> {2} PREPARE n={3}'.format(t, msg.src.cid, self.cid, msg.data['prop_no'])
        pn = msg.data['prop_no']
        if pn < self.highest_promised:
            reject_msg = Msg(self, msg.src, 'REJECTED', {'prop_no': pn})
            self.mq.append(reject_msg)
            return
        
        prom_msg = Msg(self, msg.src, 'PROMISE', {'prop_no': pn, 'prior': self.highest_accepted})
        self.mq.append(prom_msg)
        return

    def promise(self, msg, t):
        out_str = '{0}: {1} -> {2} PROMISE n={3}'.format(t, msg.src.cid, self.cid, msg.data['prop_no'])
        if msg.data['prior'] is not None:
            print out_str + ' (Prior: n={0}, v={1})'.format(*msg.data['prior'])
        else:
            print out_str + ' (Prior: None)'


        if self.state[0] != 'PROMISE_WAIT':
            raise Exception()

        self.state[1]['n_proms'] += 1
        if self.state[1]['n_proms'] >= self.majority_count:
            for c in self.other_computers[1]:







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
            return m

    return None

def run_paxos(n_prop, n_acc, tmax, events):
    net_queue = []
    proposers = {}
    acceptors = {}
    prop_number = [1]
    for i in range(1, n_prop + 1):
        cid = 'P' + str(i)
        proposers[cid] = Computer(cid, computers=(proposers, acceptors), mq=net_queue, prop_ctr = prop_number)
    for i in range(1, n_acc + 1):
        cid = 'A' + str(i)
        acceptors[cid] = Computer(cid, computers=(proposers, acceptors), mq=net_queue)

    work_done = False
    computers = proposers.copy()
    computers.update(acceptors)

    for tick in range(tmax):
        if len(events) == 0 and len(net_queue) == 0:
            break

        # See if there's an event to be processed
        e = events[0]
        if e.t == tick:
            work_done = e.run(net_queue, computers)
        
        # If event contained a proposal, then we do no more work this tick.
        if work_done:
            continue

        msg = extract_message(net_queue)
        if msg is None:
            print str(tick) + ':'
            continue

        msg.dst.recv_message(msg, t)
