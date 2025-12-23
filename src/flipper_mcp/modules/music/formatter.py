"""FMF (Flipper Music Format) formatting and validation utilities."""

import re
from typing import Tuple, Optional


def validate_fmf_format(song_data: str) -> Tuple[bool, Optional[str]]:
    """
    Validate FMF format syntax.
    
    Args:
        song_data: Song data in FMF format
        
    Returns:
        (is_valid, error_message) tuple
    """
    if not song_data or not song_data.strip():
        return False, "Song data is empty"
    
    # Check for header (should start with BPM, DURATION, OCTAVE)
    if not re.search(r'BPM=\d+', song_data):
        return False, "Missing BPM in header (format: BPM=<number>:)"
    
    if not re.search(r'DURATION=\d+', song_data):
        return False, "Missing DURATION in header (format: DURATION=<number>:)"
    
    if not re.search(r'OCTAVE=\d+', song_data):
        return False, "Missing OCTAVE in header (format: OCTAVE=<number>:)"
    
    # Basic note pattern validation
    # Notes should match pattern: duration + note + optional octave + optional sharp/flat + optional dot
    # Example: 4C4, 8A#5, 2P, 16Bb3.
    note_pattern = r'\d+[CDEFGABP]\d*[#b]?\.?'
    
    # Extract notes section (after header)
    # Header format: BPM=...:DURATION=...:OCTAVE=...:
    # Find the last colon that ends the header
    header_pattern = r'BPM=\d+:DURATION=\d+:OCTAVE=\d+:'
    header_match = re.search(header_pattern, song_data)
    
    if not header_match:
        return False, "Invalid header format (expected: BPM=<num>:DURATION=<num>:OCTAVE=<num>:)"
    
    # Extract notes section after the header
    header_end = header_match.end()
    notes_section = song_data[header_end:].strip()
    
    if not notes_section:
        return False, "No notes found after header"
    
    # Check for valid note patterns (allow spaces and commas as separators)
    # Split by common separators and validate each token
    tokens = re.split(r'[\s,]+', notes_section)
    valid_tokens = [t for t in tokens if t.strip()]
    
    if not valid_tokens:
        return False, "No valid notes found"
    
    # Basic validation - check that tokens look like notes
    # This is lenient to allow for various formatting styles
    for token in valid_tokens:
        token = token.strip()
        if not token:
            continue
        # Should start with a digit (duration) and contain a note letter
        if not re.match(r'^\d+[CDEFGABP]', token):
            return False, f"Invalid note format: '{token}' (expected format: DURATIONNOTE[OCTAVE][#/b][.])"
    
    return True, None


def get_fmf_format_specification() -> str:
    """
    Get detailed FMF format specification.
    
    Returns:
        Detailed format specification string
    """
    spec = """FMF (Flipper Music Format) Specification
==========================================

FMF is a text-based music format similar to RTTTL, used by Flipper Zero's Music Player app.

HEADER FORMAT
-------------
The header must be at the start of the file and contains three required parameters:

  BPM=<bpm>:DURATION=<duration>:OCTAVE=<octave>:

Where:
  - BPM: Beats per minute (tempo), typically 60-200
  - DURATION: Default note duration (1=whole, 2=half, 4=quarter, 8=eighth, 16=sixteenth)
  - OCTAVE: Default octave (3-7, where 4 is middle C)

Example headers:
  BPM=120:DURATION=4:OCTAVE=4:
  BPM=100:DURATION=8:OCTAVE=5:

NOTE FORMAT
-----------
Each note follows this format:

  DURATIONNOTE[OCTAVE][SHARP/FLAT][DOT]

Components:
  - DURATION: Note duration (1, 2, 4, 8, 16)
  - NOTE: Note letter (C, D, E, F, G, A, B) or P for rest/pause
  - OCTAVE: Optional octave number (3-7), uses default if omitted
  - SHARP/FLAT: Optional # for sharp or b for flat
  - DOT: Optional . for dotted note (1.5x duration)

Examples:
  4C4     - Quarter note C in octave 4
  8A#5    - Eighth note A sharp in octave 5
  2P      - Half note rest (pause)
  16Bb3.  - Dotted sixteenth note B flat in octave 3
  4C      - Quarter note C in default octave
  8E.     - Dotted eighth note E in default octave

NOTES
-----
- Notes are separated by spaces or commas
- Rests use 'P' instead of a note letter
- Sharps use '#' and flats use 'b'
- Dotted notes add 50% to the duration
- Octave 4 is middle C (C4)
- Valid octaves are 3-7

COMPLETE EXAMPLE
----------------
BPM=120:DURATION=4:OCTAVE=4: 4C 4C 8C 4D 4E 4C 4E 4D 8C 8C 4G 4F 4E 4D 4C

This plays a simple melody with:
- Tempo: 120 BPM
- Default duration: Quarter notes (4)
- Default octave: 4
- Notes: C C C D E C E D C C G F E D C

HAPPY BIRTHDAY EXAMPLE
---------------------
BPM=100:DURATION=4:OCTAVE=4: 4C 4C 8D 4C 4F 4E 4C 4C 8D 4C 4G 4F 4C 4C 8C5 4A 4F 4E 4D 8Bb 8Bb 4A 4F 4G 4F

This is a simplified version of "Happy Birthday" with:
- Tempo: 100 BPM
- Default duration: Quarter notes
- Default octave: 4 (with one note in octave 5: C5)
- Mix of quarter and eighth notes

TIPS
----
- Start with simple melodies using default octave
- Use rests (P) for pauses between phrases
- Adjust BPM to match the song's natural tempo
- Use dotted notes for more musical expression
- Test with short melodies first"""
    
    return spec

