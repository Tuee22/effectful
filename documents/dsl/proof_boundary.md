# The [Proof Boundary](#glossary-proof-boundary): Why humans will under-utilize AI models

Picture three rooms.

In the first, a lawyer skims a contract the model drafted to save a late night. They slow at the indemnity, termination, and governing-law clauses, knowing one loose sentence can turn into a costly dispute. [1](#ref-1)

In the second, a clinician reviews a routine diabetic retinopathy scan the model flagged with high confidence. They still linger on a borderline lesion, because a single missed bleed can mean preventable blindness. [2](#ref-2)

In the third, a civil engineer scans an AI-flagged crack map from a bridge inspection, grateful for the triage. They double-check midspan fractures and bearing regions before signing off on load ratings. [3](#ref-3)

Now step into the developer's room. The model writes a function, the tests run, the build goes green, and the code ships. No regulator signs the diff. The program either passes or it doesn't. In software, the judge is already wired in.

Why does one domain delegate while others supervise? In the first two rooms, the day ends with a signature. In the last, it ends with a test report. The difference is not model intelligence, but who can verify the output.

---

## Part 0: Hook and Question

This document is written in a formal format, yet no formal checker tells us when it is complete. [Markdown](#glossary-markdown) can be validated. Links can be clicked. But the reasoning still waits for a human verdict. The loop never fully closes: a checklist depends on a checker, a proof depends on a prover, and the chain of certainty ends in a person.

Call this line the [proof boundary](#glossary-proof-boundary): where our rules fully describe the world, and where they fall short. On one side: [mechanical verification](#glossary-mechanical-verification), reproducible and absolute. On the other: human judgment, negotiated and fallible. That boundary explains where AI can be trusted to act and where it must remain an assistant. It is not a defect; it is the foundation of everything that follows.

An argument persuades. A proof compels. You can persuade someone that a bridge is safe. You can also prove that a particular load will not exceed a particular tolerance. The boundary is where those two modes trade places. The judge is the hinge of adoption: where the judge is mechanical, delegation is possible. So the question of AI adoption is: where do we demand a judge that cannot be persuaded, and where do we accept a human signature instead?

This document maps that proof boundary and asks how far we can push it without losing accountability. The boundary moves with evidence, incentives, and institutions, not just with models.

---

## Part I: Catastrophe as the Forcing Function

This [proof boundary](#glossary-proof-boundary) did not appear in a conference paper. It arrived in smoke, steel, and funerals. The pattern is consistent: human judgment is enough, until it is not. When the stakes rise high enough, industry buys proof.

### Quebec Bridge

The Quebec Bridge was to be the longest cantilever bridge on Earth. It collapsed during construction in [1907](#timeline-1907), killing 75 workers. The official inquiries found a familiar pattern: not a lack of equations, but a failure of assumptions. [4](#ref-4)

Engineers underestimated the dead load; deformations were observed; warnings were sent; work continued. Calculation was necessary, but not sufficient. The collapse pushed licensing, codes, standards, and formal review into place. Some elements became mechanically checkable; others remained human. The bridge did not just fail; it rewrote the rules for how confidence must be earned.

### Ariane 5

Thirty-seven seconds after liftoff in [1996](#timeline-1996), Ariane 5 disintegrated. [5](#ref-5)

A 64-bit velocity value was converted to a 16-bit signed integer. The value overflowed, the exception handler crashed, and the backup failed because it ran identical code. The software had worked for Ariane 4; Ariane 5 flew a faster trajectory. The assumption "this value will never exceed that range" failed. A proof is not a property of code alone; it is a property of code within a specification. Redundancy without diversity is replication, not resilience.

### Therac-25

The Therac-25 was a radiation therapy machine. To reduce cost and complexity, engineers removed hardware interlocks and relied on software alone in [1985-1987](#timeline-1985-1987). [6](#ref-6)

Under specific timing, a race condition bypassed safety checks and fired the electron beam at full power. Patients died. The bug was in every machine. Concurrency is the nightmare here: two actions interleave in a way the human mind does not anticipate. A proof checker can enumerate those interleavings; a human cannot. The safety case moved from physical interlocks to logical guarantees, and the burden shifted with it.

### Pentium FDIV

A math professor computed reciprocals of twin primes in [1994](#timeline-1994). The Pentium gave slightly wrong answers. Five missing entries in a lookup table were enough to force a $475 million replacement program. [7](#ref-7)

[Intel](#glossary-intel) ran millions of test vectors. A simple proof would have checked every entry in minutes. The FDIV bug is a microcosm of the [proof boundary](#glossary-proof-boundary): the property was finite and decidable, yet human review missed it. Proof would have been cheaper than reputation repair. When the public heard "rare," they still heard "wrong."

### [Toyota](#glossary-toyota) Unintended Acceleration

A Lexus surged to over 120 mph and crashed in [2009-2011](#timeline-2009-2011), triggering investigations. [NASA](#glossary-nasa)'s analysis found [MISRA C](#glossary-misra-c) violations in the electronic throttle control system. [8](#ref-8)

The system was complex. The code was large. The testing was extensive. Yet the failures happened. As systems scale, human judgment becomes the most fragile component. Once failure is public, the standard of proof rises, and the boundary moves. Complexity does not produce randomness; it produces behavior no one intended, executed with precision.

### Pattern

Expert teams reviewed the systems. Extensive testing was performed. Catastrophic failure still occurred. When consequences are large enough, mechanical proof becomes cheaper than fallible human review. That is the economic engine behind formalization.

We build complex systems, complexity defeats us, so we build [formal systems](#glossary-formal-system) to bound complexity. The boundary shifts when the cost of error makes it worth moving. Standards often appear after disaster, then fade from view until the next failure reminds us why they exist.

---

## Part II: The Software Evolution Toward Proof

Software history reads like a slow migration across that proof boundary. Each era hands a little more verification to machines because humans cannot scale. The pattern repeats: new tools turn "review" into "rejection," and the market learns to accept the judge.

### Assembly Era: Humans as Validators

Early programmers hand-checked every instruction in the [1940s-1950s](#timeline-1940s-1950s). One wrong register could crash the program. Debugging meant reading memory dumps by hand, often with punchcards and deck order as the only paper trail. Human validation was painfully slow and error-prone, because every change required manual inspection. A thousand lines was already a mountain; a hundred thousand was a continent. The desire for automation, for [compilers](#glossary-compiler), for tests, for [static analysis](#glossary-static-analysis) all emerged from the same insight: human attention is finite.

### [Compiler](#glossary-compiler) Revolution

[FORTRAN](#glossary-fortran) and [COBOL](#glossary-cobol) mechanized syntax in [1957-1959](#timeline-1957-1959). [9](#ref-9) Variables must be declared. Parentheses must match. Jumps must land on real labels. The [compiler](#glossary-compiler) was the first proof checker most programmers ever met: a judge that rejects without persuasion. It taught a generation to treat correctness as something a machine could pronounce.

### Type Systems

[Type systems](#glossary-type-system) mechanized whole categories of reasoning in the [1970s](#timeline-1970s). A program either type-checks or it does not. Cheap errors moved from human review into [compiler](#glossary-compiler) rules. By making some errors unrepresentable, type systems shift the proof boundary into the language itself. They turn informal contracts into enforceable structure.

### Functional Programming

Functional languages offered referential transparency and mathematical clarity in the [1980s-1990s](#timeline-1980s-1990s). They were proof-friendly but economically resisted: tooling, talent, and network effects favored imperative languages. People optimize for comprehension, hiring, and speed, not proof. Formal methods are organizational commitments as much as technical ones. The market rarely rewards purity when it conflicts with momentum.

### Distributed Systems

The internet made every program a distributed system. That sounds like scale, but it is really a trust problem. The Byzantine Generals problem in [1982](#timeline-1982) turned the fear into a formal statement: if some nodes can lie or fail, agreement becomes fragile in ways humans do not naturally anticipate. [10](#ref-10)

The difficulty is not just that networks drop packets; it is that every message can arrive late, arrive twice, or arrive out of order. Each ordering is a different universe. A design that works in the lab can fail in production because the one ordering you never tested is the one the world chooses. This is why distributed systems feel haunted: the failure comes from a path you did not imagine, not from a line you forgot to write.

### [Amazon](#glossary-amazon) and [TLA+](#glossary-tla)

[TLA+](#glossary-tla) (Temporal Logic of Actions) arrived in [1999](#timeline-1999) as Leslie Lamport's way of writing system behavior with mathematical precision. It is not code; it is a logic for describing what must always be true and what can never be true. A [model checker](#glossary-model-checker) then explores every possible interleaving to see if reality can violate the spec.

[Amazon](#glossary-amazon) adopted [TLA+](#glossary-tla) in [2011](#timeline-2011) and found deep design flaws in systems already in production. [Model checking](#glossary-model-checker) found bugs no test could. Formal methods became a competitive advantage. [11](#ref-11) The [model checker](#glossary-model-checker) is a ruthless reader: it does not care that the diagram looks plausible.

This was not academic theater. [AWS](#glossary-aws) S3 launched in [2006](#timeline-2006) and Dynamo was published in [2007](#timeline-2007-dynamo) because distributed storage is a practical version of the Byzantine fear: nodes disagree, networks lie, and data must still converge. [TLA+](#glossary-tla) helped teams rehearse those worst-case orderings, the hard versions of Byzantine failure that only show up at scale, and make the guarantees explicit before customers found the cracks.

Formal specification shifts design debate toward explicit [invariants](#glossary-invariant).

### [CompCert](#glossary-compcert) and [seL4](#glossary-sel4)

[CompCert](#glossary-compcert) proves a [C](#glossary-c) [compiler](#glossary-compiler) correct, first released in [2006](#timeline-2006-compcert). [seL4](#glossary-sel4) proves a microkernel correct, with the proof mechanized in [Isabelle/HOL](#glossary-isabelle-hol) in [2009](#timeline-2009-sel4). These rare achievements show the power of compositional proof at scale. [12](#ref-12) [39](#ref-39) Prove the foundation, and the rest of the stack breathes easier.

### Bezos' [API](#glossary-api) Mandate

At [Amazon](#glossary-amazon), Bezos required every team to expose functionality through [APIs](#glossary-api) in [2002](#timeline-2002). The mandate was audacious: no shortcuts, no backdoors, no informal dependencies. If you wanted data from another team, you had to call them like a customer. [13](#ref-13)

It was prescient because it forced the company to behave like a network of services long before "microservices" was a slogan. Infrastructure became software. Software became product. The world learned to trust [APIs](#glossary-api) because they were deterministic and testable. The proof boundary moved again, decades before [LLMs](#glossary-llm) arrived. An API is a treaty: a promise that can be invoked, checked, and enforced.

### Interlude: The Proof Culture

Formal methods are a toolkit and a culture. They ask engineers to speak in a precise language, to name every assumption, to prove every claim. The [proof boundary](#glossary-proof-boundary) is therefore not just an engineering demarcation. It is a cultural compromise between velocity and certainty. It returns whenever failure becomes too expensive to ignore.

---

## Part III: The AI Capability Surge

The AI story is a story of models and judges. A model without a verifier is a rumor; with a verifier, it becomes a tool. The judge is the hinge of adoption, and it swings more often than we admit.

### The [GPU](#glossary-gpu) Pivot and the Medium as the Message

[NVIDIA](#glossary-nvidia) was founded in [1993](#timeline-1993) to build high-end [GPUs](#glossary-gpu) for PC gamers. [17](#ref-17)

Academics discovered that [GPUs](#glossary-gpu) were good at linear algebra. [CUDA](#glossary-cuda) in [2006](#timeline-2006) turned graphics cards into programmable devices. Consumer hardware became a scientific instrument. [18](#ref-18)

When AlexNet showed the deep learning advantage in [2012](#timeline-2012-alexnet) and the [transformer](#glossary-transformer) era arrived in [2017](#timeline-2017-transformer), it rode on the back of that pivot. Scale unlocked capability, but reliability appears where verification exists. The medium shaped the message. [20](#ref-20)

Jensen Huang did not set out to build AI hardware. He set out to win gamers. The bet in [2006](#timeline-2006) looked like a graphics optimization story: make the chip programmable, make shaders flexible, make games sing. When AlexNet landed in [2012](#timeline-2012-alexnet), that same design turned out to be perfect for matrix math. The surprise was structural, not tactical: a company built for pixels became the most important supplier for intelligence.

It is hard to overstate how unexpected that was in [1993](#timeline-1993). [NVIDIA](#glossary-nvidia) was a gaming brand, not a supercomputing vendor. Yet the pivot compounded. Programmability enabled research; research demanded scale; scale demanded more GPUs. By the time the [transformer](#glossary-transformer) era arrived in [2017](#timeline-2017-transformer), the world's largest provider of AI hardware had been assembled almost by accident.

### [Benchmarks](#glossary-benchmark) as Mechanical Judges

[HumanEval](#glossary-humaneval) in [2021](#timeline-2021-humaneval), [AlphaCode](#glossary-alphacode) in [2022](#timeline-2022-alphacode), and [DIN-SQL](#glossary-din-sql) in [2023](#timeline-2023-din-sql) share a key property: outputs are mechanically checkable. AI looks good where the judge is a machine. It looks unreliable where the judge is human. [19](#ref-19) Cheap verification makes brute-force iteration possible, and iteration changes the game.

In human domains, iteration is expensive. A lawyer cannot file a thousand briefs and ask a judge to grade them. A doctor cannot attempt a thousand diagnoses on one patient. The proof boundary is therefore about iteration as much as verification.

### Formal Theorem Proving [benchmarks](#glossary-benchmark)

Formal math [benchmarks](#glossary-benchmark) show strong gains when proofs are checked by a [formal system](#glossary-formal-system), not by human intuition. Results like [HILBERT](#glossary-hilbert) on [PutnamBench](#glossary-putnambench) in [2024](#timeline-2024-hilbert) make the pattern explicit. [32](#ref-32) The improvement is not mysterious; it is the effect of fast, unforgiving feedback.

The pattern is the same across these examples: a formal judge turns exploration into iteration, and iteration turns capability into reliability.

### [MCP](#glossary-mcp) and the Connection Layer

The Model Context Protocol ([MCP](#glossary-mcp)) standardizes how models call tools in [2024](#timeline-2024-mcp). It lowers integration friction and makes verification loops easier to wire into production systems. It accelerates adoption without changing the proof boundary. [31](#ref-31) It is plumbing, but plumbing changes what is easy to build.

MCP does not create trust; it makes it cheaper to connect to whatever creates trust. That is a subtle but powerful shift.

The deeper implication is automation at scale. We already have [APIs](#glossary-api) for almost anything a company can do. MCP makes it possible for any [LLM](#glossary-llm) to issue those instructions through a standard interface. In principle, that means the model can automate anything the API can reach. In practice, most humans do not feel safe giving a model that level of agency, because the verification loop is still social, not mechanical. MCP widens the gap between what is possible and what feels accountable.

### [AlphaGo](#glossary-alphago), [AlphaZero](#glossary-alphazero), and the External Judge

[AlphaGo](#glossary-alphago) surpassed human champions in Go in [2016](#timeline-2016-alphago) by learning in a formal environment. A [legal-moves checker](#glossary-legal-moves-checker) tells the system what is allowed. [21](#ref-21)

[AlphaZero](#glossary-alphazero) learned from self-play in [2017](#timeline-2017-alphazero). It needed an external verifier that could tell it which moves were legal and who won. The [self-play](#glossary-self-play) loop is only possible because the environment is formal. [22](#ref-22)

[reinforcement learning](#glossary-rl) requires an external judge. Without a formal environment, RL cannot scale beyond imitation. The judge is the proof checker of the game.

This is why RL flourishes in games and lags in open-ended domains. The world is not a board with legal moves.

### [AlphaProof](#glossary-alphaproof) and Formal Math

[AlphaProof](#glossary-alphaproof) reached the silver level on IMO problems in [2024](#timeline-2024-alphaproof) with [Lean](#glossary-lean) verifying the proofs. The model proposes, the verifier judges, and the system iterates until it wins. [23](#ref-23)

Formal mathematics is a near-perfect laboratory: a proof is either correct or it is not. That is why models improve fastest where the rules are explicit. The result is not just better scores; it is a cleaner separation between invention and validation.

### Medical Imaging: The Assistant Ceiling

Medical imaging offers a different proof boundary. Models can detect patterns and match specialists on specific tasks, but the outputs are not formally verifiable. A diagnosis is not a theorem; it is a judgment. Retinopathy results in [2016](#timeline-2016-retinopathy) and dermatology results in [2017](#timeline-2017-dermatology) show the ceiling. [2](#ref-2) [24](#ref-24)

These systems are used as assistants; a physician signs off. The signature is not just legal cover; it is where responsibility lives. When the case is ambiguous, the model cannot carry the moral weight. Partial automation exists, but the final responsibility still sits with a person.

### Legal Drafting and the Hallucination Trap

In law, verification is not mechanical. A brief can be grammatically correct and logically plausible yet still be wrong. When a model hallucinates a citation, the error is not caught by syntax. It is caught by a human who knows the domain.

The deeper problem is that hallucinations are not an edge case; they are a structural risk in [LLMs](#glossary-llm). The model is trained to predict plausible continuations, not to guarantee truth. If the prompt looks like it should have a case, the model can invent one that matches the pattern. Without external grounding, the system confuses fluency for evidence, and legal writing is precisely the domain where fluency can hide error.

Avoiding this is hard because the model has no built-in notion of "I don't know." It can be instructed to abstain, but the training signal rewards confident completion. Retrieval systems help, yet they introduce their own failure modes: missing sources, mismatched citations, or partial context. The result is a seductive failure: the output looks more authoritative the more incorrect it becomes.

The Stanford HAI / RegLab analysis in [2024](#timeline-2024-hai-reglab) documents high hallucination rates. The field cannot delegate until there is a verifier that can mechanically check citations, arguments, and precedent. That verifier does not yet exist. [1](#ref-1)

The practical result is an assistant ceiling. A model cannot be sanctioned, disbarred, or held in contempt. Institutions cannot delegate without accountability, so adoption remains cautious until verification frameworks and liability regimes mature. The ceiling is institutional, not just technical.

Then the paradox arrives.

## Part IV: The Paradox and the Boundary

In software, tests and type checks make verification cheap, so teams ship quickly. In law, every draft still needs a licensed signer, so deployment stays cautious. The proof boundary shows up in those budgets and schedules.

### Accountability Asymmetry

A radiologist signs a report. A lawyer files a brief. An engineer stamps a design. A developer merges the code. The model signs nothing. There is no license to revoke, no liability to assign, no professional reputation to protect. Without accountability, authority cannot be delegated. The signature binds a person to a claim in a way no model can accept.

Accountability is also why automation feels acceptable in some industries and threatening in others. In software, errors can be patched. In law or medicine, errors become records that follow people.

### [Decidability](#glossary-decidability) and the Cost of Certainty

When a property is decidable, it can be mechanically verified. When it is not, verification becomes a human judgment. Certainty is scarce. The more general the system, the less we can prove about it. The more we want proof, the more we must restrict the system. Safety-critical code lives in smaller languages for a reason.

Every gain in expressiveness is a loss in provability. The proof boundary is where we decide how much freedom to trade for certainty.

This is why high-assurance domains adopt restricted subsets and strict coding standards. The language itself becomes part of the proof; [MISRA C](#glossary-misra-c) is as much a boundary as a rulebook.
 
The theoretical ceiling sits beneath the engineering practice. Logic itself pushes back. The paradox is that the more we formalize, the more we discover what formalization cannot contain.

### Russell and the Trap of Self-Reference

Bertrand Russell discovered [Russell's paradox](#glossary-russells-paradox) in [1901](#timeline-1901). Consider the set of all sets that do not contain themselves. Does that set contain itself? If it does, it should not. If it does not, it should. The system collapses. [14](#ref-14)

[Russell's paradox](#glossary-russells-paradox) is a warning about what happens when a system tries to talk about itself without care. The result is startling: a few innocent-looking words detonate the logic underneath them. [formal systems](#glossary-formal-system) place rules on themselves to avoid contradiction. The proof boundary is a set of fences built to avoid paradox. For AI, this matters because models routinely generate statements about their own reasoning. The boundary is the line that keeps those statements from becoming circular authority.

### Godel and the Sentence That Escapes

Kurt Godel showed in [1931](#timeline-1931) that any sufficiently powerful [formal system](#glossary-formal-system) contains statements that are true but unprovable within that system. This is the core of [incompleteness](#glossary-incompleteness). [15](#ref-15)

Godel's theorem is counter-intuitive because it turns a dream of perfect rigor into a limit of rigor. No [formal system](#glossary-formal-system) can be both complete and consistent when it is rich enough to express arithmetic. There will always be truths it cannot prove. Completeness is not a realistic expectation. The proof boundary is a concession to this limitation.

Douglas Hofstadter argued in *Godel, Escher, Bach* in [1979](#timeline-1979-geb) that formal rules make the world smaller: every rule is a filter, and every filter excludes nuance. Formal systems gain power by shrinking the universe they can talk about. That is why they are reliable, and why they feel austere. [29](#ref-29)

### Turing and the [halting problem](#glossary-halting-problem)

Alan Turing showed in [1936](#timeline-1936) that there is no general algorithm that can decide whether an arbitrary program will halt. The [halting problem](#glossary-halting-problem) is the computational version of Russell and Godel. [16](#ref-16)

There is no universal verifier. The surprise is that even with a complete description of a program, the question "will it stop?" is unanswerable in general. We can only decide termination for programs that belong to restricted classes. That restriction is the hidden cost of proof. When a system is formally verified, it is because the system has been tamed.

The critical truth is about the relationship between humans and formal systems. We build formal logic to escape ambiguity, then discover the escape hatch still ends in a human choice: what to formalize, what to exclude, and when the model is "close enough." [Decidability](#glossary-decidability) is the currency of proof, but it comes from narrowing the world. Those narrowed worlds are reliable, and also smaller than the lives we live.

Russell, Godel, and Turing tell us that [formal verification](#glossary-formal-verification) is not a universal solvent. It works when we design systems that accept its constraints. The proof boundary is a trade-off we negotiate over and over. At some point the story ends with a human saying, "This is good enough." That is not a failure of logic; it is the cost of being human. In practice, every verifier still needs an external context and a human decision to trust it.

---

## Part V: Verification Infrastructure and Self-Improvement

[Reinforcement learning](#glossary-rl) is often described as a model learning through trial and error. Without an environment that can tell it what counts as a valid trial, there is no learning loop. Feedback is the oxygen.

In Go, the rules define what is legal. The environment enforces those rules. Without that checker, [AlphaZero](#glossary-alphazero) in [2017](#timeline-2017-alphazero) would be lost. It would not learn; it would hallucinate. The checker is the simplest possible proof boundary.

That is the suspense in [AlphaGo](#glossary-alphago)'s story in [2016](#timeline-2016-alphago) and [AlphaZero](#glossary-alphazero)'s in [2017](#timeline-2017-alphazero): the genius is not just the model, it is the judge. The external environment makes self-play possible, and it makes errors visible. The same structure appears in [proof assistants](#glossary-proof-assistant), where a model can propose steps but the checker accepts or rejects them, without negotiation. [21](#ref-21) [22](#ref-22)

This is why pure language models fall short in games. They can describe Go, but they cannot play it at [AlphaZero](#glossary-alphazero) levels because they do not have a [legal-moves checker](#glossary-legal-moves-checker) embedded in their training loop. Stories can teach style; they cannot enforce legality.

The deeper lesson is temporal: verifiers came first. Verification infrastructure predated modern [LLMs](#glossary-llm) by decades. [SQL](#glossary-sql) standards in [1986](#timeline-1986-sql), [proof assistants](#glossary-proof-assistant) like [Coq](#glossary-coq) in [1989](#timeline-1989-coq), functional languages like [Haskell](#glossary-haskell) in [1990](#timeline-1990-haskell), [TLA+](#glossary-tla) in [1999](#timeline-1999), and [SMT solvers](#glossary-smt-solver) like [Z3](#glossary-z3) in [2007](#timeline-2007) all existed long before transformers. [34](#ref-34) [40](#ref-40) [41](#ref-41) The proof boundary did not arrive after AI; it enabled AI. The data from these systems is cleaner because it is already judged.

## Conclusion

### The Medium, the Message, and the Human Governor

Marshall McLuhan wrote in [1994](#timeline-1994-mcluhan), "The medium is the message." The telegraph compressed time. The telephone collapsed distance. Television changed how politics felt. AI is now doing the same. It compresses knowledge work, changes who gets to decide, and alters the pace of institutional response. [25](#ref-25)

Arthur Charles Clarke wrote in [2000](#timeline-2000-clarke), "Any sufficiently advanced technology is indistinguishable from magic." [26](#ref-26) But magic is not governance. Awe can dull judgment. The proof boundary is the antidote to awe.

The internet taught us that new media can reshape human health. Social media amplified connection and loneliness, knowledge and misinformation. Australia's under-16 social media law in [2024](#timeline-2024-australia-law) is a reminder that society will eventually regulate what it cannot absorb. [27](#ref-27)

The lesson is that technology is powerful enough to require governance. The more powerful the medium, the more carefully we demand a judge. The pace of adoption will therefore be set by institutions, not just by models.

The central insight stands: we will under-utilize AI inefficiently rather than over-utilize it unsafely. That friction is not a tragedy. It is a feature of human governance. In that sense, the proof boundary is not an obstacle to progress; it is how progress becomes legitimate.

---

### A Gentle Godelian Smile

This document is written in a formal format. It has headings, references, and links. It can be parsed. It can be linted. [Markdown](#glossary-markdown) can be checked. But no proof checker can tell you when it is finished.

Godel showed in [1931](#timeline-1931) that there is no way to know if a process following formal logic will end. If logic itself cannot certify its own finish line, a document about logic cannot either.

There is a quiet humor here. The document is about proof, yet its completeness is unprovable. The document is about boundaries, yet its own limit is a human decision.

A talented human writer who has read this should feel at ease: language models are not likely to win literary awards anytime soon. If the ideas here resonate, read two masterpieces: Yuval Noah Harari's *Sapiens* from [2015](#timeline-2015-sapiens) and Douglas Hofstadter's *Godel, Escher, Bach* from [1979](#timeline-1979-geb). [28](#ref-28) [29](#ref-29)

The human author thanks the [LLMs](#glossary-llm) for their attempt at writing like these two masters. The modest parting shot is this document's core thesis: we will naturally end up under-utilizing AI inefficiently rather than over-utilizing it unsafely.

---

## Appendices

### Appendix A: Chronological Thread of Proof and Power

It helps to see the proof boundary as a story across time, not just a concept on paper. The boundary has moved before. It will move again. Its motion follows a recognizable pattern: expansion through necessity, consolidation through standards, and constraint through the limits of logic.

Timeline (single sequence):
- <a id="timeline-1901"></a>1901: [Russell's paradox](#glossary-russells-paradox) exposes contradictions in naive set theory.
- <a id="timeline-1907"></a>1907: Quebec Bridge collapse.
- <a id="timeline-1931"></a>1931: Godel proves [incompleteness](#glossary-incompleteness) limits in [formal systems](#glossary-formal-system).
- <a id="timeline-1936"></a>1936: Turing proves the [halting problem](#glossary-halting-problem) is undecidable.
- <a id="timeline-1940s-1950s"></a>1940s-1950s: Assembly era manual validation.
- <a id="timeline-1957-1959"></a>1957-1959: [Compiler](#glossary-compiler) revolution ([FORTRAN](#glossary-fortran), [COBOL](#glossary-cobol)).
- <a id="timeline-1970s"></a>1970s: [type systems](#glossary-type-system) take hold ([Pascal](#glossary-pascal), [C](#glossary-c), [ML](#glossary-ml)).
- <a id="timeline-1979-geb"></a>1979: Hofstadter publishes *Godel, Escher, Bach*.
- <a id="timeline-1982"></a>1982: Byzantine Generals problem formalizes distributed agreement limits.
- <a id="timeline-1985-cpp"></a>1985: [C++](#glossary-cpp) emerges as a systems language.
- <a id="timeline-1986-isabelle-hol"></a>1986: [Isabelle/HOL](#glossary-isabelle-hol) [proof assistant](#glossary-proof-assistant) introduced.
- <a id="timeline-1986-sql"></a>1986: [SQL](#glossary-sql) standardizes core semantics.
- <a id="timeline-1985-1987"></a>1985-1987: Therac-25 overdoses and patient deaths.
- <a id="timeline-1980s-1990s"></a>1980s-1990s: Functional programming emerges (Miranda, [Haskell](#glossary-haskell)).
- <a id="timeline-1989-coq"></a>1989: [Coq](#glossary-coq) [proof assistant](#glossary-proof-assistant) introduced.
- <a id="timeline-1990-haskell"></a>1990: [Haskell](#glossary-haskell) launches.
- <a id="timeline-1993"></a>1993: [NVIDIA](#glossary-nvidia) founded for PC gaming [GPUs](#glossary-gpu).
- <a id="timeline-1994"></a>1994: Pentium FDIV bug and recall.
- <a id="timeline-1994-mcluhan"></a>1994: MIT Press reissues McLuhan's *Understanding Media*.
- <a id="timeline-1996"></a>1996: Ariane 5 explosion at 37 seconds.
- <a id="timeline-1999"></a>1999: [TLA+](#glossary-tla) formal methods mature for distributed systems.
- <a id="timeline-2000-clarke"></a>2000: Clarke's *Profiles of the Future* reissued.
- <a id="timeline-2002"></a>2002: Bezos [API](#glossary-api) mandate and internal service externalization.
- <a id="timeline-2006"></a>2006: [AWS](#glossary-aws) launches S3 and EC2; [CUDA](#glossary-cuda) enables general [GPU](#glossary-gpu) computing.
- <a id="timeline-2006-compcert"></a>2006: [CompCert](#glossary-compcert) project releases.
- <a id="timeline-2007-dynamo"></a>2007: [Amazon](#glossary-amazon) publishes the Dynamo key-value store design.
- <a id="timeline-2007"></a>2007: [Z3](#glossary-z3) [SMT solver](#glossary-smt-solver) released.
- <a id="timeline-2009-sel4"></a>2009: [seL4](#glossary-sel4) proof published.
- <a id="timeline-2009-2011"></a>2009-2011: [Toyota](#glossary-toyota) unintended acceleration crisis.
- <a id="timeline-2010-rust"></a>2010: [Rust](#glossary-rust) project begins.
- <a id="timeline-2011"></a>2011: [Amazon](#glossary-amazon) uses [TLA+](#glossary-tla) to find deep distributed-system bugs.
- <a id="timeline-2012-alexnet"></a>2012: AlexNet proves [GPU](#glossary-gpu) advantage for deep learning.
- <a id="timeline-2015-sapiens"></a>2015: Harari publishes *Sapiens*.
- <a id="timeline-2016-alphago"></a>2016: [AlphaGo](#glossary-alphago) defeats top human players in Go.
- <a id="timeline-2016-retinopathy"></a>2016: Retinopathy model validation published.
- <a id="timeline-2017-transformer"></a>2017: [Transformer](#glossary-transformer) architecture enables scalable [LLMs](#glossary-llm).
- <a id="timeline-2017-bridge-ai"></a>2017: Deep learning crack detection appears in civil infrastructure inspection.
- <a id="timeline-2017-alphazero"></a>2017: [AlphaZero](#glossary-alphazero) demonstrates self-play learning.
- <a id="timeline-2017-dermatology"></a>2017: Dermatology classifier reaches specialist-level accuracy.
- <a id="timeline-2017-plus"></a>2017+: Deep learning medical imaging breakthroughs broaden.
- <a id="timeline-2018-plus"></a>2018+: [formal verification](#glossary-formal-verification) case studies mature ([CompCert](#glossary-compcert), [seL4](#glossary-sel4)).
- <a id="timeline-2020-ross"></a>2020: [ROSS Intelligence](#glossary-ross) shuts down amid litigation.
- <a id="timeline-2021-copilot"></a>2021: [GitHub](#glossary-github) [Copilot](#glossary-copilot) launches.
- <a id="timeline-2021-humaneval"></a>2021: [HumanEval](#glossary-humaneval) benchmark released.
- <a id="timeline-2022-chatgpt"></a>2022: [OpenAI](#glossary-openai) launches [ChatGPT](#glossary-chatgpt); [LLMs](#glossary-llm) go mainstream.
- <a id="timeline-2022-alphacode"></a>2022: [AlphaCode](#glossary-alphacode) results published.
- <a id="timeline-2022-2024"></a>2022-2024: [FDA](#glossary-fda) approvals for AI devices rise; clinical adoption remains low.
- <a id="timeline-2023-mata"></a>2023: Mata v Avianca sanctions over fake citations.
- <a id="timeline-2023-din-sql"></a>2023: [DIN-SQL](#glossary-din-sql) benchmark released.
- <a id="timeline-2024-mcp"></a>2024: [MCP](#glossary-mcp) standardizes tool access for [LLMs](#glossary-llm).
- <a id="timeline-2024-hai-reglab"></a>2024: Stanford HAI / RegLab hallucination analysis published.
- <a id="timeline-2024-alphaproof"></a>2024: [AlphaProof](#glossary-alphaproof) solves IMO problems at silver level; [Lean](#glossary-lean) verifies proofs.
- <a id="timeline-2024-hilbert"></a>2024: [HILBERT](#glossary-hilbert) reaches ~70% on [PutnamBench](#glossary-putnambench) formal proofs.
- <a id="timeline-2024-australia-law"></a>2024: Australia enacts under-16 social media law.

In the early mechanical era, proof lived in materials. The Quebec Bridge collapse in [1907](#timeline-1907) forced assumptions into formal review and standards.

In the mid-twentieth century, proof moved into logic. Russell showed paradox in [1901](#timeline-1901), Godel showed [incompleteness](#glossary-incompleteness) in [1931](#timeline-1931), Turing showed that some problems are undecidable in [1936](#timeline-1936). [14](#ref-14) [15](#ref-15) [16](#ref-16)

In the late twentieth century, proof moved into software. [compilers](#glossary-compiler) in [1957-1959](#timeline-1957-1959) and [type systems](#glossary-type-system) in the [1970s](#timeline-1970s) became everyday judges. Distributed systems then forced a tighter boundary after [1982](#timeline-1982): state space exploded, informal reasoning failed, and formal specification became survival. [11](#ref-11)

The 2010s introduced another shift. Deep learning models grew in capability, but reliability grew only where verification existed. The [GPU](#glossary-gpu) pivot is part of this thread.

Today, [proof assistants](#glossary-proof-assistant) and external evaluators are becoming the backbone of AI progress. [self-play](#glossary-self-play) works because a verifier exists. Code assistants thrive because the environment is formal enough to judge.

### Appendix B: Glossary

- <a id="glossary-proof-boundary"></a>**Proof boundary**: The line between what can be verified mechanically and what must be judged by humans.
- <a id="glossary-formal-verification"></a>**Formal verification**: Mathematical proof that a system satisfies a specification under explicit assumptions.
- <a id="glossary-mechanical-verification"></a>**Mechanical verification**: Automated checking that enforces rules without human judgment.
- <a id="glossary-decidability"></a>**Decidability**: Whether a property can be determined by a terminating algorithm.
- <a id="glossary-formal-system"></a>**Formal system**: A language plus rules for deriving valid statements.
- <a id="glossary-invariant"></a>**Invariant**: A property that must hold for all reachable states of a system.
- <a id="glossary-model-checker"></a>**model checker**: A tool that exhaustively explores state space to find violations of a specification.
- <a id="glossary-proof-assistant"></a>**proof assistant**: A tool that helps construct and verify proofs in a formal system.
- <a id="glossary-type-system"></a>**type system**: A formal discipline that classifies program terms and prevents invalid operations.
- <a id="glossary-compiler"></a>**Compiler**: A program that translates source code into another form while enforcing formal rules.
- <a id="glossary-static-analysis"></a>**Static analysis**: Automated reasoning about code without executing it.
- <a id="glossary-tla"></a>**TLA+**: A specification language for concurrent and distributed systems.
- <a id="glossary-tlc"></a>**TLC**: The TLA+ model checker that explores state spaces and checks invariants.
- <a id="glossary-coq"></a>**Coq**: A proof assistant based on dependent type theory.
- <a id="glossary-isabelle-hol"></a>**Isabelle/HOL**: A proof assistant and higher-order logic environment with large, machine-checked libraries.
- <a id="glossary-lean"></a>**Lean**: A proof assistant used for formal mathematics and program verification.
- <a id="glossary-compcert"></a>**CompCert**: A formally verified C compiler proved correct in Coq.
- <a id="glossary-sel4"></a>**seL4**: A formally verified microkernel with a machine-checked proof of correctness.
- <a id="glossary-adt"></a>**ADT (Algebraic Data Type)**: Types built from sums and products to make invalid states unrepresentable.
- <a id="glossary-totality"></a>**Totality**: A function produces an output for every possible input.
- <a id="glossary-purity"></a>**Purity**: A function's output depends only on its inputs, with no side effects.
- <a id="glossary-llm"></a>**LLM (Large Language Model)**: A model trained to predict text at scale.
- <a id="glossary-transformer"></a>**Transformer**: A neural architecture based on attention that scales efficiently with data and compute.
- <a id="glossary-smt-solver"></a>**SMT solver**: Automated solver for logical formulas in satisfiability modulo theories.
- <a id="glossary-z3"></a>**Z3**: A widely used SMT solver developed by Microsoft Research.
- <a id="glossary-rl"></a>**Reinforcement learning**: Learning by interaction with an environment using rewards.
- <a id="glossary-self-play"></a>**Self-play**: Training by playing against copies of oneself in a formal environment.
- <a id="glossary-legal-moves-checker"></a>**Legal-moves checker**: An external rule engine that rejects invalid actions.
- <a id="glossary-humaneval"></a>**HumanEval**: A code benchmark with mechanically checkable tests.
- <a id="glossary-alphacode"></a>**AlphaCode**: A code-generation system evaluated on competitive programming tasks.
- <a id="glossary-din-sql"></a>**DIN-SQL**: A benchmark for text-to-SQL with executable verification.
- <a id="glossary-mcp"></a>**MCP (Model Context Protocol)**: A standard for tool access by models.
- <a id="glossary-alphago"></a>**AlphaGo**: A Go system that learned via self-play and a legal-moves environment.
- <a id="glossary-alphazero"></a>**AlphaZero**: A general self-play system for Go, Chess, and Shogi.
- <a id="glossary-alphaproof"></a>**AlphaProof**: A system that generates proofs verified by Lean.
- <a id="glossary-putnambench"></a>**PutnamBench**: A formal mathematics benchmark.
- <a id="glossary-hilbert"></a>**HILBERT**: A system reporting results on PutnamBench.
- <a id="glossary-cuda"></a>**CUDA**: NVIDIA's platform for general-purpose GPU computing.
- <a id="glossary-gpu"></a>**GPU**: A processor optimized for parallel computation.
- <a id="glossary-sql"></a>**SQL**: A query language with formal, executable semantics.
- <a id="glossary-rust"></a>**Rust**: A language emphasizing memory safety and strict compile-time checks.
- <a id="glossary-misra-c"></a>**MISRA C**: A safety-oriented C coding standard.
- <a id="glossary-halting-problem"></a>**Halting problem**: The undecidable question of whether a program terminates.
- <a id="glossary-incompleteness"></a>**Incompleteness**: The limit that some truths cannot be proven within a system.
- <a id="glossary-russells-paradox"></a>**Russell's paradox**: A self-reference paradox in naive set theory.
- <a id="glossary-oracle-problem"></a>**oracle problem**: The difficulty of defining ground truth for evaluation in messy domains.
- <a id="glossary-compositional-verification"></a>**Compositional verification**: Proof by composing verified components.
- <a id="glossary-conformance-test"></a>**conformance test**: A test that checks behavior against a specification.
- <a id="glossary-benchmark"></a>**Benchmark**: A standardized task for evaluation with defined scoring.
- <a id="glossary-api"></a>**API (Application Programming Interface)**: A formal interface that defines how software components interact.
- <a id="glossary-fortran"></a>**FORTRAN**: One of the earliest high-level programming languages, designed for scientific computing.
- <a id="glossary-cobol"></a>**COBOL**: A business-oriented programming language designed for data processing.
- <a id="glossary-pascal"></a>**Pascal**: A language designed to encourage structured programming.
- <a id="glossary-c"></a>**C**: A low-level systems programming language with manual memory control.
- <a id="glossary-ml"></a>**ML**: A family of functional languages with strong static typing.
- <a id="glossary-markdown"></a>**Markdown**: A lightweight markup language for structured text and links.
- <a id="glossary-haskell"></a>**Haskell**: A purely functional programming language with strong type systems.
- <a id="glossary-cpp"></a>**C++**: A systems language extending C with object-oriented and generic features.
- <a id="glossary-nvidia"></a>**NVIDIA**: A company known for GPUs and CUDA.
- <a id="glossary-amazon"></a>**Amazon**: A technology company whose infrastructure work popularized formal methods like TLA+.
- <a id="glossary-aws"></a>**AWS (Amazon Web Services)**: Amazon's cloud platform.
- <a id="glossary-github"></a>**GitHub**: A platform for hosting and collaborating on code.
- <a id="glossary-copilot"></a>**GitHub Copilot**: A code assistant product powered by LLMs.
- <a id="glossary-openai"></a>**OpenAI**: An AI research and product company.
- <a id="glossary-chatgpt"></a>**ChatGPT**: A conversational LLM product by OpenAI.
- <a id="glossary-anthropic"></a>**Anthropic**: An AI company behind the Model Context Protocol.
- <a id="glossary-deepmind"></a>**DeepMind**: An AI research lab known for AlphaGo and AlphaZero.
- <a id="glossary-intel"></a>**Intel**: A semiconductor company behind the Pentium processors.
- <a id="glossary-toyota"></a>**Toyota**: An automaker involved in unintended-acceleration investigations.
- <a id="glossary-nasa"></a>**NASA**: The U.S. space agency involved in automotive software analysis reports.
- <a id="glossary-fda"></a>**FDA**: The U.S. Food and Drug Administration, which clears medical AI devices.
- <a id="glossary-ross"></a>**ROSS Intelligence**: A legal AI company involved in litigation over training data.
- <a id="glossary-thomson-reuters"></a>**Thomson Reuters**: A publisher and information services company involved in ROSS litigation.


## References

1. <a id="ref-1"></a> [1] Stanford HAI / RegLab report (2024) and arXiv:2401.01301. https://hai.stanford.edu/news/hallucinating-law-legal-mistakes-large-language-models-are-pervasive; https://arxiv.org/abs/2401.01301.
2. <a id="ref-2"></a> [2] Gulshan et al., "Development and Validation of a Deep Learning Algorithm for Detection of Diabetic Retinopathy," JAMA (2016). https://pubmed.ncbi.nlm.nih.gov/27898976/.
3. <a id="ref-3"></a> [3] Cha et al., "Deep Learning-Based Crack Damage Detection Using Convolutional Neural Networks" (2017). https://doi.org/10.1111/mice.12263.
4. <a id="ref-4"></a> [4] Report of the Royal Commission on the Quebec Bridge collapse (Government of Canada). https://publications.gc.ca/site/eng/9.827964/publication.html.
5. <a id="ref-5"></a> [5] Ariane 5 Flight 501 Failure Report. https://www.ima.umn.edu/~arnold/disasters/ariane5rep.html.
6. <a id="ref-6"></a> [6] Leveson & Turner, "An Investigation of the Therac-25 Accidents," *IEEE Computer* (1993). https://ieeexplore.ieee.org/document/274940.
7. <a id="ref-7"></a> [7] Edelman, "The Pentium(R) floating point division bug" (1995). https://www-math.mit.edu/~edelman/homepage/papers/pentiumbug.pdf.
8. <a id="ref-8"></a> [8] NHTSA/NASA report on Toyota ETC; MISRA C. https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/811361; https://www.misra.org.uk/.
9. <a id="ref-9"></a> [9] Backus et al., "The FORTRAN Automatic Coding System" (1957); CODASYL COBOL Report (Apr 1960). https://softwarepreservation.computerhistory.org/FORTRAN/paper/BackusEtAl-FortranAutomaticCodingSystem-1957.pdf; https://archive.org/download/bitsavers_codasylCOB_6843924/COBOL_Report_Apr60_text.pdf.
10. <a id="ref-10"></a> [10] Lamport, Shostak, Pease, "The Byzantine Generals Problem" (1982). https://lamport.azurewebsites.net/pubs/byz.pdf.
11. <a id="ref-11"></a> [11] TLA+ overview; Dynamo: Amazon's Highly Available Key-value Store; Amazon S3 user guide. https://lamport.azurewebsites.net/tla/tla.html; https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf; https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html.
12. <a id="ref-12"></a> [12] CompCert project; seL4 SOSP 2009. https://compcert.inria.fr/; https://sel4.systems/publications/sel4-sosp09.pdf.
13. <a id="ref-13"></a> [13] Stone, *The Everything Store* (Little, Brown, 2013). https://www.hachettebookgroup.com/titles/brad-stone/the-everything-store/9780316219266/.
14. <a id="ref-14"></a> [14] Stanford Encyclopedia of Philosophy, "Russell's Paradox." https://plato.stanford.edu/entries/russell-paradox/.
15. <a id="ref-15"></a> [15] Godel (1931), *Monatshefte fuer Mathematik*. https://link.springer.com/article/10.1007/BF01700692.
16. <a id="ref-16"></a> [16] Turing (1936), "On Computable Numbers." https://www.cs.virginia.edu/~robins/Turing_Paper_1936.pdf.
17. <a id="ref-17"></a> [17] NVIDIA Corporation, Form S-1 (1999). https://www.sec.gov/Archives/edgar/data/1045810/0001045810-99-000001.txt.
18. <a id="ref-18"></a> [18] Nickolls et al., "Scalable Parallel Programming with CUDA," *ACM Queue* (2008). https://doi.org/10.1145/1365490.1365500.
19. <a id="ref-19"></a> [19] HumanEval; AlphaCode; DIN-SQL. https://arxiv.org/abs/2107.03374; https://arxiv.org/abs/2203.07814; https://arxiv.org/abs/2304.11015.
20. <a id="ref-20"></a> [20] Vaswani et al., "Attention Is All You Need" (2017). https://arxiv.org/abs/1706.03762.
21. <a id="ref-21"></a> [21] Silver et al., "Mastering the game of Go with deep neural networks and tree search," *Nature* (2016). https://www.nature.com/articles/nature16961.
22. <a id="ref-22"></a> [22] AlphaZero arXiv preprint (2017); *Nature* (2018). https://arxiv.org/abs/1712.01815; https://www.nature.com/articles/s41586-018-0107-1.
23. <a id="ref-23"></a> [23] AlphaProof announcement; AlphaGeometry2 technical report; Lean project. https://deepmind.google/blog/ai-solves-imo-problems-at-silver-medal-level/; https://arxiv.org/abs/2502.03544; https://leanprover.github.io/.
24. <a id="ref-24"></a> [24] Esteva et al., "Dermatologist-level classification of skin cancer," *Nature* (2017). https://www.nature.com/articles/nature21056.
25. <a id="ref-25"></a> [25] McLuhan, *Understanding Media* (MIT Press, 1994), ISBN 9780262631594. https://mitpress.mit.edu/9780262631594/understanding-media/.
26. <a id="ref-26"></a> [26] Clarke, *Profiles of the Future* (Hachette UK / Orion, 2000), ISBN 9780575121829. https://books.google.com/books?vid=ISBN9780575121829.
27. <a id="ref-27"></a> [27] Australia under-16 social media law (2024). https://www.legislation.gov.au/Details/C2024A00114.
28. <a id="ref-28"></a> [28] Harari, *Sapiens* (Harper, 2015), ISBN 9780062316097. https://books.google.com/books?vid=ISBN9780062316097.
29. <a id="ref-29"></a> [29] Hofstadter, *Godel, Escher, Bach* (Basic Books, 1999), ISBN 9780465026562. https://www.hachettebookgroup.com/titles/douglas-r-hofstadter/godel-escher-bach/9780465026562/.
30. <a id="ref-30"></a> [30] "The Impact of AI on Developer Productivity: Evidence from GitHub Copilot" (2023). https://arxiv.org/abs/2302.06590.
31. <a id="ref-31"></a> [31] Model Context Protocol specification repository. https://github.com/modelcontextprotocol/modelcontextprotocol.
32. <a id="ref-32"></a> [32] HILBERT / PutnamBench results. https://arxiv.org/abs/2509.22819.
33. <a id="ref-33"></a> [33] FDA AI/ML device database and adoption study. https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-aiml-enabled-medical-devices; https://pubmed.ncbi.nlm.nih.gov/41483727/.
34. <a id="ref-34"></a> [34] Verification infrastructure before LLMs (SQL, Haskell, Coq, Rust, TLA+). https://www.iso.org/standard/63555.html; https://www.haskell.org/; https://coq.inria.fr/; https://www.rust-lang.org/; https://lamport.azurewebsites.net/tla/tla.html.
35. <a id="ref-35"></a> [35] Rust vs C++ corpus scale (project histories and standards). https://www.rust-lang.org/; https://isocpp.org/std/the-standard.
36. <a id="ref-36"></a> [36] ROSS Intelligence v. Thomson Reuters Enterprise Centre GmbH (D. Del.), GovInfo docket. https://www.govinfo.gov/app/details/USCOURTS-ded-1_20-cv-00613.
37. <a id="ref-37"></a> [37] Mata v. Avianca, Inc. (S.D.N.Y.), GovInfo docket. https://www.govinfo.gov/app/details/USCOURTS-nysd-1_22-cv-01461.
38. <a id="ref-38"></a> [38] Stripe engineering blog. https://stripe.com/blog/engineering.
39. <a id="ref-39"></a> [39] Isabelle/HOL overview and documentation. https://isabelle.in.tum.de/.
40. <a id="ref-40"></a> [40] Z3 Theorem Prover. https://z3prover.github.io/.
41. <a id="ref-41"></a> [41] SMT-LIB standard and resources. https://smt-lib.org/.
