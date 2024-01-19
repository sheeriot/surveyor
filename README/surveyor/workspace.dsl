workspace "RF Field Surveyor" "A Django (python) web application for inspecting LoRaWAN peformance" {

    !identifiers hierarchical
    !docs docs

    model {

        # influxdb = softwareSystem "InfluxDB" "a time-series database" influxdbtag

        surveyor = softwareSystem "RF Field Surveyor" "RF Coverage" webapptag {
            group ComposeNginx {
                nginx = container "Nginx" "Web Server\nSSL Proxy" "Docker" nginxtag
            }
            group ComposeSurveyor {
                database = container "SQLite3" "Database" "text" databasetag
                redis = container "Redis" "Cache" "Docker" redistag
                webapp = container "Surveyor" "Django/Python" "Docker" webapptag {
                    nginx -> this gunicorn
                    -> database
                    -> redis set jobs
                    -> redis get results
                }
                worker = container "Surveyor_Worker" "Django/Python" "Docker" workertag {
                    -> redis get jobs
                    -> redis set results
                    -> database
                }
            }
            staticfiles = container "Static Files" "" "" staticfilestag {
                nginx -> this "static\nfiles"
            }
        }

        influxdb = softwareSystem "InfluxDB" "a time-series database" influxdbtag {
            organization = group "Influx Organization" {
                source = container "Influx Bucket" "data store" "bucket" influxbuckettag {
                    measurement = component "Influx Measurement" " " "table" influxmeastag
                    surveyor.webapp -> this query
                    surveyor.worker -> this query
                }
            }
        }

        fieldtech = person "Field Technician" "Field Technician" fieldtechtag {
            -> surveyor.nginx "Web Access" "https" webaccessreltag
        }

        deploymentEnvironment Dev {
            deploymentNode iotdash-dev-surveyor "Surveyor" "development linux vm" Ubuntu22.04 {
                # surveyor1 = softwareSystemInstance surveyor [] surveyor1tag
                suveyor1_webapp = containerInstance surveyor.webapp
                surveyor1_worker = containerInstance surveyor.worker
                surveyor1_nginx = containerInstance surveyor.nginx
                surveyor1_database = containerInstance surveyor.database
                surveyor1_redis = containerInstance surveyor.redis
            }
        }

        deploymentEnvironment QA {
            deploymentNode iotdash-qa-surveyor "Surveyor" "QA Linux VM" Ubuntu22.04 {
                # surveyor1 = softwareSystemInstance surveyor [] surveyor1tag
                suveyor2_webapp = containerInstance surveyor.webapp
                surveyor2_worker = containerInstance surveyor.worker
                surveyor2_nginx = containerInstance surveyor.nginx
                surveyor2_database = containerInstance surveyor.database
                surveyor2_redis = containerInstance surveyor.redis
            }
        }

        deploymentEnvironment Prod {
            deploymentNode iotdash-prod-surveyor "Surveyor" "Production Linux VM" Ubuntu22.04 {
                suveyor_webapp = containerInstance surveyor.webapp
                surveyor_worker = containerInstance surveyor.worker
                surveyor_nginx = containerInstance surveyor.nginx
                surveyor_database = containerInstance surveyor.database
                surveyor_redis = containerInstance surveyor.redis
            }
        }
        deploymentEnvironment Brazil-QA {
            deploymentNode iotdash-qa-surveyorbrazil "Surveyor" "Production Linux VM" Ubuntu22.04 {
                softwareSystemInstance surveyor "" surveyortag {
                # suveyor_webapp = containerInstance surveyor.webapp
                # surveyor_worker = containerInstance surveyor.worker
                # surveyor_nginx = containerInstance surveyor.nginx
                # surveyor_database = containerInstance surveyor.database
                # surveyor_redis = containerInstance surveyor.redis
                }
            }
        }
    }

    views {

        container surveyor RFFieldSurveyor "RF Field Surveyor" {
            include *
        }
        container influxdb "InfluxDB" "InfluxDB - Time Series Database" {
            include *
        }
        deployment surveyor Dev surveyor1_view "Surveyor1 - Development" {
            include *
        }
        deployment surveyor QA surveyor2_view "Surveyor2 - QA" {
            include *
        }
        deployment surveyor Prod surveyor_view "Surveyor - Production" {
            include *

        }
        styles {
            relationship "Relationship" {
                # color green
                dashed false
                thickness 3
            }
            element webapptag {
                // from surveyor header
                background #2f3067
                color white
                fontSize 24
                shape WebBrowser
                icon docs/icons/surveyor50b.png
            }

            element workertag {
                // from surveyor header
                background #5156b9
                color white
                icon docs/icons/surveyor50b.png
            }

            element databasetag {
                background #84cef4
                color #ffffff
                height 250
                width 250
                shape Cylinder
                icon docs/icons/sqlite_icon.png
            }
            element redistag {
                background #ff6156
                height 250
                width 250
                shape Pipe
                icon docs/icons/redis_icon.png
            }
            element nginxtag {
                background #00e95e
                height 250
                width 250
                shape Ellipse
                icon docs/icons/nginx_icon.png
            }
            element staticfilestag {
                background #efe4c6
                height 200
                width 200
                fontsize 18
                shape Folder
                icon docs/icons/documents_icon.png
            }
            element influxdbtag {
                background #9394FF
                shape Cylinder
                icon docs/icons/influxdb_icon.png
            }
            element influxbuckettag {
                background #5efff7
                shape Cylinder
                icon docs/icons/bucket_icon.png
            }
            element fieldtechtag {
                background plum
                shape Robot
            }
        }
    }

}
