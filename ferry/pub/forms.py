from typing import Any

from crispy_forms.bootstrap import AppendedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django import forms
from django.urls import reverse

from ferry.pub.models import PubEvent


class PubEventBookingForm(forms.Form):
    table_size = forms.IntegerField(max_value=100, min_value=0, required=True, label="Table Size")

    def __init__(self, *args: Any, pub_event: PubEvent, **kwargs: Any) -> None:
        self.pub_event = pub_event
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            AppendedText("table_size", "people"),
        )
        self.helper.add_input(Submit("submit", "Add Booking"))
        self.helper.form_action = reverse("pub:events-add-booking", kwargs={"pk": pub_event.id})
