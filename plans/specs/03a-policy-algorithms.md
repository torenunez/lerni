# Explore Safe Slice — Normative Policy Algorithm Appendix

## Purpose

Make the first English-language prototype deterministic across implementations.

This appendix defines:

- normalization;
- tokenization;
- input rule precedence;
- best-effort redaction patterns;
- output rule precedence;
- sentence counting;
- grounding term checks;
- numeric checks;
- markup handling;
- golden fixtures.

It is deliberately narrow. It does not constitute comprehensive PII detection, crisis detection, moderation, or multilingual safety.

## Supported locale

The first policy profile supports reviewed `en-US` lesson content only.

If lesson locale is unsupported:

- tutor generation is disabled;
- authored deterministic lesson/check content remains available if separately reviewed;
- microphone is disabled unless a policy profile for the transcript language exists;
- parent sees the limitation.

Do not silently apply the English phrase policy to another language.

## String normalization

Define:

```python
class PolicyNormalizationError(Exception):
    reason: PolicyReason


def normalize_policy_text(text: str, *, max_chars: int) -> str:
    ...
```

`PolicyNormalizationError` is constructed from the fixed reason enum only, stores/prints no input, and is mapped by `SafetyPolicy` to a fixed block. Raw or normalized length failure uses `INPUT_TOO_LONG`; remaining `Cf` uses `UNSAFE_UNICODE`.

Algorithm:

1. Require `type(text) is str`.
2. Reject if raw character count exceeds the applicable limit.
3. Normalize Unicode with NFKC.
4. Replace `\r\n` and `\r` with `\n`.
5. Replace tab with one ASCII space.
6. Remove Unicode category `Cc` except newline.
7. If any Unicode category `Cf` remains, raise the fixed typed failure before returning text.
8. Replace curly apostrophes with `'`.
9. Replace Unicode dash variants with ASCII `-`.
10. Strip each line.
11. Collapse runs of ASCII/Unicode whitespace other than newline to one space.
12. Collapse three or more newlines to two.
13. Strip the complete value.
14. Recheck normalized character limit.

For the first `en-US` profile, any remaining Unicode category `Cf` character after NFKC is blocked with `UNSAFE_UNICODE`. This includes bidirectional controls and:

```text
U+061C
U+200E
U+200F
U+202A–U+202E
U+2066–U+2069
U+00AD
U+200B
U+2060
U+FEFF
```

There is no `Cf` allowlist in the first profile. A future locale profile must define and test one explicitly.

## Tokenization

First lowercase with `str.casefold()`.

Token regex:

```python
TOKEN_RE = re.compile(
    r"[a-z0-9]+(?:['-][a-z0-9]+)*",
    re.ASCII,
)
```

This restriction is intentional for the first English lesson.

Bounded phrase matching tokenizes normalized/casefolded text and the configured phrase with `TOKEN_RE`, then requires the phrase-token tuple to occur as one contiguous token subsequence. It never uses raw substring matching; for example, `secret` does not match `secretary`. Phrase lists below use this algorithm unless an explicit regex is shown.

Scope check:

1. If the entire normalized/casefolded input is in `allowed_short_replies`, pass scope.
2. Otherwise tokenize.
3. Pass scope if at least one token exactly matches a current `scope_term`.
4. Otherwise redirect as out of scope.

Scope terms are reviewed lesson content, not generated dynamically.

## Stop words and significant terms

Use this exact first-slice set:

```text
a
an
and
are
as
at
be
because
but
by
can
do
does
for
from
has
have
how
i
if
in
is
it
its
of
on
or
so
that
the
their
then
there
they
this
to
was
we
what
when
which
who
why
will
with
you
your
```

A significant term is:

- a numeric token; or
- an alphabetic/alphanumeric token of at least three characters not in the stop-word set.

For each tutor sentence, compute significant terms for:

- the sentence;
- the union of canonical and child text for every cited fact.

Require a non-empty intersection. This is lexical traceability only.

## Number grammar

Extract numeric tokens with:

```python
NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"[+-]?"
    r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d+)?"
    r"%?"
    r"(?![A-Za-z0-9_])",
    re.ASCII,
)
```

Normalization:

