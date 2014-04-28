import sys

class General():
    def __init__(self, index, loyalty):
        self.id = index
        if loyalty == 'L':
            self.loyal = True
        else:
            self.loyal = False

        self.messages_rcvd = []

    def send_to(self, lts, message):
        new_msg_header = message[0] + [self.id]
        if self.loyal:
            new_message = (new_msg_header, message[1])
            map(lambda x: x.messages_rcvd.append(new_message), lts)
        else:
            new_message_1 = (new_msg_header, message[1])
            new_message_2 = (new_msg_header, not message[1])
            for l in lts:
                if l.id % 2 == 1:
                    l.messages_rcvd.append(new_message_1)
                else:
                    l.messages_rcvd.append(new_message_2)

def run_om_instance(line):
    components = line.split()
    m = int(components[0])
    if m == 0:
        return None
    
    n_generals = len(components[1])
    init_command = (components[2] == 'ATTACK')

    all_generals = map(lambda x: General(*x), enumerate(components[1]))
    
    om_message(all_generals[0], all_generals[1:], ([], init_command), m)
    msg_trees = map(lambda x: make_msg_tree(x.messages_rcvd, n_generals, m, 0), all_generals[1:])

    for s in msg_trees:
        i = 1
        sys.stdout.write(s[1] + ' ')
        q = False # nasty formatting hack
        for s_tree in s[2]:
            if i != s_tree[0]:
                sys.stdout.write(' ')
                i += 1
                q = True
            sys.stdout.write(s_tree[3])
            i += 1

        sys.stdout.write('  ')
        if not q:
            sys.stdout.write(' ')

        if s[3] == 'A':
            sys.stdout.write('ATTACK\n')
        elif s[3] == 'R':
            sys.stdout.write('RETREAT\n')
        else:
            sys.stdout.write('TIE\n')

    return msg_trees 
        

'''
Performs the recursive message sending on the list of generals.
'''
def om_message(cmdr, lts, message, m):
    cmdr.send_to(lts, message)
    
    if m == 0:
        return
    
    '''
    Perform the recursive step here, depending on whether the current
    commander is loyal. Either case, we know what message he sent, so
    no need to check the individual generals' message queues.
    '''
    new_msg_header = message[0] + [cmdr.id]

    if cmdr.loyal:
        new_message = (new_msg_header, message[1])
        for l in lts:
            om_message(l, [g for g in lts if not g == l], new_message, m-1)
    else:
        new_message_1 = (new_msg_header, message[1])
        new_message_2 = (new_msg_header, not message[1])
        for l in lts:
            if l.id % 2 == 1:
                om_message(l, [g for g in lts if not g == l], new_message_1, m-1)
            else:
                om_message(l, [g for g in lts if not g == l], new_message_2, m-1)

'''
Process the messages that each general receives. We can take advantage of the
property that messages from the deeper levels of recursion are sent after the
corresponding higher level.
Tree format is a tuple (sender, order, subtrees, order_used)
'''
def make_msg_tree(msg_list, n_generals, m,  rec_depth):
    if rec_depth == m:
        order_letter = 'A' if msg_list[0][1] else 'R'
        return (msg_list[0][0][-1], order_letter, None, order_letter)

    submsg_length = (len(msg_list) - 1) / (n_generals - 1 - rec_depth - 1)
    submsg_trees = []
    attack_count = 0
    total_count = 1
    for i in range(1, len(msg_list), submsg_length):
        # This line is using the particular ordering that the simulated messages
        # came in. 
        submsg_list = msg_list[i:i+submsg_length]
        this_subtree = make_msg_tree(submsg_list, n_generals, m, rec_depth + 1)
        if this_subtree[3] == 'A':
            attack_count += 1
        if this_subtree[3] != '-':
            total_count += 1

        submsg_trees.append(this_subtree)

    msg_sender = msg_list[0][0][-1]
    msg_order = 'A' if msg_list[0][1] else 'R'
    if msg_list[0][1]:
        attack_count += 1

    if total_count - attack_count > attack_count:
        order_used = 'R'
    elif total_count - attack_count == attack_count:
        order_used = '-'
    else:
        order_used = 'A'

    return (msg_sender, msg_order, submsg_trees, order_used)

def main():
    for line in sys.stdin:
        if line[0] == '0':
            break
        run_om_instance(line)
        sys.stdout.write('\n')

if __name__ == '__main__':
    main()
