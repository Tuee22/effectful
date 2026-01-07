# The [Proof Boundary](#glossary-proof-boundary): Where verification and judgment meet

## Opening: The Trolley Problem as Boundary

Picture three rooms.

In the first, a lawyer skims a contract the model drafted to save a late night. They slow at the indemnity, termination, and governing-law clauses, knowing one loose sentence can turn into a costly dispute. [1](#ref-1)

In the second, a clinician reviews a common diabetic retinopathy scan the model flagged with high confidence. They still linger on a borderline lesion, because a single missed bleed can mean preventable blindness. [2](#ref-2)

In the third, a civil engineer scans an AI-flagged crack map from a bridge inspection, grateful for the triage. They double-check midspan fractures and bearing regions before signing off on load ratings. [3](#ref-3)

Now step into the developer's room. The model writes a function. Tests run. The build goes green. Code ships. Often no regulator signs the diff. The program either passes or it does not.

Why does one domain delegate while others supervise? In the first two rooms, the day ends with a signature. In the last, it ends with a test report.

The [trolley problem](https://en.wikipedia.org/wiki/Trolley_problem) poses a simple scene with two outcomes: pull the lever and save five but kill one, or do nothing and kill five. The situation is decidable in the mechanical sense: outcomes are enumerable and rules can be written down. Yet the argument does not converge. People disagree not just about outcomes, but about which rule should govern the lever.

A model can draft a contract clause or flag a scan, but a legal code still requires interpretation, discretion, enforcement, and context.

We can formalize the physics of the tracks. We can formalize liability, insurance, and compliance. Shared agreement on which rule should govern the outcome still splits the room.

Bridge engineers argue from inspection reports and load tables; the model shows a particular load stays below a tolerance. A signature follows the argument, not the model.

An audit can surface disparate outcomes. A denial list can also read like neutral process even when it maps onto a local moral view.

The medium is the message. MCP lowers integration friction, yet the signature still sits elsewhere.

## Language, Rules, and the First Fracture

This document is written in a formal format, yet no formal checker tells us when it is complete. [Markdown](#glossary-markdown) can be validated. Links can be clicked. Formats and tools decide what counts as legible, what can be checked, and what is ignored. The reasoning still waits for a human verdict. A checklist depends on a checker, a proof depends on a prover, and the chain of assurance ends in a person.

In some domains a rule can be rerun with the same result; in others a verdict depends on a person. A compiler rejects. A judge interprets. A mechanical check repeats; a human decision carries context.

Language fractures first. A statute uses "reasonable." Two courts read it differently. It is self-referential, defined by the community that uses it, borrowing authority from itself. Law and mathematics share this. Language can build smaller worlds with stricter rules and hope they are adequate for the larger one.

Formalization can make rules explicit, exposing bias and making accountability visible. The same checklist can hide power when choices are framed as technical necessity. "All models are wrong, some models are useful" is the statistical reminder that even our best formalisms are approximations with consequences.

Inside the engineering demarcation sits a cultural compromise: where we accept machine judges and where we keep human ones. An auto-merge can ship a formatting fix, but a dosage change waits for a signature. Hiring criteria, eligibility forms, and enforcement routines decide whose language is formalized and whose experience is filtered out.

## Russell, Godel, Turing: The Formal Dream Meets Its Limits

Bertrand Russell discovered [Russell's paradox](#glossary-russells-paradox) in [1901](#timeline-1901). Consider the set of all sets that do not contain themselves. Does that set contain itself? If it does, it should not. If it does not, it should. The system collapses. [14](#ref-14)

[Russell's paradox](#glossary-russells-paradox) shows what happens when a system tries to talk about itself without care. A few innocent-looking words upend the logic underneath them. [formal systems](#glossary-formal-system) place rules on themselves to avoid contradiction. It is the first formal sign that language does not escape its own self-reference.

Kurt Godel showed in [1931](#timeline-1931) that any sufficiently expressive [formal system](#glossary-formal-system) contains statements that are consistent with the system yet unprovable within it. That is [incompleteness](#glossary-incompleteness). [15](#ref-15) No formal system is both complete and consistent when it is rich enough to express arithmetic. There will always be claims it does not derive.

A proof assistant can check a proof; it cannot certify its own consistency without stepping outside itself. The best it can do is validate consistency within its own language.

Douglas Hofstadter argued in *Godel, Escher, Bach* in [1979](#timeline-1979-geb) that formal rules make the world smaller: every rule is a filter, and every filter excludes nuance. Formal systems gain power by shrinking the universe they can talk about. Predictability follows from the smaller universe. [29](#ref-29) Scope is the price.

Alan Turing showed in [1936](#timeline-1936) that there is no general algorithm that can decide whether an arbitrary program will halt. The [halting problem](#glossary-halting-problem) is the computational version of Russell and Godel. [16](#ref-16)

There is no general verifier. Even with a complete description of a program, the question "will it stop?" is open in the general case. We can decide termination for programs that belong to restricted classes. That restriction is the hidden cost of proof.

Formal verification works when systems accept its constraints. Teams rewrite specs, constrain inputs, and teach the tooling; those choices decide which constrained languages become normal.

The trolley problem is a moral thought experiment, but the same structure appears anywhere formal logic meets disputed premises: even a fully formal system does not justify its own starting points. The only authority language has is itself.

## Catastrophe as the Forcing Function

### Quebec Bridge

The Quebec Bridge was to be the longest cantilever bridge on Earth. It collapsed during construction in [1907](#timeline-1907), killing 75 workers. The official inquiries found a familiar pattern: not a lack of equations, but a failure of assumptions. [4](#ref-4)

Engineers underestimated the dead load; deformations were observed; warnings were sent; work continued. Calculation was necessary, but not sufficient. The collapse pushed licensing, codes, standards, and formal review into place. Some elements became mechanically checkable; others remained human.

Formal review made assumptions legible, but it did not erase the labor hierarchy that killed 75 workers or make the project broadly acceptable.

### Ariane 5

Thirty-seven seconds after liftoff in [1996](#timeline-1996), Ariane 5 failed. [5](#ref-5)

A 64-bit velocity value was converted to a 16-bit signed integer. The value overflowed, the exception handler crashed, and the backup failed because it ran identical code. The software had worked for Ariane 4; Ariane 5 flew a faster trajectory. The assumption "this value will never exceed that range" failed. A proof is not a property of code alone; it is a property of code within a specification. Redundancy without diversity is replication, not resilience.

Formalization made the failure undeniable. It did not resolve who should bear the cost when a public mission fails.

### Therac-25

The Therac-25 was a radiation therapy machine. To reduce cost and complexity, engineers removed hardware interlocks and relied on software alone in [1985-1987](#timeline-1985-1987). [6](#ref-6)

Under specific timing, a race condition bypassed safety checks and fired the electron beam at full power. Patients died. The bug was in every machine. A proof checker can enumerate those interleavings; a human does not. The safety case moved from physical interlocks to logical guarantees, and the burden shifted with it.

The interleavings became explicit and liability clearer, but the tragedy remained.

### Pentium FDIV

A math professor computed reciprocals of twin primes in [1994](#timeline-1994). The Pentium gave slightly wrong answers. Five missing entries in a lookup table were enough to force a $475 million replacement program. [7](#ref-7)

[Intel](#glossary-intel) ran millions of test vectors. A simple proof would have checked every entry in minutes. The property was finite and decidable, yet human review missed it. Proof would have been cheaper than reputation repair. When the public heard "rare," they still heard "wrong."

### [Toyota](#glossary-toyota) Unintended Acceleration

A Lexus surged to over 120 mph and crashed in [2009-2011](#timeline-2009-2011), triggering investigations. [NASA](#glossary-nasa)'s analysis found [MISRA C](#glossary-misra-c) violations in the electronic throttle control system. [8](#ref-8) Causality remained contested across investigations, which is part of why the episode is debated.

The system was complex. The code was large. The testing was extensive. Yet the failures happened.

### Pattern

Expert teams reviewed the systems. Extensive testing was performed. Catastrophic failure still occurred.

---

## The Software Evolution Toward Proof

### Assembly Era: Humans as Validators

Early programmers hand-checked every instruction in the [1940s-1950s](#timeline-1940s-1950s). One wrong register could crash the program. Debugging meant reading memory dumps by hand, often with punchcards and deck order as the only paper trail. Human validation was painfully slow and error-prone, because every change required manual inspection. A thousand lines was already a mountain; a hundred thousand was a continent. The desire for automation, for [compilers](#glossary-compiler), for tests, for [static analysis](#glossary-static-analysis) all emerged from the same insight: human attention is finite.

### [Compiler](#glossary-compiler) Revolution

[FORTRAN](#glossary-fortran) and [COBOL](#glossary-cobol) mechanized syntax in [1957-1959](#timeline-1957-1959). [9](#ref-9) Variables must be declared. Parentheses must match. Jumps must land on real labels. The [compiler](#glossary-compiler) was the first proof checker most programmers ever met: a judge that rejects without persuasion. It taught a generation to treat well-formedness and certain properties as something a machine could pronounce.

The compiler could never explain why a program should exist. It could only say whether it was well formed.

### Type Systems

[Type systems](#glossary-type-system) mechanized whole categories of reasoning in the [1970s](#timeline-1970s). A program either type-checks or it does not. Cheap errors moved from human review into [compiler](#glossary-compiler) rules. Some mistakes became unrepresentable.

### Functional Programming

Functional languages offered referential transparency and mathematical clarity in the [1980s-1990s](#timeline-1980s-1990s). They were proof-friendly but economically resisted: tooling, talent, and network effects favored imperative languages. People optimized for comprehension, hiring, and speed, not proof.

### Distributed Systems

The internet made every program a distributed system. The Byzantine Generals problem in [1982](#timeline-1982) turned the fear into a formal statement: if some nodes can lie or fail, agreement becomes fragile in ways humans do not naturally anticipate. [10](#ref-10)

The difficulty is that networks drop packets and that every message can arrive late, arrive twice, or arrive out of order. Each ordering is a different universe. A design that works in the lab can fail in production because the one ordering you never tested is the one the world chooses.

The complexity spirals beyond what any individual can hold in their head. Formal specification becomes less like academic rigor and more like survival.

### [Amazon](#glossary-amazon) and [TLA+](#glossary-tla)

[TLA+](#glossary-tla) (Temporal Logic of Actions) arrived in [1999](#timeline-1999) as Leslie Lamport's way of writing system behavior with mathematical precision. It is not code; it is a logic for describing what must always hold and what can never hold. A [model checker](#glossary-model-checker) then explores every possible interleaving to see if reality can violate the spec.

[Amazon](#glossary-amazon) adopted [TLA+](#glossary-tla) in [2011](#timeline-2011) and found deep design flaws in systems already in production. [Model checking](#glossary-model-checker) found bugs no test could. [11](#ref-11) The [model checker](#glossary-model-checker) is a strict reader: it does not care that the diagram looks plausible.

[AWS](#glossary-aws) S3 launched in [2006](#timeline-2006) and Dynamo was published in [2007](#timeline-2007-dynamo) because distributed storage is a practical version of the Byzantine fear: nodes disagree, networks lie, and data must still converge. [TLA+](#glossary-tla) helped teams rehearse those worst-case orderings, the hard versions of Byzantine failure that only show up at scale, and make the guarantees explicit before customers found the cracks.

### [CompCert](#glossary-compcert) and [seL4](#glossary-sel4)

[CompCert](#glossary-compcert) shows that a [C](#glossary-c) [compiler](#glossary-compiler) conforms to its spec, first released in [2006](#timeline-2006-compcert). [seL4](#glossary-sel4) shows a microkernel's compliance with its spec, with the proof mechanized in [Isabelle/HOL](#glossary-isabelle-hol) in [2009](#timeline-2009-sel4). [12](#ref-12) [39](#ref-39)

### Bezos' [API](#glossary-api) Mandate

At [Amazon](#glossary-amazon), Bezos required every team to expose functionality through [APIs](#glossary-api) in [2002](#timeline-2002). The mandate was strict: no shortcuts, no backdoors, no informal dependencies. If you wanted data from another team, you had to call them like a customer. [13](#ref-13)

The mandate pushed the company to behave like a network of services long before "microservices" was a slogan. Infrastructure became software. Software became product. The world learned to rely on [APIs](#glossary-api) because they were deterministic and testable. An API is a treaty: a promise that can be invoked, checked, and enforced.

## The AI Capability Surge

Web teams ship with tests and linters; formal proofs are rare. Generative content in marketing took off with minimal verification.

### The [GPU](#glossary-gpu) Pivot and the Medium as the Message

[NVIDIA](#glossary-nvidia) was founded in [1993](#timeline-1993) to build high-end [GPUs](#glossary-gpu) for PC gamers. [17](#ref-17) [CUDA](#glossary-cuda) in [2006](#timeline-2006) turned graphics cards into programmable devices, and consumer hardware became a scientific instrument. [18](#ref-18)

When AlexNet showed the deep learning advantage in [2012](#timeline-2012-alexnet) and the [transformer](#glossary-transformer) era arrived in [2017](#timeline-2017-transformer), it rode on the back of that pivot. The medium shaped the message. [20](#ref-20)

That same medium could now ingest a different kind of dataset: the formal artifacts built for decades. Proof assistants, model checkers, and formal specifications finally had a machine-native substrate that could learn from them at scale.

### [Benchmarks](#glossary-benchmark) as Mechanical Judges

[HumanEval](#glossary-humaneval) in [2021](#timeline-2021-humaneval), [AlphaCode](#glossary-alphacode) in [2022](#timeline-2022-alphacode), and [DIN-SQL](#glossary-din-sql) in [2023](#timeline-2023-din-sql) share a key property: outputs are mechanically checkable. [19](#ref-19) A model can generate a hundred candidates and let tests or execution reject the wrong ones.

In human domains, iteration is expensive. A lawyer does not file a thousand briefs and ask a judge to grade them. A doctor does not attempt a thousand diagnoses on one patient.

### Formal Theorem Proving [benchmarks](#glossary-benchmark)

Results like [HILBERT](#glossary-hilbert) on [PutnamBench](#glossary-putnambench) in [2024](#timeline-2024-hilbert) show the jump when proofs are checked by a [formal system](#glossary-formal-system). [32](#ref-32)

### [MCP](#glossary-mcp) and the Connection Layer

The Model Context Protocol ([MCP](#glossary-mcp)) standardizes how models call tools in [2024](#timeline-2024-mcp). It lowers integration friction and makes verification loops easier to wire into production systems. [31](#ref-31)

We already have [APIs](#glossary-api) for almost anything a company can do. MCP makes it possible for any [LLM](#glossary-llm) to issue those instructions through a standard interface. The model can automate anything the API can reach, even when the verification loop is still social, not mechanical.

### [AlphaGo](#glossary-alphago), [AlphaZero](#glossary-alphazero), and the External Judge

[AlphaGo](#glossary-alphago) surpassed human champions in Go in [2016](#timeline-2016-alphago) by learning in a formal environment. A [legal-moves checker](#glossary-legal-moves-checker) tells the system what is allowed. [21](#ref-21)

[AlphaZero](#glossary-alphazero) learned from self-play in [2017](#timeline-2017-alphazero). It needed an external verifier that could tell it which moves were legal and who won. The [self-play](#glossary-self-play) loop is only possible because the environment is formal. [22](#ref-22)

[reinforcement learning](#glossary-rl) relies on an external judge. Without a formal environment, RL does not scale beyond imitation.

### [AlphaProof](#glossary-alphaproof) and Formal Math

[AlphaProof](#glossary-alphaproof) reached the silver level on IMO problems in [2024](#timeline-2024-alphaproof) with [Lean](#glossary-lean) verifying the proofs. The model proposes, the verifier judges, and the system iterates until it wins. [23](#ref-23)

Formal mathematics is a convenient laboratory: Lean accepts the proof or it does not.

### Medical Imaging: The Assistant Boundary

Models can detect patterns and match specialists on specific tasks, but the outputs are not formally verifiable. Two clinicians can disagree on a borderline scan. Retinopathy results in [2016](#timeline-2016-retinopathy) and dermatology results in [2017](#timeline-2017-dermatology) show the boundary. [2](#ref-2) [24](#ref-24)

These systems are used as assistants; a physician signs off. The signature is legal cover and a place where accountability and lived consequences concentrate. When the case is ambiguous, the model does not absorb the contested meaning of the decision. Partial automation exists, but the final decision remains human because the rule is not only accuracy but acceptable risk distribution.

### Legal Drafting and the Hallucination Trap

In law, verification is not mechanical. A brief can be grammatically well-formed and logically plausible yet still be unsupported. When a model hallucinates a citation, the error is not caught by syntax. It is caught by a human who knows the domain.

Hallucinations are a structural risk in [LLMs](#glossary-llm). The model is trained to predict plausible continuations, not to guarantee grounding. If the prompt looks like it should have a case, the model can invent one that matches the pattern. Without external grounding, the system confuses fluency for evidence.

The model has no built-in notion of "I don't know." It can be instructed to abstain, but the training signal rewards confident completion. Retrieval systems help reduce hallucinations, yet they introduce their own failure modes: missing sources, mismatched citations, or partial context. The output looks more authoritative the more unsupported it becomes.

The Stanford HAI / RegLab analysis in [2024](#timeline-2024-hai-reglab) documents high hallucination rates. A judge still checks citations, arguments, and precedent by hand. [1](#ref-1)

A fake citation in a brief can trigger sanctions against the lawyer, not the model. Institutions do not delegate without accountability, so adoption remains cautious until verification frameworks and liability regimes mature.

Then the paradox arrives.

## The Paradox and the Boundary

In software, tests and type checks make verification cheap, so teams ship quickly. In law, every draft still needs a licensed signer, so deployment stays cautious.

### Accountability Asymmetry

A radiologist signs a report. A lawyer files a brief. An engineer stamps a design. A developer merges the code. The model signs nothing. There is no license to revoke, no liability to assign, no professional reputation to protect. The signature binds a person to a claim in a way no model can accept.

In software, errors can be patched. In law or medicine, errors become records that follow people.

### [Decidability](#glossary-decidability) and the Cost of Predictability

When a property is decidable, it can be mechanically verified. When it is not, verification becomes a human judgment. Many properties are decidable in principle but too expensive to check at scale. The more general the system, the less we can establish about it. The more we want proof, the more we must restrict the system. Safety-critical code lives in smaller languages for a reason.

High-assurance domains adopt restricted subsets and strict coding standards. [MISRA C](#glossary-misra-c) bans features before they ever reach a checker.

---

## The Moral Frontier: Formalization and Legitimacy

Statutes, procedures, and enforcement regimes formalize values. Proof systems stop earlier: they do not resolve contested claims without human discretion.

## Verification Infrastructure and Self-Improvement

[Reinforcement learning](#glossary-rl) is often described as a model learning through trial and error. Without an environment that can tell it what counts as a valid trial, there is no learning loop.

In Go, the rules define what is legal. The environment enforces those rules. Without that checker, [AlphaZero](#glossary-alphazero) in [2017](#timeline-2017-alphazero) would be lost. It would not learn; it would hallucinate.

In [AlphaGo](#glossary-alphago)'s story in [2016](#timeline-2016-alphago) and [AlphaZero](#glossary-alphazero)'s in [2017](#timeline-2017-alphazero), the model relies on the judge. The external environment makes self-play possible, and it makes errors visible. The same structure appears in [proof assistants](#glossary-proof-assistant), where a model can propose steps but the checker accepts or rejects them, without negotiation. [21](#ref-21) [22](#ref-22)

Pure language models fall short in games. They can describe Go, but they do not play it at [AlphaZero](#glossary-alphazero) levels because they do not have a [legal-moves checker](#glossary-legal-moves-checker) embedded in their training loop. Stories can teach style; they do not enforce legality.

Verification infrastructure predated modern [LLMs](#glossary-llm) by decades. [SQL](#glossary-sql) standards in [1986](#timeline-1986-sql), [proof assistants](#glossary-proof-assistant) like [Coq](#glossary-coq) in [1989](#timeline-1989-coq), functional languages like [Haskell](#glossary-haskell) in [1990](#timeline-1990-haskell), [TLA+](#glossary-tla) in [1999](#timeline-1999), and [SMT solvers](#glossary-smt-solver) like [Z3](#glossary-z3) in [2007](#timeline-2007) all existed long before transformers. [34](#ref-34) [40](#ref-40) [41](#ref-41)

## Civic Struggle and the Limits of Legal Legitimacy

### U.S. Civil Rights Movement

The civil rights struggle made the machinery of legitimacy visible. Martin Luther King Jr. argued from a jail cell that legality is not the same as moral legitimacy, and that obedience to laws that degrade people fails the movement’s moral frame. [42](#ref-42) The U.S. Supreme Court’s decision in *Brown v. Board of Education* formally rejected “separate but equal,” but the decision did not end segregationist resistance or erase entrenched power. [43](#ref-43) The Civil Rights Act of 1964 and the Voting Rights Act of 1965 codified equality and political inclusion into law. [44](#ref-44) [45](#ref-45) Those changes were necessary, but they did not end disenfranchisement or the backlash that followed. [55](#ref-55) [56](#ref-56)

### Women’s Suffrage

The Seneca Falls Declaration of Sentiments declared the exclusion of women from political life as a moral harm, long before any formal change arrived. [46](#ref-46) The Nineteenth Amendment then formalized political inclusion. [47](#ref-47) The transition did not enfranchise all women or end voter suppression; the debate continued in courts and legislatures.

### Anti-Apartheid Movement

Nelson Mandela’s “Statement from the Dock” made the moral case against a legal regime that had already formalized racial domination. [48](#ref-48) The Freedom Charter articulated a competing moral order rooted in equality and shared citizenship, rejecting the legitimacy of apartheid law. [49](#ref-49) The legal system’s precision was not its redemption; it was the method by which oppression was enforced. The movement brought that architecture into the open, but it did not confer moral legitimacy on the regime.

### Independence and Decolonization

The Indian Independence Act of 1947 is a formal document that ended British rule in law. [50](#ref-50) That legal shift did not resolve state violence, nor the mass displacement and intercommunal violence around partition shaped by imperial policy and boundary-making, nor the long afterlives of imperial administration and coercive institutions. [57](#ref-57) [58](#ref-58) Imperial legitimacy had been codified long before; the transition was a change in legal structure, not an automatic moral reconciliation. The UN declaration on granting independence to countries and peoples codified international recognition of a growing, uneven opposition to imperial rule led by independence movements. [51](#ref-51) These formal shifts mattered, but they did not retroactively cleanse the violence of imperial systems or the ongoing harms that outlasted independence in land, language, and political power. They exposed what was already being contested in streets, courts, and daily survival.

### Indigenous Rights

The UN Declaration on the Rights of Indigenous Peoples formalizes recognition of rights that long predated the document. [52](#ref-52) Recognition did not resolve power imbalances on the ground, including land dispossession, sovereignty constraints, and resource extraction. [59](#ref-59)

### Disability Rights

The Americans with Disabilities Act formalized access and anti-discrimination in law. [53](#ref-53) The law made exclusions explicit and enforceable, but it also revealed how institutions define “reasonable accommodation.”

### LGBTQ+ Rights

Obergefell v. Hodges formalized marriage equality in the United States, turning a moral debate into enforceable legal recognition. [54](#ref-54) This was a formal recognition of inclusion claims, but it did not end discrimination, criminalization in other jurisdictions, or the ongoing harms faced by trans and gender-nonconforming people.

## Conclusion: The Never-Ending Human Narrative

Marshall McLuhan wrote in [1994](#timeline-1994-mcluhan), "The medium is the message." The telegraph compressed time. The telephone collapsed distance. Television changed how politics felt. AI does the same. It compresses knowledge work, changes who gets to decide, and alters the pace of institutional response. [25](#ref-25)

Arthur Charles Clarke wrote in [2000](#timeline-2000-clarke), "Any sufficiently advanced technology is indistinguishable from magic." [26](#ref-26)

Social media amplified connection and loneliness, knowledge and misinformation. Australia's under-16 social media law in [2024](#timeline-2024-australia-law) is a reminder that society often moves to regulate what it does not absorb. [27](#ref-27)

Proofs need provers. Statutes need signers. Models need judges. A theorem gets a name on it; a policy gets a seal; a model output gets a signature. If the ideas here resonate, read Yuval Noah Harari's *Sapiens* and Douglas Hofstadter's *Godel, Escher, Bach* for two very different lenses on the same tension. [28](#ref-28) [29](#ref-29)

---

## Appendices

### Appendix A: Chronological Thread of Proof and Power

Timeline (single sequence):
- <a id="timeline-1901"></a>1901: [Russell's paradox](#glossary-russells-paradox) exposes contradictions in naive set theory.
- <a id="timeline-1907"></a>1907: Quebec Bridge collapse.
- <a id="timeline-1931"></a>1931: Godel demonstrates [incompleteness](#glossary-incompleteness) constraints in [formal systems](#glossary-formal-system).
- <a id="timeline-1936"></a>1936: Turing demonstrates the [halting problem](#glossary-halting-problem) is undecidable.
- <a id="timeline-1940s-1950s"></a>1940s-1950s: Assembly era manual validation.
- <a id="timeline-1957-1959"></a>1957-1959: [Compiler](#glossary-compiler) revolution ([FORTRAN](#glossary-fortran), [COBOL](#glossary-cobol)).
- <a id="timeline-1970s"></a>1970s: [type systems](#glossary-type-system) take hold ([Pascal](#glossary-pascal), [C](#glossary-c), [ML](#glossary-ml)).
- <a id="timeline-1979-geb"></a>1979: Hofstadter publishes *Godel, Escher, Bach*.
- <a id="timeline-1982"></a>1982: Byzantine Generals problem formalizes distributed agreement constraints.
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
- <a id="timeline-1996"></a>1996: Ariane 5 failure at 37 seconds.
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
- <a id="timeline-2012-alexnet"></a>2012: AlexNet shows [GPU](#glossary-gpu) advantage for deep learning.
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



### Appendix B: Glossary

- <a id="glossary-proof-boundary"></a>**Proof boundary**: The line between what can be verified mechanically and what must be judged by humans, including decidable cases where rule agreement is missing.
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
- <a id="glossary-compcert"></a>**CompCert**: A formally verified C compiler with machine-checked compliance to its spec in Coq.
- <a id="glossary-sel4"></a>**seL4**: A formally verified microkernel with machine-checked compliance to its spec.
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
- <a id="glossary-incompleteness"></a>**Incompleteness**: The condition that some claims are not derivable within a system.
- <a id="glossary-russells-paradox"></a>**Russell's paradox**: A self-reference paradox in naive set theory.
- <a id="glossary-oracle-problem"></a>**oracle problem**: The difficulty of defining reference labels for evaluation in messy domains.
- <a id="glossary-compositional-verification"></a>**Compositional verification**: Proof by composing verified components.
- <a id="glossary-conformance-test"></a>**conformance test**: A test that checks behavior against a specification.
- <a id="glossary-benchmark"></a>**Benchmark**: A standardized task for evaluation with defined scoring.
- <a id="glossary-api"></a>**API (Application Programming Interface)**: A formal interface that defines how software components interact.
- <a id="glossary-fortran"></a>**FORTRAN**: One of the earliest high-level programming languages, designed for scientific computing.
- <a id="glossary-cobol"></a>**COBOL**: A business-oriented programming language designed for data processing.
- <a id="glossary-pascal"></a>**Pascal**: A language designed to encourage structured programming.
- <a id="glossary-c"></a>**C**: A low-level systems programming language with manual memory control.
- <a id="glossary-ml"></a>**ML**: A family of functional languages with strong static typing.
- <a id="glossary-markdown"></a>**Markdown**: A lightweight markup language for structured text and links. The language in which this document is written.
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
42. <a id="ref-42"></a> [42] King, "Letter from Birmingham Jail" (1963), Stanford King Institute. https://kinginstitute.stanford.edu/king-papers/documents/letter-birmingham-jail.
43. <a id="ref-43"></a> [43] Brown v. Board of Education (1954), U.S. National Archives. https://www.archives.gov/milestone-documents/brown-v-board-of-education.
44. <a id="ref-44"></a> [44] Civil Rights Act of 1964, U.S. National Archives. https://www.archives.gov/milestone-documents/civil-rights-act.
45. <a id="ref-45"></a> [45] Voting Rights Act of 1965, U.S. National Archives. https://www.archives.gov/milestone-documents/voting-rights-act.
46. <a id="ref-46"></a> [46] Declaration of Sentiments (1848), Library of Congress. https://www.loc.gov/resource/rbpe.18500500/.
47. <a id="ref-47"></a> [47] 19th Amendment (1920), U.S. National Archives. https://www.archives.gov/milestone-documents/19th-amendment.
48. <a id="ref-48"></a> [48] Mandela, "Statement from the Dock" (1964), Nelson Mandela Foundation. https://www.nelsonmandela.org/content/page/statement-from-the-dock.
49. <a id="ref-49"></a> [49] Freedom Charter (1955), African National Congress. https://www.anc1912.org.za/freedom-charter/.
50. <a id="ref-50"></a> [50] Indian Independence Act 1947 (UK Parliament). https://www.legislation.gov.uk/ukpga/Geo6/10-11/30/contents/enacted.
51. <a id="ref-51"></a> [51] UN General Assembly Resolution 1514 (1960), United Nations. https://www.un.org/en/decolonization/declaration.shtml.
52. <a id="ref-52"></a> [52] UN Declaration on the Rights of Indigenous Peoples (2007), United Nations. https://www.un.org/development/desa/indigenouspeoples/declaration-on-the-rights-of-indigenous-peoples.html.
53. <a id="ref-53"></a> [53] Americans with Disabilities Act (1990), U.S. National Archives. https://www.archives.gov/milestone-documents/americans-with-disabilities-act.
54. <a id="ref-54"></a> [54] Obergefell v. Hodges (2015), U.S. Supreme Court. https://www.supremecourt.gov/opinions/14pdf/14-556_3204.pdf.
55. <a id="ref-55"></a> [55] Numan V. Bartley, *The Rise of Massive Resistance: Race and Politics in the South During the 1950s* (Louisiana State University Press, 1969).
56. <a id="ref-56"></a> [56] U.S. Commission on Civil Rights, *The Voting Rights Act: Unfulfilled Goals* (2006). https://www.usccr.gov/pubs/081506_vra_report.pdf.
57. <a id="ref-57"></a> [57] Ian Talbot and Gurharpal Singh, *The Partition of India* (Cambridge University Press, 2009).
58. <a id="ref-58"></a> [58] Yasmin Khan, *The Great Partition: The Making of India and Pakistan* (Yale University Press, 2007). https://yalebooks.yale.edu/book/9780300186356/the-great-partition/.
59. <a id="ref-59"></a> [59] United Nations, *State of the World's Indigenous Peoples* (2009). https://www.un.org/development/desa/indigenouspeoples/publications/2009/09/state-of-the-worlds-indigenous-peoples.html.
