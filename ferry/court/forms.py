from typing import Any

from crispy_forms.bootstrap import (
    PrependedText,
)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django import forms

from ferry.accounts.models import Person
from ferry.court.models import Consequence


class ConsequenceCreateForm(forms.ModelForm):
    content = forms.CharField(label="Sentence", max_length=150)

    class Meta:
        model = Consequence
        fields = ("content",)

    def __init__(self, *args: Any, person: Person, **kwargs: Any) -> None:
        self.person = person
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            PrependedText("content", "$player has been sentenced to"),
        )
        self.helper.add_input(Submit("submit", "Create Consequence"))

    def save(self, commit: bool = True) -> Any:  # noqa: FBT001, FBT002
        self.instance.created_by = self.person
        return super().save(commit)