1. After NFKC, map every Unicode `Nd` character with `unicodedata.decimal()` to its ASCII digit; reject any remaining character for which `isdigit()` or `isnumeric()` is true but that is not ASCII `0`–`9`.
2. Remove commas inside matched digits.
3. Preserve leading sign.
4. For decimal forms:
   - remove trailing zeros;
   - remove trailing decimal point;
   - normalize `-0` to `0`.
5. Preserve `%`.

Hyphenated `0-60` produces `0` and `-60` under the raw grammar; before extraction, treat a hyphen between two unsigned digit runs as a separator, so the values become `0` and `60`.

Every normalized number must appear in `allowed_numbers` of at least one fact cited by that sentence.

After all non-overlapping regex matches, every ASCII digit position in the sentence must be covered by exactly one match. A digit adjacent to a letter/underscore or otherwise left unmatched (for example `999mph`) rejects the sentence rather than bypassing numeric grounding.

No derived arithmetic is accepted unless the exact output number is explicitly allowed.

## Sentence counting

Generated drafts already contain structured `TutorSentence` records. The application:

- counts those records as the primary sentence count;
- rejects an empty sentence;
- rejects any one record containing more than one terminal-sentence boundary.

Terminal boundary regex:

```python
SENTENCE_BOUNDARY_RE = re.compile(
    r"[.!?]+(?:[\"')\]]+)?(?=\s|$)",
    re.ASCII,
)
```

A sentence record may end with one boundary. A second boundary before the end rejects the draft. Newline inside a sentence record is rejected.

This avoids locale-dependent NLP tokenizers.

## Literal formula/markup prefixes

For spreadsheet imports, a cell whose first non-whitespace character is one of:

```text
=
+
-
@
```

is rejected when that field is free text, unless the field-specific grammar explicitly permits a leading minus for a numeric value.

CSV export neutralizes such parent notes by prefixing a single apostrophe in the exported spreadsheet-facing copy while preserving the local JSON value. The export manifest records `spreadsheet_neutralized=true`.

CSV cannot prove whether a spreadsheet formula was evaluated before export. The importer claims only literal-prefix rejection and requires an operator attestation that the source workbook is formula-free.

## Best-effort pattern set

Compile case-insensitively after normalization.

### Email

```python
r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b"
```

### URL and link

```python
r"\b(?:https?://|www\.)\S+"
r"!\?*\[[^\]\n]{0,200}\]\([^)\n]{1,500}\)"
```

### Phone-like value

Candidate:

```python
r"(?<!\w)(?:\+?\d[\d(). -]{5,}\d)(?!\w)"
```

Redact only if the candidate contains 7–15 digits.

### IPv4

Match four one-to-three digit groups and validate each integer is 0–255.

### Explicit name declaration

```python
r"\b(?:my name is|call me|i am called|i'm called)\s+"
r"([a-z][a-z' -]{0,39})"
r"(?=$|[,.!?;\n])"
```

Replace capture only.

### Address/location/school disclosure

```python
r"\bmy address is\s+[^.!?\n]{1,100}"
r"\bi live (?:at|in|near)\s+[^.!?\n]{1,100}"
r"\bmy school is\s+[^.!?\n]{1,100}"
r"\bi go to\s+[^.!?\n]{1,100}\bschool\b"
```

Map `my address is` and `i live at` matches to `RedactionKind.ADDRESS`; map `i live in` and `i live near` to `RedactionKind.LOCATION`; map both school patterns to `RedactionKind.SCHOOL`. Apply the first matching pattern in the displayed order and replace the complete matched disclosure with that kind’s exact fixed marker.

### Age disclosure

```python
r"\bi am\s+([0-9]{1,2})\s+years? old\b"
r"\bi'm\s+([0-9]{1,2})\b"
```

The second pattern is applied only when the value is 3–17.

### Explicit credential

```python
r"\b(?:password|passcode|api[ _-]?key|access[ _-]?token|secret)\s*[:=]\s*\S+"
r"\bbearer\s+[a-z0-9._~+/-]{8,}\b"
r"-----BEGIN [A-Z ]+PRIVATE KEY-----"
```

High-entropy-like candidate:

```python
r"\b[A-Za-z0-9_-]{32,}\b"
```

Treat it as credential-like only when it contains at least three of:

- lowercase;
- uppercase;
- digit;
- `_` or `-`.

## Serious-distress first-slice phrase set

After normalization/casefolding, escalate on these bounded phrases:

