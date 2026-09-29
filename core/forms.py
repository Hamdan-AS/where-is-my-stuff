import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import User

CATEGORIES = ["Wallet / Purse", "Cards / IDs", "Keys", "Electronics", "Bag", "Documents", "Cash / Money", "Other"]
CONTENTS = ["CNIC", "Bank cards", "Cash", "Driving licence", "Other items"]
COLOURS = ["Black", "Brown", "Blue", "Red", "Green", "Grey", "White", "Silver", "Other"]
BANK_SERVICES = ["HBL", "MCB", "UBL", "Meezan Bank", "National Bank of Pakistan", "Bank Alfalah", "Allied Bank", "NayaPay", "SadaPay", "JazzCash", "Easypaisa", "Other"]
DEPARTMENTS = [
    "Computer and Information Systems Engineering (CIS)",
    "Computer Science & Information Technology (CSIT)",
    "Civil Engineering",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Metallurgical Engineering",
    "Other",
]

def choices(values):
    return [(v, v) for v in values]

# Control characters and invisible Unicode marks. They exist mainly to hide
# identifiers from the screens below, so they are rejected outright.
# Newline (0x0a), tab (0x09) and carriage return (0x0d) stay legal.
# \x7f-\x9f covers the C1 controls. \u2060-\u206f covers the bidi isolates
# (\u2066-\u2069) alongside the word joiner and the deprecated trailing marks,
# so a place or name cannot be reordered after the embeddings are blocked.
BAD_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060-\u206f\ufeff]")

# Private identifiers that must never appear in a public field (title, location
# description, public description). Reject, never rewrite: the owner moves this
# into the private matching questions instead.
SHORT_FIELD_FORMATS = [             # unmistakable personal data in any context
    re.compile(r"(?:\d[\u3000.@\t -]?){10,}", re.I),   # spaced/dashed/dotted digit runs
    re.compile(r"\b\d{7,11}\b", re.I),                 # bare runs: mobiles, landlines, tokens
    re.compile(r"\d{3}[-.]\d{4}", re.I),               # short separated numbers, e.g. 0300-1234
    re.compile(r"\b\d{13}\b", re.I),                   # raw 13-digit CNIC
    re.compile(r"\b\d{4,5}-\d{7}-\d\b", re.I),         # CNIC 42101-1234567-1
]
IDENTIFIER_PATTERNS = SHORT_FIELD_FORMATS + [
    re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.I),                  # email
    re.compile(r"\b[a-z0-9._+-]+\s+at\s+[a-z0-9.-]+\s+dot\s+[a-z]{2,}\b", re.I),  # obfuscated email
    re.compile(r"\b\d{4}[- .]?[A-Za-z]{1,4}[- .]?\d{2,4}\b", re.I),    # roll 2023-ME-123, 2023ME123
    re.compile(r"\b(?:cnic|nic|id\s?card|identity\s?card|card|account|iban|atm|debit|credit|"
               r"license|licence|passport|emirates)\b[^.\n]{0,30}\d{3,}", re.I),
    re.compile(r"\b(?:roll|reg(?:istration)?|enrol{1,2}ment|seat|token)\s*(?:no\.?|number|#)\s*\d+", re.I),
    re.compile(r"\blasts?\s+(?:\d+\s+|(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+)?"
               r"digits?\b[^\d\n]{0,40}\d", re.I),                    # "last 4 digits 1234"
]

PRIVATE_HINT = ("Move phone numbers, emails, CNIC, card, account, and roll numbers into the private "
                "matching questions. By design only the matched party ever sees those; keeping them "
                "out of the public description protects the owner.")

def words(value):
    value = value.strip()
    if BAD_CHARS.search(value):
        raise ValidationError("Remove special or invisible characters and paste plain text.")
    if not any(c.isalpha() for c in value):
        raise ValidationError("Include words, not only numbers or punctuation.")
    return value

def public_short(value):
    words(value)
    if "@" in value or any(pat.search(value) for pat in SHORT_FIELD_FORMATS):
        raise ValidationError("Remove phone numbers, emails, and personal ID numbers from this field.")
    return value

def public_text(value):
    words(value)
    if any(pat.search(value) for pat in IDENTIFIER_PATTERNS):
        raise ValidationError(PRIVATE_HINT)
    return value

class Registration(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(label="Full name", validators=[words])
    class Meta:
        model = User
        fields = ["first_name", "email"]
    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already registered.")
        return email
    def save(self, commit=True):
        user = super().save(False)
        user.username = user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class EmailLogin(AuthenticationForm):
    username = forms.CharField(label="Email", widget=forms.EmailInput(attrs={
        "autocomplete": "username", "placeholder": "Yahan Apni email dalo", "autofocus": True,
    }))
    remember_me = forms.BooleanField(required=False, label="Remember me")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].widget.attrs["placeholder"] = "Enter your password"

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()

