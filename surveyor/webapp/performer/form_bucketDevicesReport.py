from django import forms
from django.forms import DateTimeInput
# from django.core.exceptions import ValidationError
# from django.urls import reverse

# from pytz import NonExistentTimeError
from device.models import InfluxSource
# from accounts.models import Person
# from icecream import ic

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Submit, Div, Button, ButtonHolder, HTML, Column


class bucketDevicesForm(forms.Form):
    source = forms.ModelChoiceField(queryset=None, help_text="InfluxDB Source")
    meas = forms.CharField(initial='nameme', min_length=2, max_length=20, strip=True, help_text="InfluxDB Measurement")

    start = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "class": "col-sm-6",
                "min": "2023-01-01T00:00",
                "type": "datetime-local",
            }
        )
    )
    end = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "class": "col-sm-6",
                "min": "2023-01-01T00:00",
                "type": "datetime-local",
            }
        )
    )
    center_latitude = forms.DecimalField(required=False, max_digits=10,
                                         decimal_places=5, help_text="Center Latitude")
    center_longitude = forms.DecimalField(required=False, max_digits=10,
                                          decimal_places=5, help_text="Center Longitude")
    radius_km = forms.IntegerField(required=False, initial=2, min_value=1,
                                   max_value=10, help_text="Radius Markers (km)")

    def __init__(self, *args, **kwargs):
        self.orgs_list = kwargs.pop('orgs_list', None)
        super(bucketDevicesForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = "GET"
        self.fields["source"].queryset = InfluxSource.objects.filter(
            surveyor_org__in=self.orgs_list
        ).order_by("name")
        for fieldname in ['center_latitude', 'center_longitude', 'radius_km']:
            self.fields[fieldname].help_text = None
        self.helper.form_id = 'bucketDevicesDelayForm'
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        "source",
                        "meas",
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
                        css_class="col-12 col-lg-6 col-md-8",
                    ),
                    Column(
                        "center_latitude",
                        "center_longitude",
                        "radius_km",
                        HTML('<p><strong>Optionally, provide a map center and marker rings!</strong></p>'),
                        css_class="col-12 col-lg-4 col-md-6",
                    ),
                ),
                Row(
                    HTML('<hr>'),
                    Submit("submit", "Submit", css_class="mt-3 btn-primary w-25"),
                ),
            )
        )
