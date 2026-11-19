"""Localize interface messages while keeping task text and shortcuts intact."""
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

PORTUGUESE = json.loads(Path(__file__).with_name('pt.json').read_text(encoding='utf-8'))
_language = 'en'


def tr(message):
    return PORTUGUESE.get(message, message) if _language == 'pt' else message


def preference_root():
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state'))
    return Path(os.environ.get('LEFT_UNDONE_STATE_DIR', state / 'left-undone-herdr'))


def load_language(root):
    global _language
    try:
        value = (root / 'language').read_text().strip()
    except (OSError, UnicodeError):
        value = 'en'
    _language = 'pt' if value == 'pt' else 'en'


def language_button():
    return '[9 English]' if _language == 'pt' else '[9 Português]'


def toggle_language(root):
    global _language
    value = 'en' if _language == 'pt' else 'pt'
    with NamedTemporaryFile(mode='w', dir=root, delete=False) as temp:
        path = Path(temp.name)
        try:
            temp.write(value + '\n')
            temp.flush()
            path.replace(root / 'language')
        finally:
            path.unlink(missing_ok=True)
    _language = value


# Status files and closure records written by earlier collectors may be in
# either language. Localize these application-owned messages at read time.
_ENGLISH = {translation: source for source, translation in PORTUGUESE.items()}


# Only these two saved system messages interpolate values. Restrict the
# patterns to their actual field types so task text never becomes a template.
_TEMPLATES = {
    'Curation: {0} changes · {1} preserved': (r'(\d+)', r'(\d+)'),
    '{0}: analyzer unavailable (exit code {1}). Check CLI sign-in and usage limits.':
        (r'(codex|claude)', r'(-?\d+)'),
}


def saved_patterns():
    for template, fields in _TEMPLATES.items():
        for localized in (template, PORTUGUESE[template]):
            pattern = re.escape(localized)
            for index, field in enumerate(fields):
                pattern = pattern.replace(re.escape('{' + str(index) + '}'), field)
            yield re.compile(pattern), template


_SAVED_MESSAGES = tuple(saved_patterns())


def stored_label(text):
    key = _ENGLISH.get(text, text)
    if key in PORTUGUESE:
        return tr(key)
    for pattern, template in _SAVED_MESSAGES:
        match = pattern.fullmatch(text)
        if match:
            return tr(template).format(*match.groups())
    return text


def collector_status(text):
    message, separator, tail = text.rpartition(' · ')
    if separator and (re.fullmatch(r'\d{2}:\d{2}:\d{2}', tail) or
                      stored_label(separator + tail) == tr(' · retrying in 30 s')):
        suffix = stored_label(separator + tail)
        return collector_status(message) + suffix
    for prefix in ('Error: ', 'Erro: '):
        if text.startswith(prefix):
            return tr('Error: ') + stored_label(text[len(prefix):])
    if _ENGLISH.get(text, text) == 'Curation up to date':
        return tr('Collector active')
    return stored_label(text)
