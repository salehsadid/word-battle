# Removes uncommon words from data/cleaned_words.txt, in place.
#
# Run after scripts/build_dictionary.py (it needs the same `wordfreq` package):
#
#     pip install wordfreq
#     python scripts/filter_common_words.py
#
# Short words matter most, because they are the ones that actually appear on the board, so they get the strictest
# frequency limits. Frequency alone lets some names, crude words and abbreviations through and drops a few everyday
# words, so both are fixed with hand-made lists.

from pathlib import Path

from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parents[1]
DICT = ROOT / "data" / "cleaned_words.txt"

# Minimum Zipf frequency by word length (3.5 is about 3 uses per million words).
# 2- and 3-letter words come from short, hand-checked lists, so they are not frequency-filtered.
MIN_ZIPF = {4: 3.6, 5: 3.5}
MIN_ZIPF_LONG = 3.4      # 6 letters and longer

# Removed whatever their frequency: names, crude words, abbreviations, prefixes, fragments, archaic words.
BLOCK = set("""
ASS BUM PEE FRO SAC TIC PRO MID MOD BIO PER VIA NOR ION HEX ORB VAT
BETH CAIN CHAD COBB GLEN HANK JAKE JANE JOSH KANE KIRK MAYA MICK MILO NOEL TATE TROY VERA RUTH MODI CARL COLE DALE
LANG HONG SEPT HAHA PARA SEMI ANTI WIFI COMP CANT WONT TORY RAPE CRAP DAMN BUTT HECK NUDE HOMO METH FART DOPE
LOWE HOWE BACH LING MONO SHRI NESS CASA COCA NANA PAPA
BENNY BOBBY BRENT BROCK BURKE COLIN DONNA HARRY HENRY HOGAN JENNY JERRY JIMMY KELLY KERRY LAURA LEONE LEVIN
LEWIS LOGAN MARIA NANCY PEDRO PERRY PETER RALPH RANDY RILEY ROGER SALLY SILVA SMITH SONNY TERRY TOMMY WALLY
WEBER MONTE BUFFY WIGAN WILLY MOLLY CHANG CISCO HONDA TESLA YAHOO CALIF CHEVY ARIEL DILDO HORNY SPERM PRICK
QUEER LYNCH JIHAD KAPPA MATER MOMMA FELLA GIMME AMINO HYDRO TERRA IMPLY CIRCA QUASI
BAILEY BURTON DALTON DEXTER GRAHAM HECTOR HURLEY JORDAN MARCEL MARTIN MORGAN MORRIS MURPHY NELSON NEWTON
PHOEBE REGINA SHELLY SHERRY STELLA THORPE WARREN ABIGAIL BURGESS COLLINS DERRICK GILBERT LAMBERT MAXWELL
TIFFANY TIMOTHY BENJAMIN FRANKLIN NAPOLEON SHERLOCK MADELEINE
""".split())

# Kept although their frequency is below the limit: everyday words.
KEEP = set("""
BEET YOLK YAWN HOOF GULL MOTH KITE PLUM WINK TIDY VASE COMB DART LOFT CLAP SOCK MASH TAME SOAK DAMP CHEW BULB
FOWL SILL SOOT HISS FUZZ BLOB OMEN CRAM SNUG GUST WREN HIVE CURL TUCK LUSH BREW COZY NEON PEST TUNA MAZE DIME
ACNE ZINC
""".split())


# True if the word should stay in the dictionary.
def keep(word: str) -> bool:
    if word in BLOCK:
        return False
    if len(word) <= 3 or word in KEEP:
        return True
    limit = MIN_ZIPF.get(len(word), MIN_ZIPF_LONG)
    return zipf_frequency(word.lower(), "en") >= limit


# Filter the dictionary file in place.
def main() -> None:
    words = [w.strip().upper() for w in DICT.read_text(encoding="utf-8").splitlines() if w.strip()]
    kept = sorted(set(w for w in words if keep(w)))
    DICT.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"{len(words):,} words -> {len(kept):,} words ({len(words) - len(kept):,} removed)")


if __name__ == "__main__":
    main()
