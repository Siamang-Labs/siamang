"""UIConfig — visual settings for the deployed survey."""

from __future__ import annotations

from dataclasses import dataclass

_DENSITY_VALUES = {"compact", "comfortable", "spacious"}
_FONT_PAIR_VALUES = {"serif", "sans", "mixed"}
_LOGO_POSITIONS = {"left", "right", "center"}
_QUESTION_STYLES = {"plain", "divided", "carded", "accent"}
_FONT_PRESET_VALUES = {"academic", "modern", "humanist"}
_THEME_VALUES = {"light", "dark", "system"}


# ─── Font preset definitions ─────────────────────────────────────────────────
# Each preset defines body, heading, and UI font stacks plus a Google Fonts URL.

FONT_PRESETS: dict[str, dict[str, str]] = {
    "academic": {
        "body": '"Source Serif 4", "Charter", Georgia, "Times New Roman", serif',
        "heading": '"Source Serif 4", "Charter", Georgia, serif',
        "ui": '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif',
        "google_fonts": "https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap",
    },
    "modern": {
        "body": '"Inter", "Helvetica Neue", system-ui, -apple-system, sans-serif',
        "heading": '"Inter", "Helvetica Neue", system-ui, sans-serif',
        "ui": '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif',
        "google_fonts": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    },
    "humanist": {
        "body": '"Nunito", "Segoe UI", system-ui, sans-serif',
        "heading": '"Nunito", "Segoe UI", system-ui, sans-serif',
        "ui": '"Nunito", system-ui, -apple-system, "Segoe UI", sans-serif',
        "google_fonts": "https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700&display=swap",
    },
}


