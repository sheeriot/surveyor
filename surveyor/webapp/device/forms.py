from django import forms
from django.forms import ModelForm, DateTimeInput
from django.urls import reverse

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Submit, Div, Button, ButtonHolder, Column

from .models import EndNode
from device.models import InfluxSource

# from icecream import ic


class EndNodeForm(ModelForm):
    class Meta:
        model = EndNode
        fields = [
                'surveyor_org', 'name', 'dev_eui', 'influx_source', 'influx_measurement', 'app_eui',
                'app_key', 'frequency_plan', 'manufacturer', 'model', 'revision', 'gps_payload'
                 ]


class bucketDeviceForm(forms.Form):
    source = forms.ModelChoiceField(queryset=None, help_text="InfluxDB Source")
    meas = forms.CharField(initial='nameme', min_length=2, max_length=15, strip=True, help_text="InfluxDB Measurement")
    dev_eui = forms.CharField(initial='ABCD1234EFCD9876', min_length=16, max_length=16, help_text="Device EUI")

    start = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "class": "col-sm-6",
                # "min": "2023-01-01T00:00",
                "type": "datetime-local",
            }
        )
    )
    end = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "class": "col-sm-6",
                # "min": "2023-01-01T00:00",
                "type": "datetime-local",
            }
        )
    )

    def __init__(self, *args, **kwargs):
        if 'orgs_list' in kwargs:
            self.orgs_list = kwargs.pop('orgs_list')
        super(bucketDeviceForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_method = "GET"
        self.fields["source"].queryset = InfluxSource.objects.filter(
            surveyor_org__in=self.orgs_list
        ).order_by('surveyor_org', 'name')
        self.helper.form_action = reverse('bucketdevice')
        self.helper.layout = Layout(
            Div(
                Row(
                    Column('source'),
                    Column('meas'),
                    Column('dev_eui'),
                    # css_class='form-row'
                ),
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