class TypeForm(forms.Form):
    kind = forms.ChoiceField(choices=choices(["Lost", "Found"]), widget=forms.RadioSelect)
    title = forms.CharField(max_length=120, validators=[public_short])
    category = forms.ChoiceField(choices=choices(CATEGORIES))
    event_date = forms.DateField(input_formats=["%d-%m-%Y"], initial=timezone.localdate,
        widget=forms.DateInput(format="%d-%m-%Y", attrs={"placeholder": "DD-MM-YYYY"}))
    def clean_event_date(self):
        value = self.cleaned_data["event_date"]
        if value > timezone.localdate() or value.year < 2000:
            raise ValidationError("Enter a real date between 2000 and today.")
        return value

class DetailsForm(forms.Form):
    description = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 3}), validators=[public_text], label="Public description")
    contact = forms.CharField(max_length=120, help_text="Shared only after both participants accept a handover.")
    def clean_contact(self):
        value = self.cleaned_data["contact"]
        if "@" in value:
            forms.EmailField().clean(value)
        elif not re.fullmatch(r"\+?[0-9 ()-]{7,24}", value) or not 7 <= len(re.sub(r"\D", "", value)) <= 15:
            raise ValidationError("Enter a valid email or phone number.")
        return value

class LocationForm(forms.Form):
    location = forms.CharField(max_length=100, label="Place", validators=[public_short],
        widget=forms.TextInput(attrs={"placeholder": "e.g. Gulshan Block 7, near Ayesha Manzil"}),
        help_text="A readable place name. Pin the exact spot on the map.")
    lat = forms.DecimalField(max_digits=10, decimal_places=8, min_value=-90, max_value=90, label="Latitude",
        widget=forms.NumberInput(attrs={"step": "any", "placeholder": "24.8607"}))
    lng = forms.DecimalField(max_digits=11, decimal_places=8, min_value=-180, max_value=180, label="Longitude",
        widget=forms.NumberInput(attrs={"step": "any", "placeholder": "67.0011"}))
    location_detail = forms.CharField(max_length=255, validators=[public_short], label="Location description")