@dataclass(frozen=True, slots=True)
class UIConfig:
    """Visual settings consumed by the theme + runtime adapters.

    The defaults aim for a calm, research-grade look: serif body type,
    narrow measure, single accent, comfortable spacing. Override any field
    for brand-specific surveys or pick one of the
    :data:`siamang.frontend.theme.presets.THEME_PRESETS` entries.

    Font presets:
        - ``"academic"`` — Source Serif 4 body + Inter UI (default)
        - ``"modern"`` — Inter everywhere, clean geometric sans
        - ``"humanist"`` — Nunito, friendly rounded sans-serif
    """

    # --- palette ----------------------------------------------------------
    primary_color: str = "#2c5f8a"
    accent_color: str | None = None  # falls back to primary_color
    background_color: str = "#fbfbfb"
    surface_color: str = "#ffffff"  # cards / panels
    text_color: str = "#1a1a1a"
    muted_text_color: str = "#5a5a5a"
    border_color: str = "#e6e4df"
    error_color: str = "#b3261e"
    error_soft_color: str = "#fdf1f0"

    # --- typography -------------------------------------------------------
    font_preset: str = "academic"  # "academic" | "modern" | "humanist"
    font_family: str = '"Source Serif 4", "Charter", Georgia, "Times New Roman", serif'
    heading_font_family: str | None = None  # None -> mirrors body font
    ui_font_family: str = '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif'
    mono_font_family: str = '"JetBrains Mono", "Menlo", "Consolas", monospace'
    font_size: str = "15.5px"
    line_height: str = "1.6"
    font_pair: str = "serif"  # "serif" | "sans" | "mixed"

    # --- layout / density -------------------------------------------------
    width: str = "700px"
    radius: str = "4px"
    density: str = "comfortable"  # "compact" | "comfortable" | "spacious"
    question_style: str = "plain"  # "plain" | "divided" | "carded" | "accent"

    # --- header / branding ------------------------------------------------
    logo_url: str | None = None
    logo_text: str | None = None  # short text shown when logo_url is unset
    logo_position: str = "left"  # "left" | "right" | "center"
    show_title: bool = True
    institution_name: str | None = None
    study_subtitle: str | None = None
    show_section_numbers: bool = True
    show_progress_text: bool = True
    estimated_minutes: int | None = None

    # --- footer -----------------------------------------------------------
    privacy_url: str | None = None
    contact_email: str | None = None
    ethics_statement: str | None = None

    # --- overrides --------------------------------------------------------
    custom_css: str | None = None

    # --- i18n UI strings ---------------------------------------------------
    next_button_text: str | None = None
    prev_button_text: str | None = None
    submit_button_text: str | None = None
    submitting_text: str | None = None
    required_text: str | None = None
    saving_text: str | None = None
    select_placeholder: str | None = None
    of_text: str | None = None
    selected_text: str | None = None
    resume_title: str | None = None
    resume_action: str | None = None
    restart_action: str | None = None
    page_text: str | None = None
    of_total_text: str | None = None
    retry_title: str | None = None
    retry_body: str | None = None
    retry_action: str | None = None
    save_local_action: str | None = None
    completion_title: str | None = None
    completion_body: str | None = None
    # Every other fixed phrase of the runtime. None keeps the English default
    # quoted in the comment beside (or above) the field; "{name}" in a
    # template is replaced by the value named.
    # Where the respondent is (see show_section_numbers):
    welcome_text: str | None = None  # "Welcome"
    section_text: str | None = None  # "Section {n} of {total}"
    final_section_text: str | None = None  # "Final thoughts"
    estimated_time_text: str | None = None  # "About {minutes} minutes"
    # Answering:
    other_text: str | None = None  # "Other" — metadata["other_label"] wins
    other_placeholder: str | None = None  # "Please specify..."
    none_of_above_text: str | None = None  # "None of the above"
    not_applicable_text: str | None = None  # "Not applicable" (na_option=True)
    min_choices_text: str | None = None  # "Select at least {n} more"
    # "Please answer every row." — a required matrix with rows left ({n} of them)
    required_rows_text: str | None = None
    max_reached_text: str | None = None  # "Maximum reached"
    min_value_text: str | None = None  # "Minimum value is {min}"
    max_value_text: str | None = None  # "Maximum value is {max}"
    chars_remaining_text: str | None = None  # "{n} characters remaining"
    search_placeholder: str | None = None  # "Type to search…"
    no_options_text: str | None = None  # "No options found"
    ranking_hint_text: str | None = None  # "Tap or drag to rank"
    ranking_remaining_text: str | None = None  # "Remaining options"
    invalid_format_text: str | None = None  # "Please check the format of your answer."
    invalid_email_text: str | None = None  # "Please enter a valid email address."
    invalid_phone_text: str | None = None  # "Please enter a valid phone number."
    invalid_url_text: str | None = None  # "Please enter a valid web address (https://…)."
    invalid_date_text: str | None = None  # "Please enter a valid date."
    invalid_time_text: str | None = None  # "Please enter a valid time."
    # The end of the interview:
    response_id_text: str | None = None  # "Response ID"
    submitted_text: str | None = None  # "Submitted"
    screen_out_title: str | None = None  # "Thank you" — a screen-out page without a title
    # "You will be redirected in {seconds} seconds. {link} if not redirected."
    redirect_countdown_text: str | None = None
    redirect_link_text: str | None = None  # "Click here"
    redirecting_text: str | None = None  # "Redirecting you now. {link} if you are not redirected."
    redirecting_link_text: str | None = None  # "Continue"
    quota_full_title: str | None = None  # "Thank you for your interest"
    # "We have already reached our target sample for participants like you."
    quota_full_body: str | None = None
    closed_title: str | None = None  # "Survey closed"
    closed_body: str | None = None  # "This survey is no longer accepting responses."
    error_title: str | None = None  # "Submission error"
    # "We could not save your responses. Please refresh and try again."
    error_body: str | None = None
    attempt_text: str | None = None  # "Attempt {n} of {max}."
    # Around the questions:
    privacy_text: str | None = None  # "Privacy"
    contact_text: str | None = None  # "Contact research team"
    skip_link_text: str | None = None  # "Skip to questionnaire"
    access_error: str | None = None  # "Invalid access code. Please try again."
    page_error_title: str | None = None  # "Something went wrong"
    # "An unexpected error occurred. Your previous answers have been saved."
    page_error_body: str | None = None
    app_error_title: str | None = None  # "Survey temporarily unavailable"
    # "We encountered an unexpected error. Your previous answers have been saved."
    app_error_body: str | None = None
    reload_action: str | None = None  # "Reload survey"

    # --- progress style -------------------------------------------------
    progress_style: str = "bar"  # "bar" | "dots" | "both"

    # --- theme ------------------------------------------------------------
    # `default_theme` is what the respondent starts on; "system" follows their
    # operating system. It is a starting point, not a decision: the runtime
    # shows a light/dark button and remembers what they pick.
    #
    # `allow_theme_switch=False` takes that button away and pins the survey to
    # `default_theme`. A questionnaire is a measurement instrument, and when
    # half a sample answers on a dark ground the presentation is an
    # uncontrolled variable: contrast, legibility, and any image stimulus with
    # a light background all change. Leave it on where the respondent's comfort
    # matters more than that — reading on a dark screen is a real accessibility
    # need, not a preference — and turn it off where the instrument has to look
    # the same for everyone.
    default_theme: str = "light"  # "light" | "dark" | "system"
    allow_theme_switch: bool = True

    # --- redirect -------------------------------------------------------
    # Where a respondent goes after the survey: on completion (a final page
    # without its own redirect_url), after a screen-out (disqualification
    # page) and when the quota is full. Templates: ``{url:NAME}`` is the
    # value of ``?NAME=`` the respondent arrived with (a panel's respondent
    # id), ``{answer:x}`` / ``{label:x}`` pipe answers; values are URL-encoded.
    redirect_url: str | None = None
    screen_out_redirect_url: str | None = None
    quota_full_redirect_url: str | None = None

    # --- color palette extras -------------------------------------------
    warn_color: str = "#9a6a1a"

    # --- navigation -----------------------------------------------------
    allow_back: bool = True  # Show the "Previous" button between pages.

    # --- analytics ------------------------------------------------------
    enable_analytics: bool = False  # Injects Vercel Analytics script

    # --- access code ----------------------------------------------------
    require_access_code: bool = False
    access_codes: list[str] | None = None  # None or list of valid codes
    access_title: str | None = None
    access_body: str | None = None
    access_placeholder: str | None = None
    access_button: str | None = None

    def __post_init__(self) -> None:
        if self.logo_position not in _LOGO_POSITIONS:
            raise ValueError(f"logo_position must be one of: {sorted(_LOGO_POSITIONS)}.")
        if self.density not in _DENSITY_VALUES:
            raise ValueError(f"density must be one of: {sorted(_DENSITY_VALUES)}.")
        if self.font_pair not in _FONT_PAIR_VALUES:
            raise ValueError(f"font_pair must be one of: {sorted(_FONT_PAIR_VALUES)}.")
        if self.question_style not in _QUESTION_STYLES:
            raise ValueError(f"question_style must be one of: {sorted(_QUESTION_STYLES)}.")
        if self.font_preset not in _FONT_PRESET_VALUES:
            raise ValueError(f"font_preset must be one of: {sorted(_FONT_PRESET_VALUES)}.")
        if self.default_theme not in _THEME_VALUES:
            raise ValueError(f"default_theme must be one of: {sorted(_THEME_VALUES)}.")

    @property
    def effective_accent(self) -> str:
        return self.accent_color or self.primary_color

    @property
    def effective_heading_font(self) -> str:
        if self.heading_font_family:
            return self.heading_font_family
        # Use font preset heading if no explicit override
        preset = FONT_PRESETS.get(self.font_preset, FONT_PRESETS["academic"])
        return preset["heading"]

    @property
    def effective_body_font(self) -> str:
        """Body font — uses font_preset unless font_family was explicitly changed."""
        preset = FONT_PRESETS.get(self.font_preset, FONT_PRESETS["academic"])
        # If user set a custom font_family different from the default, respect it
        default_body = '"Source Serif 4", "Charter", Georgia, "Times New Roman", serif'
        if self.font_family != default_body:
            return self.font_family
        return preset["body"]

    @property
    def effective_ui_font(self) -> str:
        """UI font — uses font_preset unless ui_font_family was explicitly changed."""
        preset = FONT_PRESETS.get(self.font_preset, FONT_PRESETS["academic"])
        default_ui = '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif'
        if self.ui_font_family != default_ui:
            return self.ui_font_family
        return preset["ui"]

    @property
    def effective_google_fonts_url(self) -> str:
        """Google Fonts URL for the active font preset."""
        preset = FONT_PRESETS.get(self.font_preset, FONT_PRESETS["academic"])
        return preset["google_fonts"]

    @property
    def effective_logo_text(self) -> str:
        if self.logo_text:
            return self.logo_text
        if self.institution_name:
            words = [w for w in self.institution_name.split() if w and w[0].isalpha()]
            initials = "".join(w[0].upper() for w in words[:2]) or self.institution_name[:2].upper()
            return initials
        return ""
