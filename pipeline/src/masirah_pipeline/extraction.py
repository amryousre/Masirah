"""Extracting a structured profile from a CV's text (FR-008), through the provider port.

The instructions and the output schema live here, not in an adapter, so every provider is asked
the same thing and the prompt version names exactly what was asked (AI-02). The conventions in
the instructions are the corpus labels' (tests/fixtures/cvs/README.md), which the accuracy gate
scores against.
"""

from dataclasses import dataclass

from masirah_pipeline.domain.profile import (
    PROFILE_SCHEMA,
    MalformedProfileError,
    Profile,
    profile_from_output,
)
from masirah_pipeline.ports.model_provider import (
    MalformedOutputError,
    StructuredModel,
    StructuredRequest,
    StructuredResponse,
)

PROMPT_VERSION = "extract-profile/1"
# Room for a long CV's profile, and for a reasoning model's thinking, which counts as output.
MAX_OUTPUT_TOKENS = 16_000

INSTRUCTIONS = """\
You extract a candidate's profile from the text of their CV for a recruiter. The text was taken \
from a PDF or Word file: columns are read one after another, pieces of one line are separated by \
tabs, and the CV may be in Arabic, English or both.

Fill every field from what the CV states. Never guess, infer or calculate a value; when the CV \
does not give it, use null, or an empty list for a list.

Copy each value as the CV writes it, in the CV's own language and spelling, typos included. Do \
not translate, expand abbreviations or correct mistakes.

Field by field:
- name: the candidate's full name.
- emails: every email address of the candidate.
- phones: every phone number of the candidate, in E.164 form with ASCII digits and no spaces. \
Write an Egyptian mobile such as 0100 123 4567 as +201001234567, convert Arabic-Indic digits, and \
use the country code the CV gives or the number's own national format implies.
- location: the city the candidate lives in, without the country or district. null if not stated.
- years_of_experience: only a figure the CV states, such as "6 years of experience". Never \
compute it from dates.
- employment: every paid role, including traineeships and internships, but not volunteering and \
not projects. employer and title are separate: in "Sales Executive at Nile Pharma" the employer \
is Nile Pharma. start and end are YYYY-MM when the CV gives the month and YYYY when it gives only \
the year. end is "present" for a current role, and null when the CV does not say.
- education: degrees and diplomas only. Courses, online programmes and training go in \
certifications instead, even when the CV lists them under education. Dates as for employment.
- skills: the technical skills the CV lists as skills, one item each, as written. Not soft skills \
such as teamwork, communication or fast learning.
- languages: each language and the level the CV gives for it, both as written.
- certifications: certificates, courses and training programmes, with the issuer when the CV \
names one.
"""


@dataclass(frozen=True)
class ExtractedProfile:
    profile: Profile
    response: StructuredResponse


def extract_profile(model: StructuredModel, text: str) -> ExtractedProfile:
    if not text.strip():
        raise ValueError("the document has no text to extract from")
    request = StructuredRequest(
        instructions=INSTRUCTIONS,
        content=text,
        schema_name="cv_profile",
        schema=PROFILE_SCHEMA,
        prompt_version=PROMPT_VERSION,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    response = model.complete(request)
    try:
        profile = profile_from_output(response.output)
    except MalformedProfileError as error:
        raise MalformedOutputError(str(error), cost_egp=response.cost_egp) from error
    return ExtractedProfile(profile, response)
