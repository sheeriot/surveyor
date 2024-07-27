from django import forms
from django.forms import DateTimeInput
# from django.core.exceptions import ValidationError
# from django.urls import reverse

from device.models import InfluxSource, BucketDevice

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Submit, Div, Button, ButtonHolder, HTML, Column


class bucketDevicesForm(forms.Form):

    source = forms.ModelChoiceField(queryset=None, help_text="InfluxDB Source")
    no_choice = [('None', 'None')]
    report_group = forms.ChoiceField(choices=no_choice,
                                     help_text="Scope to report_group",
                                     required=False,
                                     )
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

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")
        if start and end and start >= end:
            raise forms.ValidationError("Start date must be before end date.")
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.orgs_list = kwargs.pop('orgs_list', None)
        super(bucketDevicesForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

        self.helper.form_id = 'bucketDevicesReportForm'
        self.helper.form_method = 'get'
        self.helper.form_action = 'bucketDevicesReport'

        self.fields["source"].queryset = InfluxSource.objects.filter(
            surveyor_org__in=self.orgs_list
        ).order_by("name")

        if 'source' in self.data:
            try:
                source_id = int(self.data.get('source'))
                report_groups = BucketDevice.objects.filter(
                    influx_source_id=source_id).values_list(
                        'report_group', flat=True
                        ).distinct().order_by('report_group')
                report_groups = list(filter(lambda x: x != '', report_groups))
                self.fields['report_group'].choices = [('None', 'None')] + [(group, group) for group in report_groups]
            except (ValueError, TypeError):
                self.fields['report_group'].choices = [('None', 'None')]
        else:
            self.fields['report_group'].choices = [('None', 'None')]

        for fieldname in ['center_latitude', 'center_longitude', 'radius_km']:
            self.fields[fieldname].help_text = None

        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        "source",
                        "report_group",
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
                                css_class="d-inline",
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
                            HTML('<br><b>Recent:</b>'),
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
                    ),
                    Column(
                        "center_latitude",
                        "center_longitude",
                        "radius_km",
                        HTML('<p><strong>Optionally, provide a map center and marker rings!</strong></p>'),
                        css_class="col-md-3",
                    ),
                ),
                Row(
                    Submit("submit", "Submit", css_class="mt-3 btn-primary w-25"),
                ),
            )
        )