def schema(category, data):
    fields = {}
    def select(key, label, options):
        fields[key] = forms.ChoiceField(label=label, choices=[("", "Choose…")] + choices(options))
    def text(key, label):
        fields[key] = forms.CharField(label=label, max_length=80, validators=[words])
    def suffix(key, label, n):
        fields[key] = forms.RegexField(r"^[0-9]{%d}$" % n, label=label,
            widget=forms.PasswordInput(attrs={"inputmode": "numeric", "maxlength": n, "pattern": "[0-9]{%d}" % n, "autocomplete": "off"}),
            error_messages={"invalid": f"Enter exactly {n} digits."})
    select("colour", "Colour", COLOURS)
    if category == "Wallet / Purse":
        select("material", "Wallet material", ["Leather", "Fabric", "Synthetic", "Other"])
        select("logo", "Visible logo?", ["Yes", "No"])
        if data.get("logo") == "Yes":
            text("logo_name", "Logo name")
        fields["contents"] = forms.MultipleChoiceField(choices=choices(CONTENTS), required=False,
            widget=forms.CheckboxSelectMultiple, help_text="Select known contents. Leave empty for an empty wallet.")
        selected = data.get("contents", [])
        if "CNIC" in selected:
            suffix("cnic_suffix", "Full 13-digit CNIC", 13)
        if "Bank cards" in selected:
            fields["bank_count"] = forms.IntegerField(min_value=1, max_value=5, initial=1, label="Number of bank cards")
            try:
                count = max(1, min(5, int(data.get("bank_count", 1))))
            except (ValueError, TypeError):
                count = 1
            for i in range(1, count + 1):
                select(f"bank_{i}_issuer", f"Bank card {i} bank or payment service", BANK_SERVICES)
                if data.get(f"bank_{i}_issuer") == "Other":
                    text(f"bank_{i}_other", f"Bank card {i} service name")
                suffix(f"bank_{i}_suffix", f"Bank card {i} full 16-digit number", 16)
        if "Cash" in selected:
            select("cash_range", "Cash approximate amount", ["Below Rs. 500", "Rs. 500 to 1,999", "Rs. 2,000 to 4,999", "Rs. 5,000+"])
            select("cash_notes", "Cash denominations", ["Rs. 100", "Rs. 500", "Rs. 1,000", "Mixed notes"])
        if "Driving licence" in selected:
            text("licence_issuer", "Driving licence issuing authority")
        if "Other items" in selected:
            text("other_contents", "Other contents identifying description")
        select("mark", "Wallet distinguishing mark", ["None", "Scratch", "Sticker", "Tear", "Initials"])
    elif category == "Cards / IDs":
        select("card_type", "Card type", ["CNIC", "NED Student Card", "Bank Card"])
        issuer_options = {
            "CNIC": ["NADRA", "Other"],
            "NED Student Card": DEPARTMENTS,
            "Bank Card": BANK_SERVICES,
        }.get(data.get("card_type"), ["Other"])
        select("issuer", "Issuer or department", issuer_options)
        if data.get("issuer") == "Other":
            text("issuer_other", "Issuer or service name")
        suffix("suffix", "Full 13-digit CNIC, full 16-digit bank card number, or last 4 digits (NED student card)", 13 if data.get("card_type") == "CNIC" else 16 if data.get("card_type") == "Bank Card" else 4)
        select("mark", "Visible mark", ["None", "Scratch", "Sticker", "Crack"])
    else:
        specs = {
            "Keys": [("count", "Key count", ["1", "2", "3", "4", "5+"]), ("kind", "Key type", ["Home", "Car", "Bike", "Locker", "Other"]), ("fob", "Keyring", ["None", "Plastic", "Fabric", "Metal"])],
            "Bag": [("kind", "Bag type", ["Backpack", "Handbag", "Laptop bag", "Tote", "Other"]), ("material", "Material", ["Fabric", "Leather", "Canvas", "Synthetic"]), ("pockets", "Pocket count", ["1", "2", "3", "4+"])],
            "Electronics": [("kind", "Device", ["Phone", "Laptop", "Tablet", "Earbuds", "Charger", "Other"]), ("case", "Case", ["None", "Hard", "Soft", "Sleeve"])],
            "Documents": [("kind", "Document", ["Notebook", "Assignment", "Certificate", "Folder", "Other"]), ("holder", "Holder", ["None", "Folder", "Envelope"])],
            "Cash / Money": [("amount", "Approximate amount", ["Below Rs. 500", "Rs. 500 to 1,999", "Rs. 2,000 to 4,999", "Rs. 5,000+"]), ("notes", "Denominations", ["Rs. 100", "Rs. 500", "Rs. 1,000", "Mixed notes"])],
            "Other": [("material", "Material", ["Metal", "Plastic", "Fabric", "Leather", "Paper", "Other"]), ("size", "Size", ["Small", "Medium", "Large"])],
        }
        for key, label, options in specs.get(category, []):
            select(key, label, options)
        if category == "Electronics":
            text("brand", "Brand")
        if category == "Documents":
            text("issuer", "Issuer")
        select("mark", "Distinguishing mark", ["None", "Scratch", "Sticker", "Tear", "Other"])
    return fields

class MatchingForm(forms.Form):
    def __init__(self, *args, category, selection=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(schema(category, selection or {}))
        for field in self.fields.values():
            field.widget.attrs["title"] = "We value your privacy. Your information is not visible to other users or staff."

# The meeting time is typed as free text, so the browser pattern and the server
# guard have to agree exactly. Keep one copy: when these were written out
# separately, day, month and hour came to accept a single digit that was then
# read as a zero-padded one, while minutes stayed strict.
MEETING_TIME_PATTERN = r"\d{2}-\d{2}-\d{2} \d{2}:\d{2} [AaPp][Mm]"
MEETING_TIME_HINT = "Use DD-MM-YY hh:mm AM/PM with two digits, for example 08-09-26 09:25 PM."

class MeetingForm(forms.Form):
    meeting_place = forms.CharField(
        max_length=255,
        validators=[words],
        label="Meeting place",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Gulshan Chowrangi, near the fountain"}),
        help_text="Any public, safe place for the handover.",
    )
    meeting_at = forms.DateTimeField(
        label="Meeting date and time (Pakistan time)",
        input_formats=["%d-%m-%y %I:%M %p"],
        widget=forms.TextInput(attrs={
            "placeholder": "DD-MM-YY hh:mm AM/PM",
            "pattern": MEETING_TIME_PATTERN,
            "maxlength": 18,  # "15-10-26 03:00 PM" is the longest accepted value
            "autocomplete": "off",
        }),
        error_messages={"invalid": MEETING_TIME_HINT},
    )
    def clean_meeting_at(self):
        raw = self.data.get(self.add_prefix("meeting_at"), "")
        if not re.fullmatch(MEETING_TIME_PATTERN, raw):
            raise ValidationError(MEETING_TIME_HINT)
        value = self.cleaned_data["meeting_at"]
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        if value <= timezone.now():
            raise ValidationError("Choose a future meeting time (Pakistan time).")
        return value
