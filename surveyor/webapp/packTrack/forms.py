from django import forms
from django.forms import DateTimeInput
from device.models import EndNode
# from icecream import ic

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Button, ButtonHolder, Field


class selectForm(forms.Form):

    endnode = forms.ModelChoiceField(queryset=None, help_text="LoRaWAN End Device")
    start = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "class": "col-sm-6",
                "min": "2023-01-01T00:01",
                "type": "datetime-local",
            }
        )
    )

    end = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "class": "col-sm-6",
                "min": "2023-01-01T00:01",
                "type": "datetime-local",
            }
        )
    )

    def __init__(self, *args, **kwargs):
        self.orgs_list = kwargs.pop('orgs_list', None)
        super(selectForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_method = "GET"

        self.fields["endnode"].queryset = EndNode.objects.filter(
            surveyororg=self.orgs_list
        ).order_by("surveyor_org", "name")

        self.helper.layout = Layout(
            Div(
                Field("endnode", css_class="col-md-8 w-50"),
                Div(
                    "start",
                    ButtonHolder(
                        Button(
                            "1 day ago",
                            "yesterday",
                            css_class="btn btn-outline-secondary btn-sm",
                            onclick="calculateTime(this);",
                        ),
                        Button(
                            "today",
                            "today",
                            css_class="btn btn-outline-secondary btn-sm",
                            onclick="calculateTime(this);",
                        ),
                        Button(
                            "1 week ago",
                            "1 week ago",
                            css_class="btn btn-outline-secondary btn-sm",
                            onclick="calculateTime(this);",
                        ),
                        Button(
                            "1 month ago",
                            "1 month ago",
                            css_class="btn btn-outline-secondary btn-sm",
                            onclick="calculateTime(this);",
                        ),
                        css_id="start-btn-holder",
                        css_class="d-inline col-auto",
                    ),
                ),
                Div(
                    "end",
                    ButtonHolder(
                        Button(
                            "yesterday",
                            "today",
                            css_class="btn btn-outline-secondary btn-sm",
                            onclick="calculateTime(this);",
                        ),
                        Button(
                            "now",
                            "now",
                            css_class="btn btn-outline-secondary btn-sm",
                            onclick="calculateTime(this);",
                        ),
                        css_id="end-btn-holder",
                        css_class="d-inline col-auto",
                    ),
                ),
                Div(
                    Button(
                        "last hour",
                        "last hour",
                        css_class="btn btn-outline-secondary btn-sm",
                        onclick="lastHours(this);",
                    ),
                    Button(
                        "last 3 hours",
                        "last 3 hours",
                        css_class="btn btn-outline-secondary btn-sm",
                        onclick="lastHours(this);",
                    ),
                ),
                Submit("submit", "Submit", css_class="mt-3 btn-primary w-50"),
                css_class="row",
            )
        )
