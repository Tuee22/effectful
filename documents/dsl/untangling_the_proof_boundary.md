# Untangling the Proof Boundary

> **Purpose**: A plain-language synopsis of [The Proof Boundary](proof_boundary.md), intended to make the paper's argument accessible to readers encountering these ideas for the first time.

## What is the proof boundary?

The **proof boundary** is the line that separates what computers can verify from what humans must judge.

On one side of that line, a machine can check whether something is correct — exhaustively, repeatedly, without opinion. A compiler rejects bad syntax. A type checker catches mismatched data. A model checker explores every possible sequence of events in a system. These tools don't guess. They don't get tired. They either confirm or reject.

On the other side of the line sits everything a machine cannot settle: whether a medical diagnosis is the right call, whether a contract clause is fair, whether a law is just. These questions require human judgment because no one has figured out how to write a set of rules that a computer could apply to answer them definitively.

The paper argues this line is permanent. It is not a limitation of today's technology that a future breakthrough will erase. Three mathematical results from the early twentieth century — Russell's paradox (1901), Gödel's incompleteness theorems (1931), and Turing's halting problem (1936) — proved that formal systems have built-in limits. No system powerful enough to do interesting work can verify everything about itself. There will always be true statements it cannot prove and questions it cannot answer.

## What does the proof boundary have to do with AI?

AI extends automation dramatically, but it does not dissolve the proof boundary. A large language model can draft a contract, suggest a diagnosis, or generate code — but without an external checker, its outputs are suggestions, not guarantees.

The paper draws a sharp contrast. Systems like AlphaZero achieve superhuman performance at chess and Go because they have a **cheap, unambiguous judge**: the rules of the game. Every move is either legal or illegal. Every game ends in a win, loss, or draw. The system can play millions of games against itself and learn from the results because the feedback is instant and trustworthy.

Most real-world domains have no such judge. A lawyer cannot file a thousand briefs and ask a court to grade them. A doctor cannot run a thousand diagnoses on one patient. In these domains, AI can assist, but the final judgment stays human — not because the AI isn't smart enough, but because no one has built a trusted, mechanical way to check the answer.

This is the **oracle problem**: who defines what "correct" means, which evidence counts, and how disputes get resolved? In chess, the oracle is the rulebook. In a courtroom, it's a judge interpreting precedent. In a hospital, it's a clinician weighing ambiguous evidence. Where the oracle is mechanical, automation thrives. Where the oracle is human, the proof boundary holds.

## What happens when people ignore the proof boundary?

The paper's most concrete argument comes from five case studies where expert teams reviewed systems, performed extensive testing, and catastrophic failure still occurred:

- **Quebec Bridge (1907)**: Dead-load estimates drifted during construction. Warnings were sent. Work continued. The bridge collapsed, killing 75 workers.
- **Therac-25 (1985–87)**: A radiation therapy machine removed hardware safety interlocks and relied on software alone. A race condition — a timing-dependent bug invisible to code review — fired the beam at hundreds of times the intended dose. Patients died.
- **Pentium FDIV (1994)**: Five missing entries in a lookup table caused wrong floating-point answers. Intel had tested millions of inputs. A formal proof checking every entry would have caught it in minutes. The recall cost roughly $475 million.
- **Ariane 5 (1996)**: A 64-bit value was converted to a 16-bit integer. The value overflowed. A decade of work and four satellites were destroyed 37 seconds after liftoff.
- **Toyota (2009)**: An electronic throttle system with extensive testing but no formal proofs led to unintended acceleration incidents. People died.

The pattern is the same in every case: human experts reviewed the system. Testing was extensive. The failure was in a property that *could* have been formally verified but wasn't. A mechanical proof checker can exhaustively inspect all possible interleavings of a concurrent system, or all entries in a lookup table, or all possible input ranges. A human reviewer — no matter how skilled — cannot.

The paper's argument is not that formal verification is easy or cheap. It is that when the cost of failure is high enough, the cost of *not* verifying is higher.

## How did software get here?

The paper traces a progression in which each generation of tools moved another class of checking from human judgment to mechanical verification:

1. **Assembly era (1940s–50s)**: Programmers checked every instruction by hand. Human attention was the only validator.
2. **Compilers (1957+)**: FORTRAN and COBOL mechanized syntax checking. The compiler was the first proof checker most programmers ever met.
3. **Type systems (1970s+)**: Types turned many design errors into compile-time rejections instead of runtime surprises.
4. **Formal methods (1990s+)**: Tools like TLA+ let engineers specify what a system *must always do* and *must never do*, then mechanically check every possible state. Amazon used TLA+ to find bugs in production systems that testing had missed.

Each step narrowed what programmers could express but expanded what could be guaranteed correct. The trade-off is fundamental: **verification demands restriction**. The more general a system, the less you can prove about it. Safety-critical code lives in smaller, more constrained languages precisely because those constraints enable proof.

## What about the human side?

The paper's second half argues that the proof boundary is not just a technical concern — it is a social justice issue.

Wherever a domain can be formalized, automation follows. Those who formalize first extract value. But formalization does not land evenly. A formal checker can say "the rule was followed" with machine certainty while the people affected contest the rule itself. If the rule is unjust, perfect consistency is perfect injustice.

The paper traces this through history: the Nuremberg Laws, apartheid in South Africa, residential schools in Canada, and the U.S. civil rights movement all illustrate cases where rules were followed precisely — and that was the problem. Legality and legitimacy are not the same thing. Martin Luther King Jr. argued from a Birmingham jail cell that obedience to laws that degrade people is itself a moral failure.

The point is not that formal systems are bad. It is that they are powerful, and power must be governed. Whoever writes the rules that formal systems enforce controls what gets automated with machine certainty. The proof boundary determines who has to justify themselves and who gets to act without justification.

## The conclusion

The paper closes with a formulation that ties the technical and human arguments together:

> Proofs do not abolish discretion. They relocate it, explicitly, to the formal rules that define what counts as valid. The oracle becomes the legislature.

The proof boundary is permanent. Gödel proved that. But its *location* — which domains are formalized, which decisions are automated, which rules are enforced — is a human choice. Economic pressure pushes the boundary outward. AI accelerates that push. But only humans can define the oracles that determine correctness. And only humans can decide whether those oracles are just.

The boundary does not move evenly. It can speed access and close doors at the same time. That makes the question of who controls the boundary — who writes the rules, who benefits, and who is harmed — a civic question as much as a technical one. It is, as the paper argues, a never-ending human narrative.
