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
            computers[self.prop].recv_message(msg)
            return True

        return False


class Computer():
    msg_dispatch = {
            'PROPOSE': Computer.propose
    }

    def __init__(self, cid, **kwargs):
        self.cid = cid
        self.other_computers = kwargs.pop('computers')
        self.mq = kwargs.pop('mq')
        self.failed = False
        self.role = cid[0]
        self.misc_data = kwargs
    
    def recv_message(self, msg):



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
    computers = {}
    for i in range(1, n_prop + 1):
        cid = 'P' + str(i)
        computers[cid] = Computer(cid, computers=computers, mq=net_queue, n_acc=n_acc)
    for i in range(1, n_acc + 1):
        cid = 'A' + str(i)
        computers[cid] = Computer(cid, computers=computers, mq=net_queue)

    prop_number = [1]
    work_done = False

    for tick in range(tmax):
        if len(events) == 0 and len(net_queue) == 0:
            break

        # See if there's an event to be processed
        e = events[0]
        if e.t == tick:
            work_done = e.run(net_queue, computers, prop_number)
        
        # If event contained a proposal, then we do no more work this tick.
        if work_done:
            continue

        msg = extract_message(net_queue)
        if msg is None:
            print str(tick) + ':'
            continue

        msg.dst.recv_message(msg)
