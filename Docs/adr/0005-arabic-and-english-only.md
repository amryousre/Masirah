# Arabic and English only for version 1.0

CV intake and parsing are scoped to Arabic, English, and documents mixing the two, with no language
pre-selection required of the user. Other languages are out of scope for version 1.0. A CV that is
neither Arabic nor English is flagged rather than parsed and presented as though it were understood.

The corpus behind the accuracy gates covers Arabic and English, and those gates, 95 percent field
accuracy on native PDFs and 85 percent on photographs, are what version 1.0 is measured against.
Scoping intake to the same two languages keeps what is promised and what is tested identical.

## Considered and rejected: accept any language, guarantee two

The alternative was to accept CVs in any language while measuring only Arabic and English, leaving
everything else best-effort and protected by the confidence threshold and the manual review queue.

Arguments for it, recorded because they will be raised again: Egyptian employers do receive
applications from Sudanese, Syrian, Indian and Filipino candidates, so a strict limit turns away
real applicants to real Egyptian jobs. Text extraction is language-agnostic and the models are
multilingual, so most other languages would have parsed correctly with no extra code. Rejecting a
non-Arabic, non-English CV actually costs more to build than accepting it, because the system must
first detect the language in order to turn it away.

It was rejected in favour of a narrower, fully tested version 1.0. The founder is building solo and
part-time, and a smaller surface that is entirely covered by the release gate is worth more at this
stage than a broader surface that is partly unmeasured.

## Consequences

Language detection becomes a requirement rather than an optimisation, because the flagging
behaviour depends on it. This is work that the accept-everything option would not have needed.

The review queue gains a second reason for a document to land in it, alongside low parsing
confidence: an unsupported language. Those two cases must be distinguishable to the user, since one
means try again with a better scan and the other means this is not supported yet.

Expanding the supported set later is a matter of sourcing and labelling a corpus for the new
language and then widening the intake rule. Nothing in the architecture prevents it. That expansion
is recorded as open in OQ-09.
