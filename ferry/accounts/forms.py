import base64
import binascii
from datetime import timedelta
from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, TimestampSigner

from ferry.accounts.models import APIToken, Person, User


class UserPersonLinkForm(forms.Form):
    link_code = forms.CharField(
        required=True,
        max_length=250,
        label="FACT Code",
        help_text="Please enter your FACT code. Use /ferry fact in Discord to obtain one.",
    )

    def __init__(self, *args: Any, user: User, **kwargs: Any) -> None:
        self.user = user
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Link my account"))

    def clean_link_code(self) -> Person:
        signer = TimestampSigner()
        try:
            signed_data = base64.b64decode(self.cleaned_data["link_code"]).decode()
        except binascii.Error:
            raise ValidationError("The FACT is invalid.") from None
        except UnicodeDecodeError:
            raise ValidationError("The FACT is invalid.") from None

        try:
            person_id = signer.unsign(signed_data, max_age=timedelta(hours=1))
        except BadSignature:
            raise ValidationError("The FACT is invalid.") from None

        try:
            return Person.objects.filter(user__isnull=True).get(pk=person_id)
        except Person.DoesNotExist:
            raise ValidationError("The FACT is invalid.") from None

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()

        if self.user.person is not None:
            raise ValidationError("You are already linked to a person. How did you even get here?")

        return cleaned_data

    def save(self) -> None:
        self.user.person = self.cleaned_data["link_code"]
        self.user.save()


class PersonProfileForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ("display_name",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Save"))


class CreateAPITokenForm(forms.ModelForm):
    class Meta:
        model = APIToken
        fields = ("name",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Create Token"))
