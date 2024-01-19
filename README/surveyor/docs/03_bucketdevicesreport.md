
## Bucket Device Report

Use this view for viewing all the devices in an InfluxDB Bucket. Links are provided to inspect individual devices with PackGraph (single device packet history view).

Select the **Source**, type in the **Measurement** table name, adjust the __start__ and __end__ times as needed, then click **Submit**.

![Bucket Device Report Form](images/surveyor_bucketdeviceform.png)

This report (BucketDevice View) is executed using an "Asynchronous Task", meaning that it will be given to the Surveyor_Worker to perform in the background.

Your browser will watch the status of the task then download the results into the web page using AJAX (background web) transactions.

### Want Rings?

The Bucket Device Report will allow you to set a GPS location and ring size if you want to add rings as markers to the map.

### Report Parameters

The report page first reports back the task status and requested parameters.

![Bucket Device Report - Status/Parameters](images/surveyor_bucketdevicereportrequest.png)

A URL is provided for sharing. The **bookmark-able** URL uses Zulu time to ensure the report parameters are consistent, regardless of the timezone of the requester. These bookmark-able URLs can be used to generate periodic reports.

### Report Generation

While that task executes, let's peek under the hood. Here is a Web Transaction view of this long running task:

![BucketDeviceReport - Transactions](diagrams/bucketDevicesReport.png)

Status icons are presented on the web browser to indicate report progress.

### Location Data

Fixed Location of Device (FLoD) Data, I made that up for fixed devices, can be provided in the Surveyor using one of two methods.
- bucketdevice admin pages allow uploading of device lat/long data using CSV
- retrieving the pluscode location (e.g. 8624C3F8+CW8) from the InfluxDB measurement data

**Note:** Only devices with locations will appear on the maps. All devices should appear in the tables.

### Sections

The BucketDevices report includes the following sections
- **Report Summary** - top level summary data
- **Packet Delivery Ratio (PDR) Distribution** - quick view of frame packet delivery performance
- **Geolocation Maps** - show PDR by location
- **Device Summary Report** - PDR table for all devices
- **Device/Gateway Summary Report** - frame information by device and gateway

Here is an example header showing report contents and a summary.

![Bucket Device Report Header - Contents/Summary](images/surveyor_bucketdevicereportheader.png)
