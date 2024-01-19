from django import forms
from django.core.exceptions import ValidationError
from django.forms import DateTimeInput

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    Layout,
    Submit,
    Button,
    ButtonHolder,
    Div,
    Field,
)
from crispy_forms.bootstrap import InlineCheckboxes

from device.models import EndNode


class GpsDevicesForm(forms.Form):
    endnodes = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=[],
        required=True,
    )

    start = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "class": "col-sm-6",
                "min": "2010-01-01T00:01",
                "type": "datetime-local",
            }
        )
    )
    end = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "type": "datetime-local",
                "min": "2010-01-01T00:01",
            }
        )
    )

    def __init__(self, *args, **kwargs):
        self.orgs_list = kwargs.pop('orgs_list', None)
        super().__init__(*args, **kwargs)

        # Pare the list by Orgs
        self.fields["endnodes"].choices = [
            (endnode.id, endnode)
            for endnode in list(
                EndNode.objects.filter(
                    gps_payload=True,
                    surveyor_org__in=self.orgs_list
                ).order_by("surveyor_org", "name")
            )
        ]

        self.fields["endnodes"].queryset = EndNode.objects.filter(
            gps_payload=True,
            survyeororg__in=self.orgs_list
        ).order_by("name")

        self.helper = FormHelper(self)
        self.helper.form_method = "GET"
        self.helper.layout = Layout(
            Div(
                InlineCheckboxes("endnodes"),
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

    def clean(self):
        cleaned_data = super().clean()
        valid = False
        for key, val in cleaned_data.items():
            if val:
                valid = True
                break
            if not valid:
                raise ValidationError("You must input at least one search parameter!")


class MapGpsDeviceForm(forms.Form):

    endnode = forms.ModelChoiceField(queryset=None, help_text="LoRaWAN End Device")
    start = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={"min": "2010-01-01T00:01", "type": "datetime-local"}
        )
    )

    end = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={"type": "datetime-local", "min": "2010-01-01T00:01"}
        )
    )

    def __init__(self, *args, **kwargs):
        self.orgs_list = kwargs.pop('orgs_list', None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_method = "GET"

        # Pare the list by Orgs
        self.fields["endnode"].queryset = EndNode.objects.filter(
            gps_payload=True,
            surveyor_org__in=self.orgs_list
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

# class CoverageForm(forms.Form):
#     gateways = forms.MultipleChoiceField(
#         widget=forms.CheckboxSelectMultiple,
#         choices=[],
#         required=True,
#     )

#     endnodes = forms.MultipleChoiceField(
#         widget=forms.CheckboxSelectMultiple,
#         choices=[],
#         required=True,
#     )

#     start = forms.DateTimeField(
#         widget=DateTimeInput(
#             attrs={
#                 "class": "col-sm-6",
#                 "min": "2010-01-01T00:01",
#                 "type": "datetime-local",
#             }
#         )
#     )

#     end = forms.DateTimeField(
#         widget=DateTimeInput(
#             attrs={
#                 "type": "datetime-local",
#                 "min": "2010-01-01T00:01",
#             }
#         )
#     )

#     def __init__(self, *args, **kwargs):
#         self.gateways = kwargs.pop('gateways',[])
#         super().__init__(*args, **kwargs)
#         self.fields["gateways"].choices = [
#             (gateway_eui,gateway_eui) for gateway_eui in self.gateways
#         ]

#         self.helper = FormHelper
#         self.helper.form_method = "GET"
#         self.helper.layout = Layout(
#             Div(
#                 InlineCheckboxes("gateways"),
#                 Field("endnodes", type="hidden"),
#                 Field("start", type="hidden"),
#                 Field("end", type="hidden"),
#                 Submit("submit", "Submit", css_class="mt-3 btn-primary w-50")
#                 )
#             )

#     def clean(self):
#         cleaned_data = super().clean()
#         valid = False
#         for key, val in cleaned_data.items():
#             if val:
#                 valid = True
#                 break
#             if not valid:
#                 raise ValidationError("You must input at least one search parameter!")
