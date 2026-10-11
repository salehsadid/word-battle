# WordBattle Dictionary Resources

This directory contains offline English dictionary resources utilized by WordBattle (WordGrid).

## Files

- `raw_words.txt`: Original offline English word list (83,667 words, derived from standard Scrabble/TWL lexical sources).
- `cleaned_words.txt`: Preprocessed and filtered dictionary with plural forms excluded according to project requirements.
- `test_words.txt`: Controlled vocabulary used for deterministic unit testing.

## Preprocessing & Filtering Summary

- Source words filtered: 4,994 entries
- Removed proper nouns: 253 (e.g., PIERRE, MOSCOW, KUTUZOV, HOLMES, JEFFERSON, VIRGINIA, etc.)
- Removed plurals: 279 (regular and irregular plurals)
- Removed weird short forms / Roman numerals / fragments: 50 (e.g., LL, PP, FF, TM, VE, DIDN, II, III, IV, etc.)
- Accepted, deduplicated, and sorted words: 4,414 words (from ABANDON to ZONE)

## Plural Filtering Policy

1. **Explicit Preserved Singulars**: Words ending in S that are genuine singular nouns or core words (such as `BUS`, `GAS`, `LENS`, `ANALYSIS`, `GLASS`, `GRASS`, `KISS`, `CRISIS`, `PHYSICS`, etc.) are explicitly preserved and never stripped.
2. **Irregular Plurals**: Identified using a curated lexical mapping of English irregular plural nouns to their singular roots.
3. **Morphological Regular Plurals**: Words ending in S or ES are evaluated through morphological validation (using `inflect` and reference vocabulary verification) to ensure the base form is an accepted English root before the plural form is excluded.
4. **Offline Operation**: Preprocessing occurs once and is saved to `cleaned_words.txt`. The game runs 100% offline with zero network calls.