```text
i want to die
i want to kill myself
i am going to kill myself
i want to hurt myself
i am going to hurt myself
someone is hurting me
someone hurt me
i am in danger
i can't breathe
i cannot breathe
there is a fire
call the police
call an ambulance
```

Also match:

```python
r"\b(?:going to|want to|might)\s+(?:die|kill myself|hurt myself)\b"
```

The fixed response tells the learner to stop and get the supervising adult now. It does not claim that help was contacted.

False positives and missed phrasings are expected. Parent supervision remains mandatory.

## Bounded harmful or age-inappropriate phrases

Redirect input and reject generated output on contiguous phrase matches:

```text
how can i hurt someone
how do i kill someone
use a car to hurt someone
run someone over
show me how to make a weapon
show me how to make a bomb
help me hide a weapon
help me buy drugs
sexual picture of a child
keep abuse secret
```

Also match normalized/casefolded:

```python
r"\b(?:how (?:can|do) i|tell me how to|show me how to)\s+(?:hurt|kill|attack|shoot|stab|poison|run over)\b"
r"\b(?:make|build|hide)\s+(?:a\s+)?(?:bomb|weapon)\b"
r"\b(?:buy|sell|hide)\s+(?:illegal\s+)?drugs?\b"
```

Serious-distress rules retain higher precedence. These bounded patterns are a minimum deterministic backstop, not a complete harm classifier. Generated tutor use additionally requires the qualified harm gate and reviewed adversarial fixture set from the tutor plan.

## Input relationship/secrecy phrases

Redirect on:

```text
keep this secret
don't tell my parent
do not tell my parent
don't tell my parents
do not tell my parents
be my best friend
can you be my friend
will you be my friend
can we meet
where can we meet
```

Do not match generic uses of `secret` inside lesson content without one of the bounded patterns.

Every input match in this section maps exactly to `PolicyReason.INPUT_RELATIONSHIP_OR_SECRECY`. Output-only relationship/secrecy/dependency/coercion/meeting matches below map to `PolicyReason.RELATIONSHIP_OR_SECRECY`; the two reasons are never interchanged.

## Output relationship, dependency, secrecy, and coercion phrases

Generated output is rejected with `RELATIONSHIP_OR_SECRECY` when bounded phrase matching finds:

```text
keep this secret
keep our conversation secret
our little secret
don't tell your parent
do not tell your parent
don't tell your parents
do not tell your parents
don't tell anyone
do not tell anyone
this is between us
i won't tell your parent
i will not tell your parent
i won't tell your parents
i will not tell your parents
i am your best friend
i'm your best friend
you only need me
you don't need your parent
you do not need your parent
you don't need your parents
you do not need your parents
only i understand you
trust me instead
you can trust only me
prove you trust me
if you loved me
let's meet
we should meet
meet me
come see me
come visit me
```

Also reject these normalized/casefolded regexes:

```python
r"\b(?:tell|show|send|give)\s+me\s+your\s+(?:name|address|school|phone|email|location|password)\b"
r"\bwhat(?:'s| is)\s+your\s+(?:name|address|school|phone|email|location|password)\b"
r"\b(?:let's|we should|you should|can we)\s+meet\b"
r"\b(?:talk|listen)\s+to\s+me\s+instead\s+of\s+your\s+parents?\b"
```

The personal-data solicitation regexes map to `URL_OR_CONTACT`; relationship, secrecy, dependency, coercion, and meeting patterns map to `RELATIONSHIP_OR_SECRECY`. Ordinary factual uses such as “a secret code in this example” are not blocked absent a listed phrase. This bounded policy is deliberately incomplete, and parent supervision remains required.

## Instruction-override phrases

Redirect on:

```python
r"\bignore\s+(?:all\s+|the\s+|your\s+)?(?:previous\s+)?instructions\b"
r"\bpretend\s+(?:the\s+)?rules?\s+(?:do not|don't)\s+apply\b"
r"\bshow\s+(?:me\s+)?(?:the\s+)?(?:system|developer)\s+(?:prompt|message)\b"
r"\breveal\s+(?:the\s+)?(?:system|developer)\s+(?:prompt|message)\b"
r"\bchange\s+(?:the\s+)?correct\s+answer\b"
```

This catches common bounded forms only.

## Input precedence

Use exactly:

