# The [Proof Boundary](#glossary-proof-boundary): Where verification and judgment meet

## Opening: The Trolley Problem as Boundary

Picture three rooms.

In the first, a lawyer scans a late-night contract draft. They pause on indemnity, termination, and governing-law clauses, a line that could decide a future lawsuit. [1](#ref-1)

In the second, a clinician reviews a diabetic retinopathy scan the model flagged with high confidence. A faint bleed near the macula makes the call borderline, with real consequences. [2](#ref-2)

In the third, a civil engineer scrolls through an AI-generated crack map from a bridge inspection. They pause at midspan and bearing regions to decide which fractures count as critical before stamping a load rating. [3](#ref-3)

In contrast, consider a software developer. It is 3am and they are sound asleep. A user reports a bug. An [LLM](#glossary-llm) suggests a code patch to fix it. Tests run. The build goes green. Code ships. The bug is fixed. It is now 3:15am and the developer, still asleep, has successfully put out a production fire. How? They made a choice months ago: a formal validation checker that approves patches for them. The fix was automated. The responsibility is still theirs.

The same pattern appears in the [trolley problem](#glossary-trolley-problem). Outcomes are enumerable. The lever state is well-defined. The argument still splits the room. The tracks can be modelled, but the moral answer cannot be made unanimous. The lever moves, but the argument stays: what rule should govern the switch? More importantly, who gets to write it?

AI makes automation easier to wire, but automation does not solve human responsibility. It does not provide moral clarity. The [proof boundary](#glossary-proof-boundary) holds: where a checker can speak conclusively, machines may act alone. When rules are undecidable, a human must still sign.

## Language, Rules, and the Boundary

This document is written in a [formal language](#glossary-formal-language), [Markdown](#glossary-markdown). (You can see the unrendered code on github.com by clicking the raw button.) Yet despite this formality no formal checker tells us when the document is complete. [Markdown](#glossary-markdown) is a [formal language](#glossary-formal-language) because it must be syntactically valid to render in a browser. Links must work when clicked. But is this document finished? This reasoning still rests on a human verdict. A checklist still depends on a checker. A proof depends on a prover. This document cannot be proven to be finished because its human author does not know how to write a proof to validate it. The final judgment still rests with a person. The subject matter—the role of formal proofs in AI adoption—does not alter the simple fact that no formal validator exists for an essay. Even one about formal validation.

The workflow shifts toward machines only where the checker is trusted. And cheap. Where it is absent or disputed, or just too expensive, the workflow stays human.

In some domains, a rule can be reapplied and the same result is guaranteed. In others a verdict depends on a person. A [compiler](#glossary-compiler) rejects. A judge interprets. A mechanical check repeats itself. A human decision does not, and cannot: it carries subjective context.

A legal statute uses "reasonable." Two reasonable courts read it differently. Law is self-referential, defined solely by the humans that wrote it, borrowing authority from itself. Law and mathematics both share this. Language can build smaller worlds with stricter rules, but what is the benefit? Ask the one writing the rules.

Formalization can make rules explicit, exposing bias and making accountability visible. The same structure can hide power when choices are framed as technical necessity. Statisticians have a pithy saying: "All models are wrong, some models are useful."

But useful to whom?

## Russell, Gödel, Turing: Western rationalism folds in on itself

Bertrand Russell discovered [Russell's paradox](#glossary-russells-paradox) in [1901](#timeline-1901). Consider the set of all sets that do not contain themselves. Does that set contain itself? If it does, it should not. If it does not, it should. [4](#ref-4)

[Russell's paradox](#glossary-russells-paradox) shows what happens when a system tries to talk about itself without care. A few words upend the logic underneath them. [Formal systems](#glossary-formal-system) place rules on themselves to avoid contradiction. This is the first formal proof that language cannot escape its own self-reference.

Kurt Gödel showed in [1931](#timeline-1931) that any sufficiently expressive [formal system](#glossary-formal-system) contains statements that are consistent with the system yet unprovable within it. That is [incompleteness](#glossary-incompleteness). [5](#ref-5) No [formal system](#glossary-formal-system) is both complete and consistent when it is rich enough to express arithmetic. There will always be true theorems it does not derive.

A [proof assistant](#glossary-proof-assistant) can check a proof; it cannot certify its own consistency without stepping outside itself. The best it can do is validate consistency within its own language.

Douglas Hofstadter argued in *Gödel, Escher, Bach* in [1979](#timeline-1979-geb) that formal rules make the world smaller: every rule is a filter, and every filter excludes nuance. [Formal systems](#glossary-formal-system) gain power by shrinking the universe they can talk about. Predictability follows from the smaller universe. [6](#ref-6) Scope is the price.

Alan Turing showed in [1936](#timeline-1936) that there is no general algorithm that can decide whether an arbitrary program will halt. The [halting problem](#glossary-halting-problem) is the computational version of Russell and Gödel. [7](#ref-7)

There is no general verifier. Even with a complete description of a program, the question "will it stop?" is open in the general case. We can decide termination for programs only when they belong to restricted classes of programs. That restriction is the hidden cost of proof.

[Formal verification](#glossary-formal-verification) works when systems accept its constraints. Teams rewrite specs, constrain inputs, and teach the tooling; those choices decide which constrained languages become normal.

The [trolley problem](#glossary-trolley-problem) is a moral thought experiment, but the same structure appears anywhere formal logic meets disputed premises: even a fully [formal system](#glossary-formal-system) does not justify its own starting points. The only authority language has is itself.

## Catastrophe as the Forcing Function

### Quebec Bridge ([1907](#timeline-1907))

The Quebec Bridge was to be the longest cantilever bridge on Earth. It collapsed during construction, killing 75 workers. The official inquiries emphasised failures of assumptions and oversight, not just calculation. [8](#ref-8)

As the design evolved, dead load grew faster than estimates, deflections were observed, and warnings were sent. Work continued. The collapse changed licensing, codes, standards, and formal review. Some engineering rules became formal. Others remained human judgement.

### Therac-25 ([1985](#timeline-1985-therac)-1987)

The Therac-25 was a radiation therapy machine. To reduce cost and complexity, engineers removed hardware interlocks and relied on software alone. [9](#ref-9)

Under specific timing, a [race condition](#glossary-race-condition) bypassed safety checks and fired the electron beam at full power. The bug appeared across deployed machines. In one documented case, a patient received 15,000 to 20,000 rad (150 to 200 Gy), hundreds of times the intended dose. [10](#ref-10) A proof checker can exhaustively inspect all software interleavings to guarantee no [race conditions](#glossary-race-condition). A human verifer, even a technical expert, cannot. The safety case moved from physical interlocks to logical guarantees, and the burden shifted with it. Formal proof should have replaced the removed mechanical guarantees. Because it did not patients died.

In the aftermath industry changed. The interleavings became explicit and liability clearer. The tragedy remained.

### Pentium FDIV ([1994](#timeline-1994))

Lynchburg College professor Thomas R. Nicely computed reciprocals of twin primes. The Pentium gave slightly wrong answers. Five missing entries in a lookup table were enough to force a costly replacement program, reported at about $475 million. [11](#ref-11) The error was deterministic, not random; it could be reproduced by the right operands. [11](#ref-11)

Before shipping the chip [Intel](#glossary-intel) had run millions of test vectors. The test suite did not capture the conditions needed to reproduce the bug. A simple proof would have checked every entry in minutes. The property was finite and decidable. Yet extensive expert human review missed it. Proof would have been cheaper than reputation repair. When the public heard "rare," they still heard "wrong."

### Ariane 5 ([1996](#timeline-1996))

Shortly after liftoff Ariane 5 exploded. [12](#ref-12) It was the maiden flight of the [ESA](#glossary-esa) launcher. A decade in the making, €7 billion spent, four uninsured scientific satellites. 37 seconds after liftoff it was all gone. [13](#ref-13)

A 64-bit velocity value was implicitly converted to a 16-bit signed integer. The value overflowed, one inertial reference system shut down. The backup, running identical code, did its job perfectly: it reproduced the casting error. The engine nozzle angle changed and 3 million pounds of thrust tore the accelerating rocket to shreds. The software had worked for Ariane 4 without overflow; but Ariane 5 flew a faster trajectory. The assumption "this value will never exceed that range" failed. A proof is not a property of code alone; it is a property of code within a specification. Redundancy without diversity is replication, not resilience.

Formalization made the failure undeniable. It did not resolve who should bear the cost when a public mission fails.

### [Toyota](#glossary-toyota) Unintended Acceleration

A Lexus surged to over 120 mph and crashed in [2009](#timeline-2009-toyota)-2011, triggering investigations. The 2009 San Diego crash involved off-duty California Highway Patrol officer Mark Saylor, his wife, daughter, and his brother-in-law, Chris Lastrella, with a recorded 911 call describing a stuck accelerator and failing brakes. [14](#ref-14) In the recording, Lastrella says, "We're in a Lexus... our accelerator is stuck... there's no brakes... hold on... hold on and pray... pray." [14](#ref-14) [NASA](#glossary-nasa)'s analysis found [MISRA C](#glossary-misra-c) violations in the electronic throttle control system. [15](#ref-15)

[Toyota](#glossary-toyota)'s electronic throttle system was complex. The code was large. The testing was extensive. Experts pored over every line. No formal proofs were performed. People died. [Toyota](#glossary-toyota)'s reputation was shattered.

### Pattern

Expert teams reviewed the systems. Extensive testing was performed. Catastrophic failure still occurred. The lesson: no amount of manual verification by human experts can provide the safety guarantees of mechanical proofs. Industries learned the hard way that [formal verification](#glossary-formal-verification) is worth the effort.

---

## The Software Evolution Toward Proof

### Assembly Era: Humans as Validators

In [1940](#timeline-1940-assembly) and through the 1950s, early programmers did not have compilers. They had to manually check every instruction—every punch card—by hand. One wrong register could crash the program. Debugging meant reading memory dumps by hand, often with deck order as the only paper trail. Human validation was painfully slow and error-prone, because every change required manual inspection. A thousand lines was challenging; a hundred thousand was impossible. The desire for automation, for [compilers](#glossary-compiler), for tests, for [static analysis](#glossary-static-analysis) all emerged from the same insight: human attention is a finite resource.

### [Compiler](#glossary-compiler) Revolution

[FORTRAN](#glossary-fortran) and [COBOL](#glossary-cobol) mechanized syntax in [1957](#timeline-1957-compilers). [16](#ref-16) Variables must be declared. Parentheses must match. Jumps must land on real labels. The [compiler](#glossary-compiler) was the first proof checker most programmers ever met: a judge that rejects without subjectivity. It taught a generation that a [formal language](#glossary-formal-language) could be proof checked without a human reviewer.

The [compiler](#glossary-compiler) could only say whether the code was well formed. That it obeyed the language's grammar. It could not guarantee much else.

### [Type Systems](#glossary-type-system)

[Type systems](#glossary-type-system) mechanized whole categories of reasoning in the [1970s](#timeline-1970s). A program either type-checks or it does not. More errors moved from human review into [compiler](#glossary-compiler) rules. Some mistakes became unrepresentable.
Types drew a tighter boundary around what counts as a valid program, turning many design questions into compile-time rejection instead of runtime surprise. The checker became stricter, but also narrower: anything outside the type language still required human judgment.

### [Functional programming](#glossary-functional-programming)

[Functional languages](#glossary-functional-languages) offered referential transparency and mathematical clarity beginning in [1980](#timeline-1980-fp) and through the 1990s. They were proof-friendly. But economics resisted: tooling, talent, and network effects favored [imperative languages](#glossary-imperative-languages). Businesses optimized for comprehension, hiring, and speed, not proof. Software stayed buggy.

### [Distributed systems](#glossary-distributed-systems)

The internet made every program a [distributed system](#glossary-distributed-systems). The [Byzantine Generals problem](#glossary-byzantine-generals) in [1982](#timeline-1982) turned the fear into a formal statement: if some nodes can lie or fail, agreement becomes fragile in ways humans do not naturally anticipate. [17](#ref-17)

The difficulty is every message can arrive late, arrive twice, out of order, or never. Each ordering is a different universe. A design that works in the lab can fail in production because the ordering you tested is not the one the world chooses.

The complexity of distributed consensus algorithms spirals beyond what any individual or team can hold in their head.

### [Amazon](#glossary-amazon) and [TLA+](#glossary-tla)

[TLA+](#glossary-tla) (Temporal Logic of Actions) arrived in [1999](#timeline-1999) as Leslie Lamport's way of writing system behaviour with mathematical precision. It is not code; it is a logic for describing what must always hold and what can never hold. A [model checker](#glossary-model-checker) then explores every possible interleaving to see if reality can violate the spec.

[Amazon](#glossary-amazon) adopted [TLA+](#glossary-tla) in [2011](#timeline-2011) and reported design flaws in systems, including ones already in production. [Model checking](#glossary-model-checker) surfaced bugs missed by testing. [18](#ref-18) The [model checker](#glossary-model-checker) is a strict reader: it does not care that the system diagram looks plausible. Diagrams are not proofs.

[AWS](#glossary-aws) S3 launched in [2006](#timeline-2006) and Dynamo was published in [2007](#timeline-2007-dynamo) because distributed storage is a practical version of the [Byzantine Generals problem](#glossary-byzantine-generals): nodes disagree, networks lose packets, and data must still converge. [TLA+](#glossary-tla) helped teams rehearse those worst-case orderings, the trickiest versions of Byzantine failure that only show up at scale, and make the guarantees explicit before customers found the cracks.

### [CompCert](#glossary-compcert) and [seL4](#glossary-sel4)

[CompCert](#glossary-compcert) shows that a [C](#glossary-c) [compiler](#glossary-compiler) conforms to its specification. [2006](#timeline-2006-compcert) The proof moves a critical part of the toolchain from “trusted by reputation” to “trusted by check.” Reviewers stop debating whether the compiler preserves meaning and start debating the specification itself. [SeL4](#glossary-sel4) shows a microkernel's compliance with its design, with the proof mechanized in [Isabelle/HOL](#glossary-isabelle-hol). [2009](#timeline-2009-sel4) [19](#ref-19) [20](#ref-20)

### Bezos' [API](#glossary-api) Mandate

At [Amazon](#glossary-amazon), Stone reports that Bezos required teams to expose functionality through [APIs](#glossary-api) in [2002](#timeline-2002). The mandate was strict: no shortcuts, no backdoors, no informal dependencies. If you wanted data from another team, you had to call them like a customer. [21](#ref-21)

The mandate pushed the company to behave like a network of services long before "microservices" was a slogan. Infrastructure became software. Software became product. The world learned to rely on [APIs](#glossary-api) because they were deterministic and testable. An [API](#glossary-api) is a treaty: a promise that can be invoked, checked, and enforced.

## Verification Infrastructure Before Language Models

Verification infrastructure predated modern [LLMs](#glossary-llm) by decades. [SQL](#glossary-sql) standards in [1986](#timeline-1986-sql), [proof assistants](#glossary-proof-assistant) like [Coq](#glossary-coq) in [1989](#timeline-1989-coq), [functional languages](#glossary-functional-languages) like [Haskell](#glossary-haskell) in [1990](#timeline-1990-haskell), [TLA+](#glossary-tla) in [1999](#timeline-1999), and [SMT solvers](#glossary-smt-solver) like [Z3](#glossary-z3) in [2007](#timeline-2007) all existed long before [transformers](#glossary-transformer). [22](#ref-22) [23](#ref-23) [24](#ref-24)

## The AI Capability Surge

### The [GPU](#glossary-gpu) Pivot: the [Medium is the Message](#glossary-medium-is-the-message)

[NVIDIA](#glossary-nvidia) was founded by Jensen Huang and cofounders in [1993](#timeline-1993) to build high-end [GPUs](#glossary-gpu) for PC gamers. [25](#ref-25) Geoffrey Hinton's work on [deep learning](#glossary-deep-learning) laid the groundwork for the modern wave. [26](#ref-26) In [2006](#timeline-2006) [CUDA](#glossary-cuda) was released to turn [NVIDIA](#glossary-nvidia) graphics cards into general programmable devices for general non-graphical compute. [GPUs](#glossary-gpu) could perform arithmetic and linear algebra orders of magnitude faster than [CPUs](#glossary-cpu) could. Accidentally, affordable consumer hardware became a cutting edge scientific instrument. [27](#ref-27)

When AlexNet showed the [deep learning](#glossary-deep-learning) advantage in [2012](#timeline-2012-alexnet) and the [transformer](#glossary-transformer) era arrived with *Attention Is All You Need* in [2017](#timeline-2017-transformer), it rode on the back of the pivot. There would be no [LLMs](#glossary-llm) without [GPUs](#glossary-gpu). The medium shaped the message. [28](#ref-28)

[LLMs](#glossary-llm) could now ingest a different kind of dataset: massive sets of formally proven artifacts, accumulated over decades. [Proof assistants](#glossary-proof-assistant), [model checkers](#glossary-model-checker), and formal specifications finally had a machine-native substrate that could learn from them at any scale.

### [Reinforcement learning](#glossary-rl) and External Judges

[Reinforcement learning](#glossary-rl), in Sutton and Barto's framing, depends on an objective signal from outside the agent. Without that environment, it cannot learn. [29](#ref-29) This is different from how LLMs learn. Sutton is blunt about language models: they "are trying to get by without having a goal or a sense of better or worse." [30](#ref-30) Here, the missing goal is the missing judge.

In the ancient Chinese game [Go](#glossary-go), organized competitive play relies on human judges to enforce the rules and resolve disputes. In [self-play](#glossary-self-play), the judge is not a person but a simulated environment that encodes the rules exactly. Without that judge, [AlphaZero](#glossary-alphazero) in [2017](#timeline-2017-alphazero) would be lost. It would not learn; it would [hallucinate](#glossary-hallucinations).

In [AlphaGo](#glossary-alphago)'s story in [2016](#timeline-2016-alphago) and [AlphaZero](#glossary-alphazero)'s in [2017](#timeline-2017-alphazero), that judge makes learning via [self-play](#glossary-self-play) possible. The same structure appears in [proof assistants](#glossary-proof-assistant), where a model can propose steps but the checker accepts or rejects them, without negotiation. [31](#ref-31) [32](#ref-32)

Pure language models fall short in games. They can describe [Go](#glossary-go). They can accumulate the knowledge of every [Go](#glossary-go) book written. They can provide a human with expert level coaching. But they do not play it at [AlphaZero](#glossary-alphazero) levels because they do not have a cheap [legal-moves checker](#glossary-legal-moves-checker) acting as judge. Stories can teach style; they do not enforce legality or uncover novel strategies. In this light, Sutton's line about models "trying to get by without having a goal or a sense of better or worse" reads less like a provocation and more like a definition of what the judge supplies. [30](#ref-30)

### [Benchmarks](#glossary-benchmark) as Mechanical Judges

[HumanEval](#glossary-humaneval) in [2021](#timeline-2021-humaneval), [AlphaCode](#glossary-alphacode) in [2022](#timeline-2022-alphacode), and [DIN-SQL](#glossary-din-sql) in [2023](#timeline-2023-din-sql) share a key property: outputs are mechanically checkable. [33](#ref-33) A model can generate a hundred candidates and let tests or execution reject the wrong ones. Those benchmarks work because the [oracle](#glossary-oracle-problem) is unambiguous and cheap to invoke; most real-world domains lack that kind of ground truth. That loop turns a model output into an action. Without it, the same output stays a suggestion.

In human domains, iteration is expensive. A lawyer does not file a thousand briefs and ask a judge to grade them. A doctor does not attempt a thousand diagnoses on one patient. However, these are precisely the sorts of world explorations an AI needs in order to learn.

### Formal Theorem Proving [benchmarks](#glossary-benchmark)

Results like [HILBERT](#glossary-hilbert) on [PutnamBench](#glossary-putnambench) in [2025](#timeline-2025-hilbert) show the jump when proofs are checked by a [formal system](#glossary-formal-system). [34](#ref-34)

### [MCP](#glossary-mcp) and the Connection Layer

The Model Context Protocol ([MCP](#glossary-mcp)) standardizes how models call tools ([2024](#timeline-2024-mcp)). It lowers integration friction and makes verification loops easier to wire into production systems. [35](#ref-35)

We already have [APIs](#glossary-api) for almost all knowledge work performed by humans. [MCP](#glossary-mcp) makes it possible for any [LLM](#glossary-llm) to issue those instructions through a standard interface. The model can automate anything the [API](#glossary-api) can reach.

The missing judge is one that can say which actions were actually required. That absence shows up in ordinary life more than it does in infrastructure. An [MCP](#glossary-mcp)-enabled system can do anything a human can do via [API](#glossary-api). Send an email, file a form, or move money. The integrations are ready. But humans do not know how to write a checker to know if an email should have been sent at all.

### [AlphaProof](#glossary-alphaproof) and Formal Math

[AlphaProof](#glossary-alphaproof) was reported to reach the silver level on IMO problems in [2024](#timeline-2024-alphaproof), with [Lean](#glossary-lean) verifying the proofs. The model proposes, the verifier judges, and the system iterates until it wins. [36](#ref-36)

Formal mathematics is a convenient laboratory: [Lean](#glossary-lean) accepts the proof or it does not.

### Medical Imaging: The Assistant Boundary

Models can detect patterns and approach specialist-level performance on specific tasks, but the outputs are not formally verifiable. Two clinicians can disagree on a borderline scan. Retinopathy results in [2016](#timeline-2016-retinopathy) and dermatology results in [2017](#timeline-2017-dermatology) show the boundary. [2](#ref-2) [37](#ref-37)

These systems are used as assistants; a physician still signs off. The signature is legal cover and a place where accountability and lived consequences concentrate. When the case is ambiguous, the model does not absorb the contested meaning of the decision. Partial automation exists, but the final decision remains human because the rule is not only accuracy but acceptable risk distribution.

### Legal Drafting and the Hallucination Trap

In law, verification is not mechanical. A brief can be grammatically well-formed and logically plausible yet still be unsupported. Citation and case-law checks can be automated, but the hard part is professional judgment: how a court might weigh competing facts, equities, and precedent in a specific case. The [proof boundary](#glossary-proof-boundary) sits in that discretionary weighing, not in syntax.

[Hallucinations](#glossary-hallucinations) are a structural risk in [LLMs](#glossary-llm). The model is trained to predict plausible continuations, not to guarantee grounding. If the prompt looks like it should have a case, the model can invent one that matches the pattern. Without external grounding, the system confuses fluency for evidence. [38](#ref-38)

The model has no built-in notion of "I don't know." It can be instructed to abstain, but the training signal rewards confident completion. Retrieval systems help reduce [hallucinations](#glossary-hallucinations), yet they introduce their own failure modes: missing sources, mismatched citations, or partial context. The output looks more authoritative the more unsupported it becomes. [38](#ref-38)

The Stanford HAI / RegLab analysis in [2024](#timeline-2024-hai-reglab) reports hallucination rates in legal tasks. A judge still checks citations, arguments, and precedent by hand. [1](#ref-1)

A fake citation in a brief can trigger sanctions against the lawyer, not the model. Software cannot be disbarred. Institutions do not delegate without accountability, so adoption remains cautious until verification frameworks and liability regimes mature.

That tension is the human side of the [proof boundary](#glossary-proof-boundary): the checker is a person who signs, and the signature is where accountability lands.

## The [Proof boundary](#glossary-proof-boundary) and Its Consequences

In software, tests and type checks make verification cheap, so teams ship quickly. In law, every draft still needs a licensed signer, so deployment stays cautious.

### Accountability Asymmetry

A radiologist signs a report. A lawyer files a brief. An engineer stamps a design. A developer merges the code. The model signs nothing. There is no license to revoke, no liability to assign, no professional reputation to protect. The signature binds a person to a claim in a way no model can accept.

In software, errors can be patched. In law or medicine, errors become records that follow people.

In domains where the work is a reversible commit, delegation is cheap. In domains where the work is a lived consequence, the hand that signs does not disappear.

### [Decidability](#glossary-decidability) and the Cost of Predictability

When a property is decidable, it can be mechanically verified. When it is not, verification becomes a human judgment. Many properties are decidable in principle but too expensive to check at scale. The more general the system, the less we can establish about it. The more we want proof, the more we must restrict the system. Safety-critical code lives in smaller languages for a reason. Model checking tools note that verification assumes finite data structures and often bounded executions. [39](#ref-39)

High-assurance domains adopt restricted subsets and strict coding standards. [MISRA C](#glossary-misra-c) bans features before they ever reach a checker. [15](#ref-15) SPARK subsets Ada to enable formal analysis. [40](#ref-40)

---

## The Moral Frontier: Formalization and Legitimacy

Statutes, procedures, and enforcement regimes formalize values. Proof systems stop earlier: they do not resolve contested claims without human discretion.

## Civic Struggle and the Limits of Legal Legitimacy

### Resistance and Human Rights ([1900](#timeline-1900-pan-african)-[1950](#timeline-1950-echr))

Early 20th-century resistance movements made legality and legitimacy visibly diverge. The Pan-African Conference in [1900](#timeline-1900-pan-african) argued that colonial rule was a moral and political problem, not just a question of legality. [41](#ref-41) South Africa's [1913](#timeline-1913-land-act) Natives Land Act formalized dispossession, while resistance had to argue against a regime that claimed legal authority. [42](#ref-42) In [1919](#timeline-1919-amritsar) the Amritsar massacre in India and the May Fourth Movement in China illustrated how state power and social legitimacy could split in different national contexts, and how protest could become a competing source of authority. [43](#ref-43) [44](#ref-44)

Mass civil resistance in India tested the moral limits of colonial legality: the [1920](#timeline-1920-noncooperation) Non-Cooperation Movement, the [1930](#timeline-1930-salt-march) Salt March, and the [1942](#timeline-1942-quit-india) Quit India Movement argued that legality could be unjust when it enforced domination. [45](#ref-45) [46](#ref-46) [47](#ref-47) In Europe, the [1935](#timeline-1935-nuremberg-laws) Nuremberg Laws showed how precise legal codification can be an instrument of oppression, while [1939](#timeline-1939-resistance) wartime resistance and the Warsaw Ghetto Uprising left records of the cost of contesting a regime that claimed legal legitimacy. [48](#ref-48) [49](#ref-49)

Postwar human-rights infrastructure formalized a competing moral order. The [1941](#timeline-1941-atlantic-charter) Atlantic Charter announced self-determination as a principle; the [1945](#timeline-1945-un-charter) UN Charter, [1945-1946](#timeline-1945-1946-nuremberg-trials) Nuremberg Trials, and the [1948](#timeline-1948-udhr) Universal Declaration of Human Rights turned that principle into legal architecture; the [1948](#timeline-1948-genocide) Genocide Convention and the [1949](#timeline-1949-geneva) Geneva Conventions tried to make mass atrocity and civilian harm illegal. [50](#ref-50) [51](#ref-51) [52](#ref-52) [53](#ref-53) [54](#ref-54) [55](#ref-55) These legal instruments did not end violence and oppression, but they made the legitimacy contest explicit: a regime could be lawful and still be condemned by a higher, newly formalized moral rule.

### Independence and Decolonization

The Indian Independence Act of [1947](#timeline-1947-independence) is a formal document that ended British rule in law. [56](#ref-56) That legal shift did not resolve state violence, nor the mass displacement and intercommunal violence around partition shaped by imperial policy and boundary-making, nor the long afterlives of imperial administration and coercive institutions. [57](#ref-57) [58](#ref-58) Imperial legitimacy had been codified long before; the transition was a change in legal structure, not an automatic moral reconciliation. The UN declaration on granting independence to countries and peoples codified international support for decolonization and independence claims. [1960](#timeline-1960-un-decolonization) [59](#ref-59) These formal shifts mattered, but they did not retroactively cleanse the violence of imperial systems or the ongoing harms that outlasted independence in land, language, and political power. They simply exposed what was already being contested in streets, courts, and daily survival.

### Women’s Suffrage

The [1848](#timeline-1848-seneca-falls) Seneca Falls Declaration of Sentiments declared the exclusion of women from political life as a moral harm. It was drafted by Elizabeth Cady Stanton, organized with Lucretia Mott, and adopted by the convention attendees. [60](#ref-60) It was not until [1920](#timeline-1920-nineteenth) that the Nineteenth Amendment formalized political inclusion. [61](#ref-61) Yet access to the ballot was not uniform. State barriers, poll taxes, literacy tests, and intimidation continued to block many women, especially women of colour, until later federal protections such as the [1965](#timeline-1965-voting-rights) Voting Rights Act reshaped enforcement. [62](#ref-62) [63](#ref-63) Census voting and registration data continue to show gaps by gender. [64](#ref-64)

### Residential Schools in Canada

Canada’s residential school system was a legal programme that removed Indigenous children from their families and communities, placing them under state- and church-run schooling designed to sever language, culture, and kinship. Churches that administered schools included the Roman Catholic, Anglican, United, and Presbyterian churches. [65](#ref-65) The federal system took form in [1883](#timeline-1883-residential-schools) under Prime Minister John A. Macdonald’s government, which authorized state-run residential and industrial schools as policy. [65](#ref-65) Under Prime Minister Pierre Elliot Trudeau, with Jean Chrétien (later Prime Minister) as Minister of Indian Affairs, the [1969](#timeline-1969-white-paper) White Paper pushed a new assimilationist direction, proposing to end legal Indian status and transfer federal responsibilities to the provinces, reframing obligations as a path to formal integration without ending the school system itself. [66](#ref-66) Indigenous children continued to be displaced by the govenment until the last federally run residential school closed in [1996](#timeline-1996-residential-schools-closure), under Prime Minister Jean Chrétien, who finally ended the education system he had decades ago "reformed". [67](#ref-67) The system’s authority was bureaucratic and lawful; its harm was lived and cumulative. In [2021](#timeline-2021-residential-schools), under Prime Minister Justin Trudeau, Pierre Trudeau’s son, reports of unmarked graves at former school sites made that harm visible in a new way, and forced a public reckoning with how legality can mask coercion and loss. [68](#ref-68)

### U.S. Civil Rights Movement

The civil rights struggle made the machinery of legitimacy visible. Martin Luther King Jr. argued from a jail cell that legality is not the same as moral legitimacy, and that obedience to laws that degrade people fails the movement’s moral frame. [69](#ref-69) The U.S. Supreme Court’s [1954](#timeline-1954-brown) decision in *Brown v. Board of Education* formally rejected “separate but equal,” but the decision did not end segregationist resistance or erase entrenched power. [70](#ref-70) The Civil Rights Act of [1964](#timeline-1964-civil-rights) and the Voting Rights Act of [1965](#timeline-1965-voting-rights) codified equality and political inclusion into law. [71](#ref-71) [62](#ref-62) Those changes were necessary, but they did not end all disenfranchisement or the backlash that followed. [72](#ref-72) [63](#ref-63) King was assassinated in [1968](#timeline-1968-mlk-death) while he was in Memphis at the Lorraine Motel. [73](#ref-73) [74](#ref-74) Even after his death, the movement faced continued resistance to desegregation and voting access. [72](#ref-72) [63](#ref-63) To this day, census voting and registration data still show racial gaps. [64](#ref-64)

### Holodomor

The Holodomor in Ukraine in [1932-1933](#timeline-1932-holodomor) was a policy-driven famine. Ukraine was a key grain-producing area in the Soviet Union. [75](#ref-75) Under Stalin, quotas arrived as state directives and were enforced as legal orders. [75](#ref-75) Search teams executed those directives; decrees restricted movement, and the [January 22, 1933](#timeline-1932-holodomor) order stopped starving peasants from escaping. [75](#ref-75) Demographers estimate close to four million residents of Ukraine died from starvation. [75](#ref-75) Against the 1926 census population of 29.0 million in the Ukrainian SSR, that is roughly 14% of the population. [76](#ref-76) Ukraine’s [2006](#timeline-2006-holodomor-law) law defines the Holodomor of 1932–1933 as genocide. [77](#ref-77)

### Anti-Apartheid Movement

In South Africa, the [1955](#timeline-1955-freedom-charter) Freedom Charter, drafted by anti-apartheid organisers and adopted at the Congress of the People, set out the civic order the movement demanded: a non-racial democracy that directly contested apartheid’s legal claims. [78](#ref-78) In [1964](#timeline-1964-statement-from-dock), Nelson Mandela’s “Statement from the Dock,” delivered during the Rivonia Trial, made that moral case against a legal regime that had already formalized racial domination. The Rivonia Trial was the prosecution of ANC leaders for sabotage and related charges, with the state seeking to break the anti-apartheid movement. Mandela received a life sentence. [79](#ref-79) [80](#ref-80) The legal system’s precision was not its redemption; it was the method by which oppression was enforced. The movement brought that architecture into the open, but it did not confer moral legitimacy on the regime. After 27 years in prison, Mandela was released in [1990](#timeline-1990-mandela-release). He was elected President in [1994](#timeline-1994-mandela-election). [80](#ref-80)

### Indigenous Rights

The UN Declaration on the Rights of Indigenous Peoples formalizes recognition of rights that long predated the document. [2007](#timeline-2007-undrip) [81](#ref-81)

### Disability Rights

The Americans with Disabilities Act formalized access and anti-discrimination in law. [1990](#timeline-1990-ada) [82](#ref-82) The law made exclusions explicit and enforceable, but it also revealed how institutions define “reasonable accommodation.”

### LGBTQ+ Rights

Obergefell v. Hodges formalized marriage equality in the United States, turning a moral debate into enforceable legal recognition. [2015](#timeline-2015-obergefell) [83](#ref-83) This was a formal recognition of inclusion claims, but it did not end discrimination or the ongoing harms faced by trans and gender-nonconforming people.

## Conclusion: The Never-Ending Human Narrative

The telegraph turned days into minutes. The telephone collapsed distance. Television made politics a performance people could watch from the couch. The internet and social media collapsed publishing into an endless scroll, and AI now compresses knowledge work into a prompt. Institutions respond after the fact: the rules arrive after the habits do, and the gaps are visible in the years between adoption and regulation. Australia's under-16 social media law in [2024](#timeline-2024-australia-law) is one recent marker of that lag. [84](#ref-84)

Marshall McLuhan summarized the dynamic as "[the medium is the message](#glossary-medium-is-the-message)." [85](#ref-85) In 1945, Arthur C. Clarke sketched a world-spanning relay network—essentially the internet—and argued that a "true broadcast service, giving constant field strength at all times over the whole globe would be invaluable, not to say indispensable, in a world society." [86](#ref-86) Put together, the point is that new tools reshape how we act before we agree on why we should trust them. The [proof boundary](#glossary-proof-boundary) is the line where that trust is assigned through power consensus, not earned by capability.

AI taking responsibility for real decisions is less about raw model capability and more about the [proof boundary](#glossary-proof-boundary). We already expose much of our knowledge work to automation through [APIs](#glossary-api), and [MCP](#glossary-mcp) makes those systems directly callable by [LLMs](#glossary-llm). The missing piece is not another model upgrade. It is a checker that can show, step by step, that the agent read what mattered, responded to what was required, and recorded what it owes. For now, the handoff still ends with a human deciding whether the record is convincing enough to let the work ship. That does not change with a better model, it changes with humans deciding it is worth it to pay the cost of formalization.

This tension turns out to be the same self-reference problem Gödel made unavoidable. A checker that claims "every required action was handled" must spell out what counts as required, what counts as evidence, and which [oracle](#glossary-oracle-problem) gets the last word. It is a system trying to justify its own completeness. The rules need a judge outside the rules, and once you introduce that judge, you are back to the boundary again. This is not an AI shortcoming awaiting an update; this is an immutable property of [formal systems](#glossary-formal-system) themselves. Proofs do not abolish discretion. They only relocate it, explicitly, to formal rules. Gödel proved that incompleteness is a property of logic itself. If you want formal proofs for anything, you must accept this message. No new medium will ever replace this.

The twist is that the [proof boundary](#glossary-proof-boundary) makes adoption predictable. Economic pressure and political incentive push it outward. Formal work checkers are the only way to make human labour obsolete, because it's the only kind of authority an AI can understand and learn from. [Sutton](#ref-30)'s complaint that [LLMs](#glossary-llm) don't have a plan is the same missing judge in another form: without a proof-backed objective, the system cannot choose a path with confidence. Economics and politics can only happen along lines that can be formalized. Before AI can take over the mundane and tedious parts of life, those domains need formal proof checkers. Because of the [oracle problem](#glossary-oracle-problem), only humans can provide them. Or decide not to. Whatever is not provable stays in the realm of judgment, negotiation, and signature. Capitalism wants us to see the proof boundary as an ever expanding horizon of human wonder and opportunity. The reality is that the proof boundary can be moved in either direction. Formal rules can, and should be, removed whenever the illusion of legitimacy stops the humans responsible for the rules from being held accountable.

Comfort with [formal systems](#glossary-formal-system) varies widely across individuals and cultures, so the push to expand the [proof boundary](#glossary-proof-boundary) does not land evenly. Economic pressure to extract value from automation rewards early adopters of newly formalized systems, who are often those with the best access and opportunity. The drive to expand the boundary often widens existing gaps. That makes the boundary a social justice issue as well as a technical one.

Communities already forced to defend their standing in front of authority will feel formal checkers as an amplifier: the system can now say "the rule was followed" with machine certainty while the people affected are left to contest the rule itself. When the [proof boundary](#glossary-proof-boundary) moves, it does not move evenly. It can speed access and close doors at the same time.

Where proof can sign, automation becomes normal; where it cannot, responsibility stays human. Solving the [oracle problem](#glossary-oracle-problem) is the price of crossing that line, and it carries a moral hazard: the [oracle](#glossary-oracle-problem) embeds who gets to define correctness, which facts count, and which harms are tolerable. When the [oracle](#glossary-oracle-problem) is wrong or partial, the proof still passes, and the power behind the [oracle](#glossary-oracle-problem) is the only place left to contest it.

Gödel also forces a final symmetry: authority can only justify itself by reference to the system it governs. Courts reason in law because law authorizes courts. Removing the human adjudicator does not break the self-referential circle. It hardens it into code. The [oracle](#glossary-oracle-problem) becomes the legislature.

## Recommended for Further Reading

*Gödel, Escher, Bach* ([1979](#timeline-1979-geb))—Douglas Hofstadter [6](#ref-6)

Explores self-reference, [formal systems](#glossary-formal-system), and proof mechanics, with a sustained focus on how rule-bound systems generate their own paradoxes. The book gives the intellectual machinery for understanding why any attempt to certify that every stated requirement in a system has been satisfied must encode its own assumptions about what counts as proof and who can validate its completion. It shows why limits in formal reasoning are structural, not just a tooling gap.

*The Whale and the Reactor* ([1986](#timeline-1986-whale-reactor))—Langdon Winner [87](#ref-87)

Argues that technologies reorganize authority as surely as they deliver power, and insists that design choices are political decisions even when presented as neutral engineering. The essays are concise but relentless about how infrastructure determines who has agency, who must comply, and who is made visible or invisible to the system. It is a clear map of how technical structures allocate control.

*Sapiens* ([2015](#timeline-2015-sapiens))—Yuval Noah Harari [88](#ref-88)

Frames myth as the shared fiction that makes large-scale human coordination possible, emphasizing how institutions, law, and money scale trust through agreed narratives. This framing is useful for seeing how [formal verification](#glossary-formal-verification) becomes its own coordination story, promising certainty in exchange for compliance with its rules. The book also shows how these stories exclude as much as they include, which mirrors the way formal rules can grant legitimacy while narrowing who is recognized by the system.

*Automating Inequality* ([2018](#timeline-2018-automating-inequality))—Virginia Eubanks [89](#ref-89)

Follows welfare systems as they become digital gatekeepers, showing how automation redraws the boundary between acceptable and unacceptable claims in practice, not in theory. The case studies are grounded in the lived mechanics of eligibility, appeal, and documentation, which exposes how formal rules can compress complex realities into brittle checks. It makes visible how those checks govern access, constrain discretion, and shift responsibility onto those least equipped to contest the logic.

*Race After Technology* ([2019](#timeline-2019-race-after-technology))—Ruha Benjamin [90](#ref-90)

Traces how ostensibly neutral technical systems encode hierarchy in data, design, and deployment, and shows how those hierarchies survive even when decisions are framed as objective. The book makes the stakes of verification legible by following how classification, scoring, and automation decide who is allowed to proceed and who is turned away. It draws a clear line between technical formality and the human consequences of who gets counted.

---

## Appendices

### Appendix A: Chronological Narrative of Proof and Power

Timeline:
- <a id="timeline-1848-seneca-falls"></a>1848: Seneca Falls Declaration of Sentiments frames women's political exclusion as a moral harm. [60](#ref-60)
- <a id="timeline-1883-residential-schools"></a>1883: Canadian federal policy formalizes the residential school system. [65](#ref-65)
- <a id="timeline-1900-pan-african"></a>1900: Pan-African Conference in London frames anti-colonial and rights claims. [41](#ref-41)
- <a id="timeline-1901"></a>1901: [Russell's paradox](#glossary-russells-paradox) exposes contradictions in naive set theory. [4](#ref-4)
- <a id="timeline-1907"></a>1907: Quebec Bridge collapse. [8](#ref-8)
- <a id="timeline-1913-land-act"></a>1913: South Africa's Natives Land Act formalizes land dispossession. [42](#ref-42)
- <a id="timeline-1919-amritsar"></a><a id="timeline-1919-may-fourth"></a>1919: Amritsar massacre intensifies anti-colonial resistance in India; May Fourth Movement in China challenges imperial influence and legitimacy. [43](#ref-43) [44](#ref-44)
- <a id="timeline-1920-noncooperation"></a><a id="timeline-1920-nineteenth"></a>1920: Indian Non-Cooperation Movement begins (1920-1922); U.S. Nineteenth Amendment formalises women's suffrage. [45](#ref-45) [61](#ref-61)
- <a id="timeline-1930-salt-march"></a>1930: Salt March from Sabarmati Ashram to Dandi, India. [46](#ref-46)
- <a id="timeline-1931"></a>1931: Gödel demonstrates [incompleteness](#glossary-incompleteness) constraints in [formal systems](#glossary-formal-system). [5](#ref-5)
- <a id="timeline-1932-holodomor"></a>1932-1933: Holodomor in Ukraine. [75](#ref-75)
- <a id="timeline-1935-nuremberg-laws"></a>1935: Nuremberg Laws formalize racial hierarchy in Germany. [48](#ref-48)
- <a id="timeline-1936"></a>1936: Turing demonstrates the [halting problem](#glossary-halting-problem) is undecidable. [7](#ref-7)
- <a id="timeline-1939-resistance"></a>1939: WWII resistance movements intensify through 1945, including the Warsaw Ghetto Uprising. [49](#ref-49)
- <a id="timeline-1940-assembly"></a>1940: Assembly era manual validation dominates through the 1950s. [91](#ref-91)
- <a id="timeline-1941-atlantic-charter"></a><a id="timeline-1941-turing"></a>1941: Atlantic Charter outlines self-determination principles; Turing's codebreaking work at Bletchley Park accelerates Allied intelligence. [50](#ref-50) [7](#ref-7)
- <a id="timeline-1942-quit-india"></a>1942: Quit India Movement calls for immediate British withdrawal and mass civil disobedience. [47](#ref-47)
- <a id="timeline-1945-clarke"></a><a id="timeline-1945-un-charter"></a><a id="timeline-1945-1946-nuremberg-trials"></a>1945: Arthur C. Clarke publishes "Extra-Terrestrial Relays" in *Wireless World*, effectively predicting the Internet. [86](#ref-86); UN Charter establishes a postwar human-rights framework. [51](#ref-51); Nuremberg Trials formalise accountability for war crimes (1945-1946). [52](#ref-52)
- <a id="timeline-1947-independence"></a>1947: Indian Independence Act ends British rule in law. [56](#ref-56)
- <a id="timeline-1948-udhr"></a><a id="timeline-1948-genocide"></a>1948: Universal Declaration of Human Rights adopted; Genocide Convention adopted. [53](#ref-53) [54](#ref-54)
- <a id="timeline-1949-geneva"></a>1949: Geneva Conventions updated to codify protections in war. [55](#ref-55)
- <a id="timeline-1950-echr"></a>1950: European Convention on Human Rights signed. [92](#ref-92)
- <a id="timeline-1954-brown"></a>1954: *Brown v. Board of Education* formally rejects “separate but equal.” [70](#ref-70)
- <a id="timeline-1955-freedom-charter"></a>1955: Freedom Charter articulates a competing moral order in South Africa. [78](#ref-78)
- <a id="timeline-1957-compilers"></a>1957: [Compiler](#glossary-compiler) revolution accelerates (1957-1959; [FORTRAN](#glossary-fortran), [COBOL](#glossary-cobol)). [16](#ref-16)
- <a id="timeline-1960-un-decolonization"></a>1960: UN General Assembly Resolution 1514 affirms decolonization and self-determination. [59](#ref-59)
- <a id="timeline-1962-mandela-imprisonment"></a>1962: Nelson Mandela is arrested and imprisoned, receiving a five-year sentence. [80](#ref-80)
- <a id="timeline-1963-mlk-jail"></a><a id="timeline-1963-mlk-release"></a><a id="timeline-1963-i-have-a-dream"></a>1963: Martin Luther King Jr. is jailed in Birmingham and released three days later; delivers the "I Have a Dream" speech. [69](#ref-69) [74](#ref-74)
- <a id="timeline-1964-mcluhan"></a><a id="timeline-1964-civil-rights"></a><a id="timeline-1964-statement-from-dock"></a>1964: McLuhan publishes *Understanding Media*, its opening line: "[the medium is the message](#glossary-medium-is-the-message)"; Civil Rights Act codifies equality and inclusion; Mandela delivers “Statement from the Dock” during the Rivonia trial, gets sentenced to life in prison. [85](#ref-85) [71](#ref-71) [79](#ref-79) [80](#ref-80)
- <a id="timeline-1965-voting-rights"></a>1965: Voting Rights Act codifies political inclusion. [62](#ref-62)
- <a id="timeline-1968-mlk-death"></a>1968: Martin Luther King Jr. is assassinated. [73](#ref-73)
- <a id="timeline-1969-white-paper"></a>1969: Canada issues the White Paper on Indian policy. Residential schools keep operating. [66](#ref-66)
- <a id="timeline-1970s"></a>1970s: [type systems](#glossary-type-system) take hold ([Pascal](#glossary-pascal), [C](#glossary-c), [ML](#glossary-ml)). [93](#ref-93) [94](#ref-94) [95](#ref-95)
- <a id="timeline-1979-geb"></a>1979: Hofstadter publishes *Gödel, Escher, Bach*. [6](#ref-6)
- <a id="timeline-1980-fp"></a>1980: Functional programming emerges through the 1980s-1990s ([Miranda](#glossary-miranda), [Haskell](#glossary-haskell)). [96](#ref-96) [22](#ref-22)
- <a id="timeline-1982"></a>1982: [Byzantine Generals problem](#glossary-byzantine-generals) formalises distributed agreement constraints. [17](#ref-17)
- <a id="timeline-1985-cpp"></a>1985: [C++](#glossary-cpp) emerges as a systems language. [97](#ref-97)
- <a id="timeline-1985-therac"></a>1985: Therac-25 overdoses and patient deaths (1985-1987). [9](#ref-9) [10](#ref-10)
- <a id="timeline-1986-whale-reactor"></a><a id="timeline-1986-isabelle-hol"></a><a id="timeline-1986-sql"></a>1986: Winner publishes *The Whale and the Reactor*; [Isabelle/HOL](#glossary-isabelle-hol) [proof assistant](#glossary-proof-assistant) introduced; [SQL](#glossary-sql) standardises core semantics. [87](#ref-87) [20](#ref-20) [22](#ref-22)
- <a id="timeline-1989-coq"></a>1989: [Coq](#glossary-coq) [proof assistant](#glossary-proof-assistant) introduced. [22](#ref-22)
- <a id="timeline-1990-haskell"></a><a id="timeline-1990-mandela-release"></a><a id="timeline-1990-ada"></a>1990: [Haskell](#glossary-haskell) launches; Mandela is released from prison; Americans with Disabilities Act is enacted. [22](#ref-22) [80](#ref-80) [82](#ref-82)
- <a id="timeline-1993"></a>1993: [NVIDIA](#glossary-nvidia) founded for PC gaming [GPUs](#glossary-gpu). [25](#ref-25)
- <a id="timeline-1994"></a><a id="timeline-1994-mandela-election"></a>1994: Pentium FDIV bug and recall; Nelson Mandela is elected President of South Africa. [11](#ref-11) [80](#ref-80)
- <a id="timeline-1996"></a><a id="timeline-1996-residential-schools-closure"></a>1996: Ariane 5 failure at 37 seconds; last federally run residential school closes in Canada. [12](#ref-12) [13](#ref-13) [67](#ref-67)
- <a id="timeline-1999"></a>1999: [TLA+](#glossary-tla) formal methods mature for [distributed systems](#glossary-distributed-systems). [18](#ref-18)
- <a id="timeline-2002"></a>2002: Bezos [API](#glossary-api) mandate and internal service externalisation. [21](#ref-21)
- <a id="timeline-2006"></a><a id="timeline-2006-compcert"></a><a id="timeline-2006-holodomor-law"></a>2006: [AWS](#glossary-aws) launches S3 and EC2; [CUDA](#glossary-cuda) enables general [GPU](#glossary-gpu) computing; [CompCert](#glossary-compcert) project releases; Ukraine passes the Holodomor law recognizing the famine as genocide. [18](#ref-18) [27](#ref-27) [33](#ref-33) [77](#ref-77)
- <a id="timeline-2007-dynamo"></a><a id="timeline-2007"></a><a id="timeline-2007-undrip"></a>2007: [Amazon](#glossary-amazon) publishes the Dynamo key-value store design; [Z3](#glossary-z3) [SMT solver](#glossary-smt-solver) released; UN Declaration on the Rights of Indigenous Peoples adopted. [18](#ref-18) [23](#ref-23) [81](#ref-81)
- <a id="timeline-2009-sel4"></a>2009: [seL4](#glossary-sel4) proof published. [19](#ref-19)
- <a id="timeline-2009-toyota"></a>2009: [Toyota](#glossary-toyota) unintended acceleration crisis (2009-2011). [14](#ref-14)
- <a id="timeline-2010-rust"></a>2010: [Rust](#glossary-rust) project begins. [22](#ref-22)
- <a id="timeline-2011"></a>2011: [Amazon](#glossary-amazon) uses [TLA+](#glossary-tla) to find deep distributed-system bugs. [18](#ref-18)
- <a id="timeline-2012-alexnet"></a>2012: AlexNet shows [GPU](#glossary-gpu) advantage for [deep learning](#glossary-deep-learning). [98](#ref-98)
- <a id="timeline-2013-mandela-death"></a>2013: Nelson Mandela dies at 95. [80](#ref-80)
- <a id="timeline-2015-sapiens"></a><a id="timeline-2015-obergefell"></a>2015: Harari publishes *Sapiens*; *Obergefell v. Hodges* recognises marriage equality in the United States. [88](#ref-88) [83](#ref-83)
- <a id="timeline-2016-alphago"></a><a id="timeline-2016-retinopathy"></a>2016: [AlphaGo](#glossary-alphago) defeats top human players in [Go](#glossary-go); retinopathy model validation published. [31](#ref-31) [2](#ref-2)
- <a id="timeline-2017-transformer"></a><a id="timeline-2017-alphazero"></a><a id="timeline-2017-dermatology"></a>2017: *Attention Is All You Need* introduces the [transformer](#glossary-transformer), unlocking scalable [LLMs](#glossary-llm); [AlphaZero](#glossary-alphazero) demonstrates self-play learning; dermatology classifier reaches specialist-level accuracy; [deep learning](#glossary-deep-learning) medical imaging breakthroughs broaden in subsequent years. [28](#ref-28) [32](#ref-32) [37](#ref-37)
- <a id="timeline-2018-bridge-ai"></a><a id="timeline-2018-automating-inequality"></a>2018: Deep learning crack detection appears in civil infrastructure inspection; [formal verification](#glossary-formal-verification) case studies mature in subsequent years ([CompCert](#glossary-compcert), [seL4](#glossary-sel4)); Eubanks publishes *Automating Inequality*. [3](#ref-3) [19](#ref-19) [20](#ref-20) [89](#ref-89)
- <a id="timeline-2019-race-after-technology"></a>2019: Benjamin publishes *Race After Technology*. [90](#ref-90)
- <a id="timeline-2020-ross"></a>2020: Thomson Reuters v. [ROSS Intelligence](#glossary-ross) litigation begins. [99](#ref-99)
- <a id="timeline-2021-copilot"></a><a id="timeline-2021-humaneval"></a><a id="timeline-2021-residential-schools"></a>2021: [GitHub](#glossary-github) [Copilot](#glossary-copilot) launches; [HumanEval](#glossary-humaneval) benchmark released; unmarked graves are reported at former residential schools in Canada. [100](#ref-100) [33](#ref-33) [68](#ref-68)
- <a id="timeline-2022-chatgpt"></a><a id="timeline-2022-alphacode"></a>2022: [OpenAI](#glossary-openai) launches [ChatGPT](#glossary-chatgpt); [LLMs](#glossary-llm) go mainstream; [AlphaCode](#glossary-alphacode) results published; [FDA](#glossary-fda) approvals for AI devices rise through 2024 while clinical adoption remains low. [101](#ref-101) [33](#ref-33) [102](#ref-102)
- <a id="timeline-2023-mata"></a><a id="timeline-2023-din-sql"></a>2023: Mata v Avianca sanctions over fake citations; [DIN-SQL](#glossary-din-sql) benchmark released. [103](#ref-103) [33](#ref-33)
- <a id="timeline-2024-mcp"></a><a id="timeline-2024-hai-reglab"></a><a id="timeline-2024-alphaproof"></a><a id="timeline-2024-australia-law"></a>2024: [MCP](#glossary-mcp) standardises tool access for [LLMs](#glossary-llm); Stanford HAI / RegLab hallucination analysis published; [AlphaProof](#glossary-alphaproof) solves IMO problems at silver level; [Lean](#glossary-lean) verifies proofs; Australia enacts under-16 social media law. [35](#ref-35) [1](#ref-1) [36](#ref-36) [84](#ref-84)
- <a id="timeline-2025-hilbert"></a>2025: [HILBERT](#glossary-hilbert) reaches ~70% on [PutnamBench](#glossary-putnambench) formal proofs. [34](#ref-34)



### Appendix B: Glossary

- <a id="glossary-proof-boundary"></a>**[Proof boundary](#glossary-proof-boundary)**: The line between what can be verified mechanically and what must be judged by humans.
- <a id="glossary-llm"></a>**[LLM](#glossary-llm) (Large Language Model)**: A model trained to predict text at scale, using [transformers](#glossary-transformer) to absorb large, human-curated corpora. [28](#ref-28)
- <a id="glossary-trolley-problem"></a>**[Trolley problem](#glossary-trolley-problem)**: A moral thought experiment that illustrates that there is no universally accepted moral rule for choosing between harmful alternatives.
- <a id="glossary-formal-language"></a>**[Formal language](#glossary-formal-language)**: A language with explicit syntax rules that can be mechanically checked by a [compiler](#glossary-compiler) or parser.
- <a id="glossary-markdown"></a>**[Markdown](#glossary-markdown)**: A lightweight markup language for structured text and links. The formal language in which this document is written.
- <a id="glossary-compiler"></a>**[Compiler](#glossary-compiler)**: A program that translates source code into another form while enforcing formal rules, often alongside [static analysis](#glossary-static-analysis).
- <a id="glossary-russells-paradox"></a>**[Russell's paradox](#glossary-russells-paradox)**: A self-reference paradox in naive set theory. [4](#ref-4)
- <a id="glossary-formal-system"></a>**[Formal system](#glossary-formal-system)**: A language plus rules for deriving valid statements, underlying [proof assistants](#glossary-proof-assistant) and [type systems](#glossary-type-system).
- <a id="glossary-incompleteness"></a>**[Incompleteness](#glossary-incompleteness)**: The condition that some claims are not derivable within a system. [5](#ref-5)
- <a id="glossary-proof-assistant"></a>**[Proof assistant](#glossary-proof-assistant)**: A tool that helps construct and verify proofs in a [formal system](#glossary-formal-system).
- <a id="glossary-halting-problem"></a>**[Halting problem](#glossary-halting-problem)**: The undecidable question of whether a program terminates. [7](#ref-7)
- <a id="glossary-formal-verification"></a>**[Formal verification](#glossary-formal-verification)**: Mathematical proof, checked by automated tools such as [proof assistants](#glossary-proof-assistant) and [model checkers](#glossary-model-checker), that a system satisfies a specification under explicit assumptions.
- <a id="glossary-race-condition"></a>**[Race condition](#glossary-race-condition)**: A bug that occurs when timing or ordering of concurrent operations changes the outcome.
- <a id="glossary-intel"></a>**[Intel](#glossary-intel)**: A semiconductor company behind the Pentium processors. [104](#ref-104)
- <a id="glossary-esa"></a>**[ESA (European Space Agency)](#glossary-esa)**: A multinational space agency responsible for scientific and exploration missions, including Cluster. [105](#ref-105)
- <a id="glossary-toyota"></a>**[Toyota](#glossary-toyota)**: An automaker involved in unintended-acceleration investigations. [14](#ref-14)
- <a id="glossary-nasa"></a>**[NASA](#glossary-nasa)**: The U.S. space agency involved in automotive software analysis reports. [15](#ref-15)
- <a id="glossary-misra-c"></a>**[MISRA C](#glossary-misra-c)**: A safety-oriented [C](#glossary-c) coding standard. [15](#ref-15)
- <a id="glossary-static-analysis"></a>**[Static analysis](#glossary-static-analysis)**: Automated reasoning about code without executing it, often integrated into a [compiler](#glossary-compiler).
- <a id="glossary-fortran"></a>**[FORTRAN](#glossary-fortran)**: One of the earliest high-level programming languages, designed for scientific computing. [16](#ref-16)
- <a id="glossary-cobol"></a>**[COBOL](#glossary-cobol)**: A business-oriented programming language designed for data processing. [16](#ref-16)
- <a id="glossary-type-system"></a>**[Type system](#glossary-type-system)**: A formal discipline that classifies program terms and prevents invalid operations, enforced by a [compiler](#glossary-compiler).
- <a id="glossary-purity"></a>**[Purity](#glossary-purity)**: A function's output depends only on its inputs, with no side effects, often emphasized in [functional languages](#glossary-functional-languages).
- <a id="glossary-functional-programming"></a>**[Functional programming](#glossary-functional-programming)**: A programming paradigm built around [functional languages](#glossary-functional-languages) and [purity](#glossary-purity).
- <a id="glossary-functional-languages"></a>**[Functional languages](#glossary-functional-languages)**: Languages that emphasize mathematics, [purity](#glossary-purity), immutability, and referential transparency.
- <a id="glossary-imperative-languages"></a>**[Imperative languages](#glossary-imperative-languages)**: Languages organized around statements that mutate program state.
- <a id="glossary-distributed-systems"></a>**[Distributed systems](#glossary-distributed-systems)**: Systems composed of multiple networked components that must coordinate state and handle failures.
- <a id="glossary-byzantine-generals"></a>**[Byzantine Generals problem](#glossary-byzantine-generals)**: A distributed-systems problem showing that agreement is hard when some participants may lie or fail. [17](#ref-17)
- <a id="glossary-amazon"></a>**[Amazon](#glossary-amazon)**: A technology company whose infrastructure work popularized formal methods like [TLA+](#glossary-tla). [18](#ref-18)
- <a id="glossary-tla"></a>**[TLA+](#glossary-tla)**: A specification language for concurrent and [distributed systems](#glossary-distributed-systems). [18](#ref-18)
- <a id="glossary-invariant"></a>**[Invariant](#glossary-invariant)**: A property that must hold for all reachable states of a system, often checked by a [model checker](#glossary-model-checker).
- <a id="glossary-model-checker"></a>**[Model checker](#glossary-model-checker)**: A tool that exhaustively explores state space to find violations of a specification or [invariant](#glossary-invariant).
- <a id="glossary-aws"></a>**[AWS (Amazon Web Services)](#glossary-aws)**: [Amazon](#glossary-amazon)'s cloud platform. [18](#ref-18)
- <a id="glossary-compcert"></a>**[CompCert](#glossary-compcert)**: A formally verified [C](#glossary-c) compiler with machine-checked compliance to its spec in [Coq](#glossary-coq). [19](#ref-19)
- <a id="glossary-sel4"></a>**[seL4](#glossary-sel4)**: a formally verified microkernel with machine-checked compliance to its spec. [19](#ref-19)
- <a id="glossary-c"></a>**[C](#glossary-c)**: A low-level systems programming language with manual memory control. [94](#ref-94)
- <a id="glossary-isabelle-hol"></a>**[Isabelle/HOL](#glossary-isabelle-hol)**: A [proof assistant](#glossary-proof-assistant) and higher-order logic environment with large, machine-checked libraries. [20](#ref-20)
- <a id="glossary-api"></a>**[API (Application Programming Interface)](#glossary-api)**: A formal interface that defines how software components interact.
- <a id="glossary-sql"></a>**[SQL](#glossary-sql)**: A query language with formal, executable semantics. [22](#ref-22)
- <a id="glossary-coq"></a>**[Coq](#glossary-coq)**: A [proof assistant](#glossary-proof-assistant) based on dependent type theory. [22](#ref-22)
- <a id="glossary-haskell"></a>**[Haskell](#glossary-haskell)**: A purely [functional language](#glossary-functional-languages) with strong type systems. [22](#ref-22)
- <a id="glossary-smt-solver"></a>**[SMT (satisfiability modulo theories) solver](#glossary-smt-solver)**: Automated solver for logical formulas in satisfiability modulo theories. [24](#ref-24)
- <a id="glossary-z3"></a>**[Z3](#glossary-z3)**: A widely used [SMT solver](#glossary-smt-solver) developed by Microsoft Research. [23](#ref-23)
- <a id="glossary-ann"></a>**[ANNs](#glossary-ann) (Artificial neural networks)**: Layered statistical models that learn patterns by adjusting weights through training data.
- <a id="glossary-transformer"></a>**[Transformer](#glossary-transformer)**: An [ANN](#glossary-ann) architecture built around self-attention, enabling parallel processing of sequences and flexible long-range dependencies; this makes scaling to large language models practical. [28](#ref-28)
- <a id="glossary-gpu"></a>**[GPU](#glossary-gpu)**: A processor optimized for parallel arithmetic computation, offering far higher throughput for many workloads than [CPUs](#glossary-cpu). [27](#ref-27)
- <a id="glossary-medium-is-the-message"></a>**[The medium is the message](#glossary-medium-is-the-message)**: McLuhan's claim that the characteristics of a medium shape social effects more than its content. [85](#ref-85)
- <a id="glossary-nvidia"></a>**[NVIDIA](#glossary-nvidia)**: A company founded by Jensen Huang, known for GPUs and [CUDA](#glossary-cuda). [25](#ref-25)
- <a id="glossary-cuda"></a>**[CUDA](#glossary-cuda)**: [NVIDIA](#glossary-nvidia)'s platform for general-purpose [GPU](#glossary-gpu) computing. [27](#ref-27)
- <a id="glossary-cpu"></a>**[CPU](#glossary-cpu)**: A general-purpose processor optimized for low-latency, sequential execution and broad instruction support.
- <a id="glossary-deep-learning"></a>**[Deep learning](#glossary-deep-learning)**: A machine learning approach that trains multilayer [ANNs](#glossary-ann) to learn representations from large datasets.
- <a id="glossary-rl"></a>**[Reinforcement learning](#glossary-rl)**: Learning by interaction with an environment using rewards, often paired with [self-play](#glossary-self-play) in games. [29](#ref-29)
- <a id="glossary-go"></a>**[Go](#glossary-go)**: A board game of territory and influence played on a grid of intersections, where players place stones to control space.
- <a id="glossary-self-play"></a>**[Self-play](#glossary-self-play)**: Training by playing against copies of oneself in a formal environment with a [legal-moves checker](#glossary-legal-moves-checker). [32](#ref-32)
- <a id="glossary-alphazero"></a>**[AlphaZero](#glossary-alphazero)**: A general [self-play](#glossary-self-play) system for [Go](#glossary-go), chess, and shogi. [32](#ref-32)
- <a id="glossary-hallucinations"></a>**[Hallucinations](#glossary-hallucinations)**: Model outputs that appear fluent and plausible but are unsupported or fabricated relative to the source context. [38](#ref-38)
- <a id="glossary-alphago"></a>**[AlphaGo](#glossary-alphago)**: A [Go](#glossary-go) system that learned via [self-play](#glossary-self-play) and a [legal-moves checker](#glossary-legal-moves-checker). [31](#ref-31)
- <a id="glossary-legal-moves-checker"></a>**[Legal-moves checker](#glossary-legal-moves-checker)**: An external rule engine that rejects invalid actions.
- <a id="glossary-benchmark"></a>**[Benchmark](#glossary-benchmark)**: A standardized task for evaluation with defined scoring.
- <a id="glossary-humaneval"></a>**[HumanEval](#glossary-humaneval)**: A code benchmark with mechanically checkable tests. [33](#ref-33)
- <a id="glossary-alphacode"></a>**[AlphaCode](#glossary-alphacode)**: A code-generation system evaluated on competitive programming tasks. [33](#ref-33)
- <a id="glossary-din-sql"></a>**[DIN-SQL](#glossary-din-sql)**: A benchmark for text-to-[SQL](#glossary-sql) with executable verification. [33](#ref-33)
- <a id="glossary-oracle-problem"></a>**[Oracle problem](#glossary-oracle-problem)**: The difficulty of defining a trustworthy ground‑truth judge for a task, including who sets the criteria, which evidence counts, and how disputes are resolved.
- <a id="glossary-hilbert"></a>**[HILBERT](#glossary-hilbert)**: A system reporting results on [PutnamBench](#glossary-putnambench). [34](#ref-34)
- <a id="glossary-putnambench"></a>**[PutnamBench](#glossary-putnambench)**: A formal mathematics benchmark. [34](#ref-34)
- <a id="glossary-mcp"></a>**[MCP (Model Context Protocol)](#glossary-mcp)**: An open protocol that defines how models describe, call, and exchange data with external tools and services. [35](#ref-35)
- <a id="glossary-alphaproof"></a>**[AlphaProof](#glossary-alphaproof)**: A system that generates proofs verified by [Lean](#glossary-lean). [36](#ref-36)
- <a id="glossary-lean"></a>**[Lean](#glossary-lean)**: A [proof assistant](#glossary-proof-assistant) used for formal mathematics and program verification. [36](#ref-36)
- <a id="glossary-decidability"></a>**[Decidability](#glossary-decidability)**: Whether a property can be determined by a terminating algorithm.
- <a id="glossary-pascal"></a>**[Pascal](#glossary-pascal)**: A language designed to encourage structured programming. [93](#ref-93)
- <a id="glossary-ml"></a>**[ML](#glossary-ml)**: A family of functional languages with strong static typing. [95](#ref-95)
- <a id="glossary-miranda"></a>**[Miranda](#glossary-miranda)**: A non-strict [functional language](#glossary-functional-languages) that influenced [Haskell](#glossary-haskell). [96](#ref-96)
- <a id="glossary-cpp"></a>**[C++](#glossary-cpp)**: A systems language extending [C](#glossary-c) with object-oriented and generic features. [97](#ref-97)
- <a id="glossary-rust"></a>**[Rust](#glossary-rust)**: A language emphasizing memory safety and strict compile-time checks. [22](#ref-22)
- <a id="glossary-ross"></a>**[ROSS Intelligence](#glossary-ross)**: A legal AI company involved in litigation over training data. [99](#ref-99)
- <a id="glossary-github"></a>**[GitHub](#glossary-github)**: A platform for hosting and collaborating on code. [106](#ref-106)
- <a id="glossary-copilot"></a>**[GitHub Copilot](#glossary-copilot)**: A code assistant product powered by [LLMs](#glossary-llm). [100](#ref-100)
- <a id="glossary-openai"></a>**[OpenAI](#glossary-openai)**: An AI research and product company. [107](#ref-107)
- <a id="glossary-chatgpt"></a>**[ChatGPT](#glossary-chatgpt)**: A conversational [LLM](#glossary-llm) product by [OpenAI](#glossary-openai). [101](#ref-101)
- <a id="glossary-fda"></a>**[FDA](#glossary-fda)**: The U.S. Food and Drug Administration, which clears medical AI devices. [102](#ref-102)
- <a id="glossary-adt"></a>**[ADT](#glossary-adt) (Algebraic Data Type)**: Types built from sums and products in a [type system](#glossary-type-system) to make invalid states unrepresentable.
- <a id="glossary-anthropic"></a>**[Anthropic](#glossary-anthropic)**: An AI company behind the Model Context Protocol. [108](#ref-108)
- <a id="glossary-compositional-verification"></a>**[Compositional verification](#glossary-compositional-verification)**: Proof by composing verified components.
- <a id="glossary-conformance-test"></a>**[Conformance test](#glossary-conformance-test)**: A test that checks behaviour against a specification.
- <a id="glossary-deepmind"></a>**[DeepMind](#glossary-deepmind)**: An AI research lab known for [AlphaGo](#glossary-alphago) and [AlphaZero](#glossary-alphazero). [109](#ref-109)
- <a id="glossary-thomson-reuters"></a>**[Thomson Reuters](#glossary-thomson-reuters)**: A publisher and information services company involved in ROSS litigation. [99](#ref-99)
- <a id="glossary-tlc"></a>**[TLC](#glossary-tlc)**: The [TLA+](#glossary-tla) [model checker](#glossary-model-checker) that explores state spaces and checks invariants. [39](#ref-39)
- <a id="glossary-totality"></a>**[Totality](#glossary-totality)**: A function produces an output for every possible input.


## References

1. <a id="ref-1"></a> [1] Stanford HAI / RegLab report (2024) and arXiv:2401.01301. https://hai.stanford.edu/news/hallucinating-law-legal-mistakes-large-language-models-are-pervasive; https://arxiv.org/abs/2401.01301.

2. <a id="ref-2"></a> [2] Gulshan et al., "Development and Validation of a Deep Learning Algorithm for Detection of Diabetic Retinopathy," JAMA (2016). https://doi.org/10.1001/jama.2016.17216.

3. <a id="ref-3"></a> [3] Yang et al., "DeepCrack: A Deep Hierarchical Feature Learning Architecture for Crack Segmentation" (2019). https://doi.org/10.1016/j.neucom.2019.01.036.

4. <a id="ref-4"></a> [4] Russell, *The Principles of Mathematics* (1903). https://archive.org/details/principlesofmath0000russ.

5. <a id="ref-5"></a> [5] Gödel (1931), *Monatshefte fuer Mathematik*. https://doi.org/10.1007/BF01700692.

6. <a id="ref-6"></a> [6] Hofstadter, *Gödel, Escher, Bach* (Basic Books, 1979). https://archive.org/details/gdelescherbach00hofs.

7. <a id="ref-7"></a> [7] Turing (1936), "On Computable Numbers." https://www.cs.virginia.edu/~robins/Turing_Paper_1936.pdf.

8. <a id="ref-8"></a> [8] Report of the Royal Commission on the Quebec Bridge collapse (Government of Canada). https://publications.gc.ca/site/eng/9.827964/publication.html.

9. <a id="ref-9"></a> [9] Leveson & Turner, "An Investigation of the Therac-25 Accidents," *IEEE Computer* (1993). https://doi.org/10.1109/MC.1993.274940.

10. <a id="ref-10"></a> [10] Leveson, "Therac-25 Accidents: An Updated Version of the Original Accident Investigation Paper" (from *Safeware*). http://sunnyday.mit.edu/papers/therac.pdf.

11. <a id="ref-11"></a> [11] Edelman, "The Pentium(R) floating point division bug" (1995). http://www-math.mit.edu/~edelman/homepage/papers/pentiumbug.pdf.

12. <a id="ref-12"></a> [12] Ariane 5 Flight 501 Failure Report. https://www.ima.umn.edu/~arnold/disasters/ariane5rep.html.

13. <a id="ref-13"></a> [13] Gleick, "A Bug and a Crash" (NYT Magazine, archived), noting ESA's decade-long €7B Ariane 5 program and four uninsured scientific satellites. https://web.archive.org/web/20120420204657/http://www.around.com/ariane.html.

14. <a id="ref-14"></a> [14] NHTSA/NASA report on Toyota ETC (2011). https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/811361.

15. <a id="ref-15"></a> [15] NHTSA/NASA report on Toyota ETC; MISRA C. https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/811361; https://www.misra.org.uk/.

16. <a id="ref-16"></a> [16] Backus et al., "The FORTRAN Automatic Coding System" (1957); CODASYL COBOL Report (Apr 1960). https://softwarepreservation.computerhistory.org/FORTRAN/paper/BackusEtAl-FortranAutomaticCodingSystem-1957.pdf; https://archive.org/download/bitsavers_codasylCOB_6843924/COBOL_Report_Apr60_text.pdf.

17. <a id="ref-17"></a> [17] Lamport, Shostak, Pease, "The Byzantine Generals Problem" (1982). https://doi.org/10.1145/357172.357176.

18. <a id="ref-18"></a> [18] TLA+ overview; Dynamo: Amazon's Highly Available Key-value Store; Amazon S3 user guide. https://lamport.azurewebsites.net/tla/tla.html; https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf; https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html.

19. <a id="ref-19"></a> [19] CompCert project; seL4 SOSP 2009. https://compcert.inria.fr/; https://sel4.systems/publications/sel4-sosp09.pdf.

20. <a id="ref-20"></a> [20] Isabelle/HOL overview and documentation. https://www.cl.cam.ac.uk/research/hvg/Isabelle/.

21. <a id="ref-21"></a> [21] Stone, *The Everything Store* (Little, Brown, 2013). https://books.google.com/books?vid=ISBN9780316219266.

22. <a id="ref-22"></a> [22] Verification infrastructure before [LLMs](#glossary-llm) (SQL, Haskell, Coq, Rust, TLA+). https://www.iso.org/standard/63555.html; https://www.haskell.org/; https://coq.inria.fr/; https://www.rust-lang.org/; https://lamport.azurewebsites.net/tla/tla.html.

23. <a id="ref-23"></a> [23] Z3 Theorem Prover. https://z3prover.github.io/.

24. <a id="ref-24"></a> [24] SMT-LIB standard and resources. https://smt-lib.org/.

25. <a id="ref-25"></a> [25] NVIDIA company overview. https://www.nvidia.com/en-us/about-nvidia/.

26. <a id="ref-26"></a> [26] Hinton and Salakhutdinov, "Reducing the Dimensionality of Data with Neural Networks," *Science* (2006). https://doi.org/10.1126/science.1127647.

27. <a id="ref-27"></a> [27] CUDA Toolkit archive (release history). https://developer.nvidia.com/cuda-toolkit-archive.

28. <a id="ref-28"></a> [28] Vaswani et al., "Attention Is All You Need" (2017). https://doi.org/10.48550/arXiv.1706.03762.

29. <a id="ref-29"></a> [29] Sutton & Barto, *Reinforcement Learning: An Introduction* (MIT Press, 2nd ed. 2018). https://mitpress.mit.edu/9780262039246/reinforcement-learning/.

30. <a id="ref-30"></a> [30] Dwarkesh Patel interview with Richard Sutton (transcript), "Richard Sutton – Father of RL thinks [LLMs](#glossary-llm) are a dead end" (2024). https://www.dwarkesh.com/p/richard-sutton.

31. <a id="ref-31"></a> [31] Silver et al., "Mastering the game of Go with deep neural networks and tree search," *Nature* (2016). https://doi.org/10.1038/nature16961.

32. <a id="ref-32"></a> [32] AlphaZero arXiv preprint (2017); *Science* (2018). https://arxiv.org/abs/1712.01815; https://doi.org/10.1126/science.aar6404.

33. <a id="ref-33"></a> [33] HumanEval; AlphaCode; DIN-SQL. https://doi.org/10.48550/arXiv.2107.03374; https://doi.org/10.48550/arXiv.2203.07814; https://doi.org/10.48550/arXiv.2304.11015.

34. <a id="ref-34"></a> [34] HILBERT / PutnamBench results. https://doi.org/10.48550/arXiv.2509.22819.

35. <a id="ref-35"></a> [35] Model Context Protocol specification repository. https://github.com/modelcontextprotocol/modelcontextprotocol.

36. <a id="ref-36"></a> [36] AlphaProof announcement; AlphaGeometry2 technical report; Lean project. https://deepmind.google/blog/ai-solves-imo-problems-at-silver-medal-level/; https://arxiv.org/abs/2502.03544; https://leanprover.github.io/.

37. <a id="ref-37"></a> [37] Esteva et al., "Dermatologist-level classification of skin cancer," *Nature* (2017). https://doi.org/10.1038/nature21056.

38. <a id="ref-38"></a> [38] Ji et al., "Survey of Hallucination in Natural Language Generation," *ACM Computing Surveys* (2023). https://doi.org/10.1145/3571730.

39. <a id="ref-39"></a> [39] Lamport, "TLA+ Tools." https://lamport.azurewebsites.net/tla/tools.html.

40. <a id="ref-40"></a> [40] SPARK Reference Manual, Introduction. https://docs.adacore.com/spark2014-docs/html/lrm/introduction.html.

41. <a id="ref-41"></a> [41] Du Bois et al., "To the Nations of the World" (1900). https://doi.org/10.2307/3012500.

42. <a id="ref-42"></a> [42] Natives Land Act of 1913 overview, South African History Online. https://www.sahistory.org.za/article/natives-land-act-1913.

43. <a id="ref-43"></a> [43] Disorders Inquiry Committee, *Report* (1919-1920). https://archive.org/details/disordersinquiry00unse.

44. <a id="ref-44"></a> [44] New York Times, "Chinese Students Riot in Peking" (May 5, 1919). https://timesmachine.nytimes.com/timesmachine/1919/05/05/96303931.html.

45. <a id="ref-45"></a> [45] Gandhi, Non-Cooperation Movement (1920). https://www.sfr-21.org/sources/non-cooperation.html.

46. <a id="ref-46"></a> [46] Gandhi, "Letter to Viceroy Irwin" (1930). https://indianculture.gov.in/digital-district-repository/district-repository/mahatma-gandhis-letters-lord-irwin-1930.

47. <a id="ref-47"></a> [47] Gandhi, "Quit India Speech" (1942). https://www.mkgandhi.org/speeches/qui.php.

48. <a id="ref-48"></a> [48] Nuremberg Laws (1935), German History in Documents and Images. https://ghdi.ghi-dc.org/sub_document.cfm?document_id=1523.

49. <a id="ref-49"></a> [49] USHMM collections item, "Drawing, 'In Memorial of the Warsaw Ghetto Uprising'." https://collections.ushmm.org/search/catalog/irn596952.

50. <a id="ref-50"></a> [50] Atlantic Charter (1941), Avalon Project, Yale Law School. https://avalon.law.yale.edu/wwii/atlantic.asp.

51. <a id="ref-51"></a> [51] Charter of the United Nations (1945), United Nations. https://treaties.un.org/doc/publication/ctc/uncharter.pdf.

52. <a id="ref-52"></a> [52] Charter of the International Military Tribunal (1945). https://avalon.law.yale.edu/imt/imtconst.asp.

53. <a id="ref-53"></a> [53] Universal Declaration of Human Rights (1948), United Nations. https://www.ohchr.org/sites/default/files/UDHR/Documents/UDHR_Translations/eng.pdf.

54. <a id="ref-54"></a> [54] Convention on the Prevention and Punishment of the Crime of Genocide (1948), United Nations. https://www.un.org/en/genocideprevention/documents/atrocity-crimes/Doc.1_Convention%20on%20the%20Prevention%20and%20Punishment%20of%20the%20Crime%20of%20Genocide.pdf.

55. <a id="ref-55"></a> [55] Geneva Conventions (1949), International Committee of the Red Cross. https://www.icrc.org/en/law-and-policy/geneva-conventions-and-their-commentaries.

56. <a id="ref-56"></a> [56] Indian Independence Act 1947 (UK Parliament). https://www.legislation.gov.uk/ukpga/Geo6/10-11/30/contents/enacted.

57. <a id="ref-57"></a> [57] The 1947 Partition Archive, oral histories and primary source documentation. https://www.1947partitionarchive.org/.

58. <a id="ref-58"></a> [58] BBC News, "India's partition: The dividing line." https://www.bbc.com/news/world-asia-10954095.

59. <a id="ref-59"></a> [59] UN General Assembly Resolution 1514 (1960), United Nations. https://undocs.org/A/RES/1514(XV).

60. <a id="ref-60"></a> [60] Declaration of Sentiments (1848), Library of Congress. https://www.loc.gov/item/rbcmiller001106/.

61. <a id="ref-61"></a> [61] 19th Amendment (1920), U.S. National Archives. https://www.archives.gov/milestone-documents/19th-amendment.

62. <a id="ref-62"></a> [62] Voting Rights Act of 1965, U.S. National Archives. https://www.archives.gov/milestone-documents/voting-rights-act.

63. <a id="ref-63"></a> [63] U.S. Department of Justice, "History of Federal Voting Rights Laws." https://www.justice.gov/crt/history-federal-voting-rights-laws.

64. <a id="ref-64"></a> [64] U.S. Census Bureau, "Voting and Registration in the Election of November 2022." https://www.census.gov/library/publications/2024/demo/p20-586.html.

65. <a id="ref-65"></a> [65] National Centre for Truth and Reconciliation, "Residential Schools." https://nctr.ca/education/teaching-resources/residential-schools/.

66. <a id="ref-66"></a> [66] Government of Canada, "Statement of the Government of Canada on Indian Policy (1969)." https://publications.gc.ca/site/eng/9.700112/publication.html.

67. <a id="ref-67"></a> [67] Government of Canada, "Residential Schools." https://www.rcaanc-cirnac.gc.ca/eng/1100100015576/1522907135142.

68. <a id="ref-68"></a> [68] National Centre for Truth and Reconciliation, "Missing Children and Unmarked Burials." https://nctr.ca/burials/missing-children-and-unmarked-burials/.

69. <a id="ref-69"></a> [69] King, "Letter from Birmingham Jail" (1963). https://www.csuchico.edu/iege/_assets/documents/susi-letter-from-birmingham-jail.pdf.

70. <a id="ref-70"></a> [70] Brown v. Board of Education (1954), U.S. National Archives. https://www.archives.gov/milestone-documents/brown-v-board-of-education.

71. <a id="ref-71"></a> [71] Civil Rights Act of 1964, U.S. National Archives. https://www.archives.gov/milestone-documents/civil-rights-act.

72. <a id="ref-72"></a> [72] Numan V. Bartley, *The Rise of Massive Resistance: Race and Politics in the South During the 1950s* (Louisiana State University Press, 1969).

73. <a id="ref-73"></a> [73] U.S. Department of Justice, "Investigation of Allegations Regarding the Assassination of Dr. Martin Luther King, Jr." (2000). https://www.justice.gov/crt/united-states-department-justice-investigation-allegations-regarding-assassination-dr-martin.

74. <a id="ref-74"></a> [74] The King Center, "Martin Luther King, Jr." https://thekingcenter.org/about-tkc/martin-luther-king-jr/.

75. <a id="ref-75"></a> [75] Holodomor Research and Education Consortium, "Holodomor Basic Facts." https://holodomor.ca/get-started/holodomor-basic-facts/.

76. <a id="ref-76"></a> [76] ЦСУ СССР, *Всесоюзная перепись населения 17 декабря 1926 г.* (All-Union Population Census). https://archive.org/details/perepis_naseleniia_1926.

77. <a id="ref-77"></a> [77] Law of Ukraine, "On the Holodomor of 1932-1933 in Ukraine" (2006). https://zakon.rada.gov.ua/laws/show/376-16?lang=en.

78. <a id="ref-78"></a> [78] Freedom Charter (1955), African National Congress. https://www.anc1912.org.za/freedom-charter/.

79. <a id="ref-79"></a> [79] Mandela, "Statement from the Dock" (1964). https://www.historyplace.com/speeches/mandela.htm.

80. <a id="ref-80"></a> [80] Nelson Mandela Foundation, "Biography." https://www.nelsonmandela.org/content/page/biography.

81. <a id="ref-81"></a> [81] UN Declaration on the Rights of Indigenous Peoples (2007), United Nations. https://undocs.org/A/RES/61/295.

82. <a id="ref-82"></a> [82] Americans with Disabilities Act (1990), ADA.gov. https://www.ada.gov/law-and-regs/ada/.

83. <a id="ref-83"></a> [83] Obergefell v. Hodges (2015), Legal Information Institute. https://www.law.cornell.edu/supremecourt/text/14-556.

84. <a id="ref-84"></a> [84] Online Safety Amendment (Social Media Minimum Age) Act 2024 (Australia). https://www.legislation.gov.au/C2024A00127/asmade/text.

85. <a id="ref-85"></a> [85] McLuhan, *Understanding Media: The Extensions of Man* (McGraw-Hill, 1964). https://archive.org/details/understandingmed00mclu.

86. <a id="ref-86"></a> [86] Clarke, "Extra-Terrestrial Relays: Can Rocket Stations Give World-Wide Radio Coverage?" *Wireless World* (Oct 1945). https://www.rfcafe.com/references/magazine-articles/extra-terrestrial-relays-arthur-c-clarke-oct-1945-wireless-world.htm.

87. <a id="ref-87"></a> [87] Winner, *The Whale and the Reactor* (University of Chicago Press, 1986), ISBN 9780226902111. https://archive.org/details/whalereactorsear00winn.

88. <a id="ref-88"></a> [88] Harari, *Sapiens* (Harper, 2015), ISBN 9780062316097. https://www.ynharari.com/book/sapiens/.

89. <a id="ref-89"></a> [89] Eubanks, *Automating Inequality* (St. Martin's Press, 2018), ISBN 9781250074317. https://www.c-span.org/video/?444334-1/automating-inequality.

90. <a id="ref-90"></a> [90] Benjamin, *Race After Technology* (Polity, 2019), ISBN 9780745338667. https://www.c-span.org/video/?466564-1/race-technology.

91. <a id="ref-91"></a> [91] Wilkes, Wheeler, Gill, *The Preparation of Programs for an Electronic Digital Computer* (1951). https://archive.org/details/preparationofpro00wilk.

92. <a id="ref-92"></a> [92] European Convention on Human Rights (1950), Council of Europe. https://rm.coe.int/1680063776.

93. <a id="ref-93"></a> [93] Jensen and Wirth, *Pascal User Manual and Report* (1974). https://archive.org/details/pascalusermanual00jens.

94. <a id="ref-94"></a> [94] Ritchie, "C Reference Manual" (1974). https://archive.org/details/crefman.

95. <a id="ref-95"></a> [95] Milner et al., *The Definition of Standard ML* (1997). https://smlfamily.github.io/sml97-defn.pdf.

96. <a id="ref-96"></a> [96] Turner, Miranda language overview. https://www.cs.kent.ac.uk/people/staff/dat/miranda/.

97. <a id="ref-97"></a> [97] Stroustrup, *The C++ Programming Language* (1st ed., 1985). https://www.stroustrup.com/1st.html.

98. <a id="ref-98"></a> [98] Krizhevsky, Sutskever, Hinton, "ImageNet Classification with Deep Convolutional Neural Networks," *NeurIPS* (2012). https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.

99. <a id="ref-99"></a> [99] Thomson Reuters Enterprise Centre GmbH v. ROSS Intelligence Inc., D. Del. docket. https://www.courtlistener.com/docket/61382368/thomson-reuters-enterprise-centre-gmbh-v-ross-intelligence-inc/.

100. <a id="ref-100"></a> [100] GitHub Copilot product page. https://github.com/features/copilot.

101. <a id="ref-101"></a> [101] OpenAI, "ChatGPT." https://openai.com/chatgpt.

102. <a id="ref-102"></a> [102] FDA, "Artificial Intelligence and Machine Learning (AI/ML)-Enabled Medical Devices." https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-aiml-enabled-medical-devices.

103. <a id="ref-103"></a> [103] Mata v. Avianca, Inc., S.D.N.Y. docket (CourtListener). https://www.courtlistener.com/docket/63107798/mata-v-avianca-inc/.

104. <a id="ref-104"></a> [104] Intel, "Company Overview." https://www.intel.com/content/www/us/en/company-overview/company-overview.html.

105. <a id="ref-105"></a> [105] European Space Agency, "About ESA." https://www.esa.int/About_Us.

106. <a id="ref-106"></a> [106] GitHub, "About." https://github.com/about.

107. <a id="ref-107"></a> [107] OpenAI, "About." https://openai.com/about.

108. <a id="ref-108"></a> [108] Anthropic, "Anthropic." https://www.anthropic.com/.

109. <a id="ref-109"></a> [109] DeepMind, "About DeepMind." https://deepmind.google/about/.
