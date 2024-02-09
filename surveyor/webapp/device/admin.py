from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django import forms
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from crispy_forms.layout import Submit
from crispy_forms.helper import FormHelper

import pandas as pd
# from icecream import ic
from time import perf_counter

from .models import EndNode, SurveyorOrg, InfluxSource, BucketDevice
from accounts.models import Person

# class EndNodeAdmin(admin.ModelAdmin):
#   exclude = ('constants',)
# Register your models here.
# admin.site.register(EndNode, EndNodeAdmin)


class SurveyorOrgAdmin(admin.ModelAdmin):
    search_fields = ['name']

admin.site.register(SurveyorOrg,SurveyorOrgAdmin)

class EndNodeAdmin(admin.ModelAdmin):
    search_fields = ['dev_eui', 'name']
    ordering = ('surveyor_org', 'influx_source', 'name')

admin.site.register(EndNode, EndNodeAdmin)

class InfluxSourceAdmin(admin.ModelAdmin):
    list_display = ('surveyor_org', 'name', 'dbname', 'host')
    list_filter = ['surveyor_org']
    search_fields = ['surveyor_org', 'name', 'dbname']
    ordering = ('surveyor_org', 'name')

admin.site.register(InfluxSource, InfluxSourceAdmin)

class BucketDeviceImportForm(forms.Form):
    influx_source = forms.ModelChoiceField(queryset=InfluxSource.objects.all())
    device_locations = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Submit'))


class BucketDeviceAdmin(admin.ModelAdmin):
    list_display = ('influx_source', 'dev_eui',
                    'name', 'lat', 'long', 'marker', 'address')
    list_filter = ['influx_source']
    search_fields = ('dev_eui', 'name', 'address')
    ordering = ('influx_source', 'name',)
    list_display_links = ["dev_eui", "name"]
    readonly_fields = ('influx_source', 'dev_eui', 'name',
                       'lat', 'long', 'address')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bucketdevice_upload/',
                self.bucketdevice_upload,
                name='bucketdevice_upload',
            ),
        ]
        return custom_urls + urls

    @method_decorator(login_required, name='dispatch')
    def bucketdevice_upload(self, request):
        context = dict(
            self.admin_site.each_context(request)
        )
        result_messages = []
        alert_messages = []
        username = request.user
        person = Person.objects.get(username=username)

        form = BucketDeviceImportForm()
        form.fields["influx_source"].queryset = InfluxSource.objects.filter(
            surveyor_org__in=person.orgs_list()
        )

        if request.method == "POST":
            form = BucketDeviceImportForm(request.POST, request.FILES)
            if form.is_valid():
                device_locations_file = request.FILES['device_locations']
            else:
                alert_messages.append(f"Form Errors: {form.errors}")
                context.update({
                    "form": form,
                    "messages": alert_messages,
                    "result_messages": result_messages,
                })
                return render(request,
                              'admin/bucketdevice_upload.html',
                              context
                              )
        else:
            alert_messages.append("New File Upload")
            context.update({
                "form": form,
                "messages": alert_messages,
                "result_messages": result_messages,
            })
            return render(request, 'admin/bucketdevice_upload.html', context)

        # good post, process it
        influx_source = form.cleaned_data['influx_source']
        # read bucket devices in model, filter by influx source
        bucketdevices_existing = BucketDevice.objects.filter(
            influx_source=form.cleaned_data['influx_source']
            )
        message = f"Removing {bucketdevices_existing.count()} \
                    existing devices from {influx_source.name}."
        result_messages.append(message)
        # now delete them
        delete_result = bucketdevices_existing.delete()
        delete_count = delete_result[0]
        delete_message = f"Deleted {delete_count} existing \
                           devices from {influx_source.name}."
        alert_messages.append(delete_message)
        result_messages.append(delete_message)

        # read csv file into a dataframe
        result_messages.append(f"File uploaded: {device_locations_file}")
        device_loc_df = pd.read_csv(device_locations_file)
        new_records = device_loc_df.shape[0]
        result_messages.append(f"New Device Records: {new_records}")
        # add the influx source id
        device_loc_df['influx_source'] = influx_source

        # Create the bulk Save
        bulk_devices = [
            BucketDevice(
                influx_source=row['influx_source'],
                dev_eui=row['dev_eui'],
                name=row['name'],
                lat=row['lat'],
                long=row['long'],
                marker=row['marker'],
                address=row['address'],
            )
            for index, row in device_loc_df.iterrows()
        ]
        # bulk create the records
        save_start = perf_counter()
        BucketDevice.objects.bulk_create(bulk_devices)

        # save time and result to messages
        save_end = perf_counter()
        save_diff = save_end - save_start
        message = f"Added {new_records} Device Records to {influx_source} \
                    in {save_diff:.2f} seconds."
        alert_messages.append(message)
        result_messages.append(message)

        context.update({
            "form": form,
            "messages": alert_messages,
            "result_messages": result_messages,
        })
        return render(request, 'admin/bucketdevice_upload.html', context)


admin.site.register(BucketDevice, BucketDeviceAdmin)
