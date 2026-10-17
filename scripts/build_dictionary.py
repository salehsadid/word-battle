"""Rebuild data/cleaned_words.txt: common, everyday English words with plurals removed.

A word is kept when it is
  1. a real word: listed in ENABLE (public-domain word-game list, no proper nouns or abbreviations),
  2. commonly used: wordfreq Zipf frequency >= MIN_ZIPF (about once per million words of modern English),
     with a stricter bar for 3-letter words and a hand-picked list for 2-letter words,
  3. not on the block list (archaic, foreign, abbreviations, offensive), nor mainly a name
     (NLTK's word list has it only capitalised: JOHN, PARIS, FRENCH), and
  4. not a plural (wordgrid.dictionary.cleaner rules).
British spellings of kept words (colour, centre, organise) and a few modern words ENABLE predates (email,
website) are added when they are common too.

Only needed to rebuild the list; the game itself stays offline. Usage:
    pip install wordfreq
    curl -LO https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt
    python scripts/build_dictionary.py enable1.txt
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordfreq import zipf_frequency  # noqa: E402

from wordgrid.config import CLEANED_DICT_PATH  # noqa: E402
from wordgrid.dictionary.cleaner import DictionaryCleaner  # noqa: E402

MIN_ZIPF = 3.0
MIN_ZIPF_3_LETTERS = 3.3  # short-word counts are inflated by abbreviations and other languages

TWO_LETTER = set("""
ah am an as at ax be by do ex go ha he hi if in is it ma me my no of oh on or ox pa so to up us we
""".split())

# Everyday words that wordfreq under-counts
EXTRA = set("""
ado asp boa cob cog cot coy ebb eel emu ewe gnu hem hoe imp ire ism jig keg lug moo mow nab nag nib
ohm orb ply pry pug rut sag sax sob sod tic tot urn wad wag yak yam yew
""".split())

# Common modern words newer than ENABLE
MODERN = set("""
app blog blogger chatbot ebook email emoji hashtag homepage inbox internet login logout malware offline online
podcast screenshot selfie smartphone texting touchscreen username webcam website wifi
""".split())

# Words NLTK lists only capitalised that are still ordinary lower-case words
KEEP_NAMELIKE = set("""
acacia advent bible biblical bohemian bologna braille burgundy cactus cannabis capitol chihuahua cupid
cyclops diaspora epiphany fauna fedora gothic hunter labrador lesbian limerick mayo mercury messiah
minimalist mod mogul nemesis ninja odyssey paisley pharaoh platonic populism populist revised rugby
saviour sumo teddy tiki titan
""".split())

BLOCK = set("""
aba ain ala als alt ama ami ana ava ave bam bel ben bey bis bob bop bot cad cam chi cis col con coo cor
cos cox dee del dev dis dom don dos dow dui dun eff ems eng eta fil gen git goa hah heh hes hon hun ids
ins jin jun kat kay ken lac lam las lea lee lex lib lin loo mae mas med mel mil mir mis mon mos nam nan
nos obi ole ons ops pac pam pas pax phi pol psi raj rec reg res rex roc rom sal sec sen ser sha sic sim
sis sos sox sri tae taj tao tat ted tel tho til tis umm var vis wat wen wha yah yeh
thee thou thy thine hath doth shalt wilt ere oft twas
fag cum tit jew boob boobs dick cock pussy bitch bastard piss wank whore slut twat dyke retard tranny
nigger nigga kike spic chink gook wetback faggot jizz asshole titty retarded
""".split())
BLOCK_PARTS = ("fuck", "shit", "cunt")  # blocked anywhere in a word: bullshit, motherfucker
BLOCK_PREFIXES = ("bitch", "faggot", "nigger", "piss", "slut", "wank", "whore")


def mostly_names() -> set:
    """Words NLTK's word list only has capitalised (proper nouns and adjectives)."""
    from nltk.corpus import words
    entries = words.words()
    lower = {w for w in entries if w.islower()}
    return {w.lower() for w in entries if w[:1].isupper()} - lower - KEEP_NAMELIKE


def is_common(word: str) -> bool:
    if word in BLOCK or word.startswith(BLOCK_PREFIXES) or any(p in word for p in BLOCK_PARTS):
        return False
    if len(word) == 2:
        return word in TWO_LETTER
    if word in EXTRA:
        return True
    floor = MIN_ZIPF_3_LETTERS if len(word) == 3 else MIN_ZIPF
    return zipf_frequency(word, "en") >= floor


def british_variants(word: str) -> set:
    """Candidate British spellings of an American word; frequency decides which are real."""
    out = set()
    for i in range(1, len(word) - 1):
        if word.startswith("or", i):                       # color -> colour
            out.add(word[:i] + "our" + word[i + 2:])
        if word.startswith(("iz", "yz"), i) and word[i + 2:i + 3] in ("e", "i", "a"):
            out.add(word[:i + 1] + "s" + word[i + 2:])      # organize -> organise, analyze -> analyse
    if word.endswith(("ter", "ber", "ger")):              # center -> centre, fiber -> fibre
        out.add(word[:-2] + "re")
    if word.endswith("ense"):                             # defense -> defence
        out.add(word[:-4] + "ence")
    if word.endswith("og"):                               # catalog -> catalogue
        out.add(word + "ue")
    for a, b in (("eled", "elled"), ("eling", "elling"), ("eler", "eller")):
        if word.endswith(a):                              # traveled -> travelled
            out.add(word[:-len(a)] + b)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("enable", type=Path, help="path to enable1.txt")
    parser.add_argument("-o", "--output", type=Path, default=CLEANED_DICT_PATH)
    args = parser.parse_args()

    real = {w.strip().lower() for w in args.enable.read_text(encoding="utf-8").split() if w.strip().isalpha()}
    common = {w for w in real if len(w) >= 2 and is_common(w)}
    british = {v for w in common for v in british_variants(w)
               if v not in real and v not in BLOCK and zipf_frequency(v, "en") >= MIN_ZIPF}
    common |= british | MODERN
    common -= mostly_names()

    # Plural detection checks stems against the full word list, so CATS goes even if CAT were rare.
    cleaner = DictionaryCleaner()
    reference = {w.upper() for w in real | common}
    accepted = sorted(w.upper() for w in common if not cleaner.is_plural(w.upper(), reference)[0])

    args.output.write_text("\n".join(accepted) + "\n", encoding="utf-8")
    print(f"ENABLE words: {len(real):,}  common: {len(common):,} (British spellings: {len(british):,})  "
          f"plurals removed: {len(common) - len(accepted):,}  written: {len(accepted):,} -> {args.output}")


if __name__ == "__main__":
    main()
