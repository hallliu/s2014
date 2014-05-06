Q: reliance on master leases? does having a distinguished leader impact
reliability at all? or scalability
A: Nice thing about master election is that thetre can be more than one master
which is more scalable.

* Having a master is a choice based on performance
* Easier to reason about systems having a single master, view the others as
  backups. 
* Does having a master destroy the distributed concept? 
** No -- paxos etc should lie on top of some other framework that can distribute computation.

* Chubby too fault-tolerant? maybe it's' wasting resources by guaranteeing tolerance in very unlikely scenarios
** Paper puts priorities on availability rather than performance. 

Q: why a file storage service?
* 


IS paxos important to this name service?
- "All working protocols for async consensus have paxos at the core"
- paxos is pretty standard for this sort of problem. 

Chubby lock paper differs from prev papers, lots of empirical evidence. What is the big takeaway for this paper?
* Dont trust programmers, anticipate unexpected uses of the API
* Usage info is pretty useful. Gives realworld implications of the protocol and how good it actually works
* FIrst description of a multi-tenant system -- reliability in the face of unexpected use


What would convince you that a system is correct, without resorting to mathematical proof?
    * testing? paxos made live has a lot of data on testing that seem helpful. Theyve convinced themselves that its correct

Why the "gap between theory and implementation"? 
    * Porbably always a sizable gap between a theoretical algorithm and a implementation of it that is testable.
    * 
