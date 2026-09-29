#!/usr/bin/env python3
"""Probe public_text screening.

Run from the repo root:

    .venv/bin/python scripts/screening_probe.py

Prints an OK/MISS line per case and a closing tally. Use it while tuning
core/forms.py patterns; the authoritative gate is core/tests.py.
"""
import django
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()
from core.forms import public_text

CASES = [
    # (label, expect_valid, payload)
    ("LEGIT short desc",            True,  "Black leather wallet lost near the library entrance"),
    ("LEGIT colours/sizes",         True,  "blue rain jacket, size small, sleeve patch on the left arm"),
    ("LEGIT laptop specs",          True,  "HP laptop, 8GB RAM, 256GB SSD, charger included"),
    ("LEGIT phone model",           True,  "iPhone 15 Pro, 512GB storage, dark blue case"),
    ("LEGIT date in text",          True,  "lost on 12-05-2026 near the cafeteria"),
    ("LEGIT room/building",         True,  "in room 105, building 5, second floor"),
    ("LEGIT year",                  True,  "2026 semester badge, round, green"),
    ("LEGIT price",                 True,  "Rs 1500 in a small brown pouch"),
    ("LEGIT key count",             True,  "bunch of 5 keys on a metal ring, one is orange"),
    ("LEGIT storage",               True,  "4GB USB drive, black casing, red cap"),
    ("LEGIT Urdu",                  True,  "سياه بٹوہ لائبریری کے قریب ملا"),
    ("LEGIT grade",                 True,  "12th grade notebook, red cover, physics notes"),
    ("LEGIT trap modelno",          True,  "F-16A model, 2024 release, boxed set"),
    ("LEGIT roll-like close call",  True,  "F-16 flight hours 2025 driving fine"),
    ("LEGIT batch",                 True,  "Batch 2026-27, MTech students only"),
    # --- identifiers that MUST be blocked ---
    ("LEAK email",                  False, "contact me at a@example.com for details"),
    ("LEAK email tags",             False, "write to name.last+tag@sub.domain.pk"),
    ("LEAK email obfuscated",       False, "reach ali at gmail dot com please"),
    ("LEAK mobile spaced",          False, "call 0312 3456789 after 5pm"),
    ("LEAK mobile dashed",          False, "0300-1234567 is my number"),
    ("LEAK mobile +92",             False, "my cell is +92-300-1234567"),
    ("LEAK landline bare 8",        False, "reach me at 99251234 in the office"),
    ("LEAK landline bare 7",        False, "dial 3051234 any time"),
    ("LEAK cnic phrased",           False, "cnic 42101-1234567-1 for verification"),
    ("LEAK cnic raw 13",            False, "id: 4210112345671"),
    ("LEAK card full",              False, "visa card number 1234 5678 9012 3456"),
    ("LEAK account long",           False, "bank account 012345678901 iirc"),
    ("LEAK iban",                   False, "iban PK36SCBL0000001123456702"),
    ("LEAK last-digits phrase",     False, "last 4 digits are 1234 on the card"),
    ("LEAK roll keyword",           False, "roll no 2023-ME-123 on the tag"),
    ("LEAK roll compact",           False, "2023ME123 is engraved on it"),
    ("LEAK reg keyword",            False, "reg 2023-CS-045 inside the cover"),
    ("LEAK seat keyword",           False, "seat number 654321 written under it"),
    ("LEAK card ending",            False, "card ending 1234, holder starts with A"),
    ("LEAK scattered digits",       False, "0-3-0-0-1-2-3-4-5-6-7 contact"),
    ("LEAK fullwidth digits",       False, "mobile ０３００１２３４５６７"),
    ("LEAK control-char breakup",   False, "0300\x00-1234567 cell"),
    ("LEAK zero-width breakup",     False, "0300\u200c1234567 cell"),
    ("LEAK dotted mobile",          False, "phone 0300.123.4567 thanks"),
    ("LEAK 300 prefix",             False, "03211234567 call me"),
    # --- leftover speech that must NOT be blocked ---
    ("LEGIT card on floor",         True,  "the card is on floor 12, near the window"),
    ("LEGIT card in case",          True,  "a bag with a red card on the side"),
    ("LEGIT seat belt",             True,  "seat belt found in the 2026 car, silver clip"),
    ("LEGIT ball rolls",            True,  "the ball will roll under the 12th stair if left on the desk"),
    ("LEGIT seat unusual",          True,  "the seat was set near the front, not the 7th row"),
    ("LEGIT metro card",            True,  "metro card, blue, with a small sticker"),
    ("LEGIT found near gate",       True,  "found near gate 3 by the tall banyan tree"),
    ("LEGIT floor 1",               True,  "left on the 1st floor of the library reading area"),
    ("LEGIT lanyard",               True,  "blue COMSATS lanyard, no attachments"),
    ("LEGIT batch 2029",            True,  "graduation badge batch 2029, silver pin"),
    ("LEGIT model numbers",         True,  "charger model 65W, cable length 1.2m"),
    ("LEGIT make/model",            True,  "Toyota Corolla keys with a black remote"),
    # --- tighter leak variants ---
    ("LEAK card attached",          False, "card no 1234 printed on the back"),
    ("LEAK cnic item context",      False, "CNIC card 42101-1234567-1 in a brown wallet"),
    ("LEAK passport",               False, "passport AV-1234567, blue cover"),
    ("LEAK whatsapp",               False, "whatsapp 0345 9876543 me"),
    ("LEAK roll short",             False, "roll no 123 engraved on the tag"),
    ("LEAK seat short",             False, "seat number 654321 written under it"),
    ("LEAK reg short",              False, "reg no 2023-CS-045 inside the cover"),
    ("LEAK token",                  False, "token #88 on the lanyard"),
    ("LEAK emirates",               False, "emirates id 784-2026-1234567-1"),
    ("LEAK last digits spelled",    False, "last four digits are 4321 on the card"),
    ("LEAK hbl account",            False, "hbl account and the digits are 1234567890"),
    ("LEAK debit",                  False, "debit card 4521 found inside"),
    ("LEAK atm",                    False, "atm pin written on the sleeve: 1908"),
    ("LEAK uppercase email",        False, "email ME AT GMAIL DOT COM teehee"),
    ("LEAK spaced phone",           False, "number is 0 3 0 0 1 2 3 4 5 6 7"),
]

def main():
    passed = failed = 0
    for label, expect_ok, payload in CASES:
        try:
            public_text(payload)
            got = True
        except Exception:
            got = False
        if got == expect_ok:
            passed += 1
        else:
            failed += 1
            print(f"  [ MISS ] {label} expect={'PASS' if expect_ok else 'BLOCK'} got={'pass' if got else 'block'} :: {payload[:60]!r}")
    print(f"\nscreening_ok {passed} / {len(CASES)} (misses {failed})")

if __name__ == "__main__":
    main()