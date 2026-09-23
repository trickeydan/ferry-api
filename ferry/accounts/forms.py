from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from ferry.accounts.models import APIToken, Person


class PersonProfileForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ("display_name", "autopub")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.fields[
            "autopub"
        ].help_text = "AutoPub will automatically mark you as attending when a pub event is created."

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
