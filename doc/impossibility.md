                      Musings on the Impossible
                             Alexey Radul
                           January 22, 2015

In a probabilistic programming language, there are (at least) four
meanings for the phrase "this situation is impossible":

- If this happens, it indicates a bug in the implementation of Venture

- If this happens, it indicates a bug in the user program [^synthesis]

- The probability of this event in the model is exactly zero (but that
  doesn't mean that it's necessarily a program error to consider it)

- The probability of this event in the model is approximately zero
  (but might not be zero because the probabilities are computed
  inexactly)

[^synthesis]: Models that involve program synthesis may wish to treat
buggy synthesized programs as probability-zero events rather than as
bugs in the synthesizer.

The first of these should be aggressively reported to developers, and
should eventually become rare enough that users can just see an
incomprehensible dump and a request to file a bug report.
Operationally, the "assert" statement seems reasonable; or throwing an
exception that is not intended for user consumption.  Standard Python
exceptions emanating from the implementation have that effect.

The second of these should result in a polite exception, and an
indication of where the problem was (both in the model and in the
inference program, as applicable).  In the interactive console, such
an error ideally would not leave the system in a broken state, but
currently it typically does (partially-regenerated trace; no way to
recover).  It would also be nice to detect some classes of such
problems statically.  One subtlety: standard Python exceptions emanating from
user-supplied foreign SPs should be treated as bugs in the user
program, not the implementation (except in cases where the
implementation messed up their calling convention).

I am consistently of two minds about how to treat the last two
classes, namely concievable events that are supposed to have
probability zero.  Possible stances are:

- "You should arrange your program such that they are never even
  contemplated".
  - Operationally, this means escalating to "bug in user program".
  - I think this is untenable, especially in the face of
    "approximately zero" probabilities.

- "Probability-zero events have no inspectable structure, except
  for the fact of having probability zero".
  - Semantically, this at least permits rejecting transitions (from
    possible states) to impossible states, and filtering out
    impossible particles.
  - Operationally, this permits leaving the Trace representing that
    event in a somewhat bad state, but not so bad that it can't be
    unrolled (e.g., for continued in-place likelihood weighting).

- "Probability-zero events are fine; you just have no quality metric
  until you enter a possible state".
  - Operationally, this essentially requires Venture to become a
    deterministic-constraint-satisfaction system too.  Which, with
    inference programming, may be fine; or may not.

As of this writing, the actual implementation is somewhere between the
"bug" and "no-structure" stances.  One reason for this is that
implementing the "no-structure" stance by catching exceptions at the
outer level basically doesn't work, because

- one has to be very careful not to catch exceptions that indicate
  actual bugs.

- the trace will typically be in an unrecoverable state after an
  exception, if it is permitted to propagate through regen.

The former problem can be mostly solved by carefully segregating
exception hierarchies, except for the issue of provenance of Python
exceptions that may come from the implementation or from foreign SPs.
- This might be fixable by catching exceptions around SP method calls,
  especially if that is done only for foreign SPs and not builtins.

The latter problem can be fixed by moving to pure-functional traces by
default (possibly leaving in-place mutating ones as an option for
advanced users that are willing to sacrifice error recovery), or by
essentially implementing a custom condition system in the interpreter
that unrolls failed operations in order to leave the trace in a
recoverable state.  This is an instance of the famous PC lusering problem.
- Maybe some clever hack with marking elements of an OmegaDB as "used"
  would make the latter relatively easy.

Specific Case: Initialization
-----------------------------

The specific case prompting the above general worries is what to do
when initialization from the prior produces a state whose likelihood
is zero.  Options include:

- Gronking

- Automatically patching it up by trying again repeatedly

- Tolerating the impossibility (and maybe bombing out if the user
  tries to start an MH transition from an impossible state)

  - In this case, can offer "try again repeatedly" as an inference SP

To address the above design choice, Taylor proposed the following
taxonomy of badness:

- Not possible at all
  - This case is not causing any design heartache.

- Unlikely enough that one would miss it in testing but hit it in the
  wild
  - In this case, patching it by trying again is almost certainly the
    right thing

- Likely enough that one would hit it in testing, but unlikely enough
  that retrying will fix it acceptably

- So nearly inevitable that retrying will not fix it
  - In this case we can say your model is pretty hosed anyway.

Decision:

- incorporate will just tolerate impossible states, setting their
  relative log weight to -infinity

- likelihood weighting and particle filtering, for example, will just
  work (unless all the particles are impossible; in which case I
  choose the philosophy of treating all impossible situations as
  equally impossible).

- mh and co should already reject transitions to impossible states

- Can make mh and co throw exceptions when starting at impossible states

- add bogo_possibilize, which keeps trying the prior until it finds a
  possible state

Specific Case: Proposals that violate invariants
------------------------------------------------

For example, what should be done if some variable must be positive,
but some proposal program wants to try setting a negative value for
it?  There are places in the implementation (of specific SPs?) that
gronk out when such an invariant is violated.  While all proposals
were made by resimulation regen only, it was the case that an SP could
maintain output invariants for itself -- the system effectively
guaranteed that the value in a node would always be one that could
have been generated by the operator of that node given some arguments
(except in situations where the operator might change, which we have
not encountered very often in our practice).  However, some proposal
programs, like gradient ascent or HMC, violate this assumption.

Perhaps we can move the whole codebase to a policy of "an assessor may
never fail, but here's a decorator that makes it return -inf instead
of throwing exceptions".  It's trickier for simulators, because there
is no natural sentinel value by which a simulator could politely
complain that its inputs are impossible; and yet, a proposer like HMC
could (transiently) violate any such constraints even if the user
program was otherwise written to obey them (e.g., non-negativity of
the degrees of freedom parameter of the student t distribution).

Problem: Catching exceptions and converting them to successful
execution that asserts the impossiblity of the inputs (or outputs, for
an assessor) is a risky catchall solution, because some exceptions
would indicate actual programming errors in the SP, and others would
indicate exceptional external circumstances (e.g., "out of file
descriptors") that call for a different response than "proceed with
inference treating something as not possible in the model".

Does this call for writing a little SP testing package that prods an
SP for a while and reports the exceptions it raises, as a way of
helping users debug programming errors in them?