1. Type/raw-length failure.
2. Normalization/unsafe-Unicode failure.
3. Empty input.
4. Effective turn cap.
5. Serious distress.
6. Harmful/age-inappropriate phrase.
7. Credential or personal-data detection.
8. Relationship/secrecy phrase.
9. Instruction override.
10. Scope.
11. Allow.

Optional external input safety runs only after app allow.

If the generated-content harm gate is not currently qualified/available before a request, do not call the tutor. If its post-generation invocation times out or fails, never display that draft. In both cases use authored fallback and tell the parent that generated tutoring is unavailable.

## Output unsafe markup

Reject generated output containing:

```python
r"<[A-Za-z!/][^>\n]{0,1000}>"
r"!?\[[^\]\n]{0,200}\]\([^)\n]{1,500}\)"
r"\b(?:javascript|data|file):"
r"```"
r"`[^`\n]+`"
```

Reject any remaining Unicode `Cc`/`Cf` except ordinary newline, which generated sentence records already prohibit.

Display generated text through a plain-text/escaped component:

```python
html.escape(text, quote=True)
```

Do not pass generated text to a Markdown/HTML renderer as trusted content.

## Output precedence

1. Type/empty/character limit.
2. Sentence-record count and boundary.
3. Unsafe Unicode/control.
4. Unsafe markup/link.
5. Harmful/age-inappropriate phrase.
6. URL/contact/credential.
7. Personal-data solicitation.
8. Relationship/secrecy/dependency/coercion/request-to-meet.
9. Grounding citation/reference.
10. Significant-term traceability.
11. Allowed-number check.
12. Mandatory generated-content harm gate.
13. Allow.

The tutor service runs each stage once.

## Golden fixtures

Create the canonical installed resource `src/lerni/explore/policy_data/policy_cases_v1.toml`. Tests load that exact bounded resource through `importlib.resources`; do not maintain a second test-only copy. Runtime readiness hashes the same bytes, so a clean wheel/sdist does not depend on a source checkout.

Each case contains:

```toml
id = "stable-case-id"
direction = "input"
text = "fixed test text"
expected_action = "redirect"
expected_reason = "instruction_override"
expected_redactions = []
```

Required cases:

### Allow

- `Why?` when `why` is an allowed short reply.
- `Why does the car with less time have greater acceleration?`
- `Is 0 to 60 a time or acceleration?`

### Redact/redirect

- explicit name;
- email;
- phone;
- address;
- school;
- age;
- secret-like token;
- URL.

Each redaction fixture asserts the exact marker mapping from plan 03, including address, location, school, age, IP, URL, and secret—not only the redaction enum.

### Escalate

- each serious-distress phrase.

### Relationship/instruction

- each bounded input secrecy/relationship phrase with expected reason `input_relationship_or_secrecy`;
- each bounded harmful/age-inappropriate phrase and regex with a lesson-scope token included;
- each instruction-override regex;
- same override with `acceleration` included to prove scope cannot bypass it.

### Output reject

- each bounded output secrecy/relationship/dependency/coercion phrase with expected reason `relationship_or_secrecy`;
- each bounded harmful/age-inappropriate phrase and regex;
- each output personal-data solicitation and meeting regex;
- benign lesson use of `secret` without a bounded phrase does not trigger this rule;
- HTML tag;
- Markdown link;
- Markdown image;
- data/javascript URL;
- bidi override;
- soft hyphen, zero-width space, word joiner, and BOM;
- two sentence boundaries inside one `TutorSentence`;
- unknown fact;
- missing citation;
- unsupported number.

### Grounding allow

- one sentence citing `acceleration-definition`;
- one sentence using only allowed `0`, `4`, `8`, and `60`.

Tests iterate the fixture and assert exact action, reason, redactions, and output.

## Change control

Changing:

- a regex;
- precedence;
- stop word;
- scope token;
- phrase list;
- number grammar;
- sentence rule;
- fixed response

requires:

1. a behavior-specific failing fixture;
2. implementation update;
3. all golden fixtures green;
4. documentation update;
5. parent review before the changed policy is used in a child pilot.

## Completion criteria

- One implementation produces exact golden outcomes.
- Policy does not depend on a model/service.
- Scope cannot override higher-priority rules.
- Output markup is escaped/rejected.
- Formula-injection limitation is accurately described.
- Unsupported locales fail closed for generated/microphone paths.
- Residual false-positive/false-negative limits are visible.
